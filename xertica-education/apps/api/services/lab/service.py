import io
import json
import os
import re
from typing import Any, Dict, List
from uuid import UUID

from adapters.llm.base import BaseLLMAdapter
from adapters.storage import get_storage_adapter
from config.settings import settings
from services.kb.interface import KnowledgeBaseInterface
from services.research.service import TECHNOLOGY_ALIASES, TOOL_REGISTRY

from .interface import LabServiceInterface
from prompts.lab import SYSTEM_PROMPT

MAX_TOOLS = 2
MAX_PREREQUISITES = 2
MAX_INSTRUCTIONS = 5
MAX_SUCCESS_CRITERIA = 3
MAX_REFLECTION_QUESTIONS = 2
MAX_SOURCE_REFERENCES = 2
MAX_SAFETY_NOTES = 1


class LabService(LabServiceInterface):
    def __init__(self, llm_adapter: BaseLLMAdapter, kb: KnowledgeBaseInterface, storage=None):
        self.llm_adapter = llm_adapter
        self.kb = kb
        self.storage = storage or get_storage_adapter()

    async def generate_lab(
        self,
        route_id: UUID,
        module_id: str,
        route_name: str,
        route_objective: str,
        module_name: str,
        module_description: str,
        module_objective: str,
        company_name: str,
        customer_context: Dict[str, Any],
        approved_sources: List[Dict[str, Any]],
        user_prompt: str | None = None,
    ) -> Dict[str, Any]:
        kb_hits = []
        grounded_text = ""
        try:
            kb_hits = await self.kb.query(
                learning_path_id=route_id,
                text="\n".join(
                    filter(
                        None,
                        [route_name, route_objective, module_name, module_description, module_objective],
                    )
                ),
                k=8,
            )
            grounded_text = "\n\n".join(
                f"- {hit.content}" for hit in kb_hits if getattr(hit, "content", None)
            )
        except Exception as e:
            print(f"Warning: RAG query failed during lab generation: {e}")

        detected_tools = self._detect_tools(
            "\n".join(
                filter(
                    None,
                    [
                        route_name,
                        route_objective,
                        module_name,
                        module_description,
                        module_objective,
                        grounded_text,
                        json.dumps(approved_sources, ensure_ascii=False),
                    ],
                )
            )
        )

        prompt = self._build_prompt(
            route_name=route_name,
            route_objective=route_objective,
            module_name=module_name,
            module_description=module_description,
            module_objective=module_objective,
            company_name=company_name,
            customer_context=customer_context,
            approved_sources=approved_sources,
            grounded_text=grounded_text,
            detected_tools=detected_tools,
            user_prompt=user_prompt,
        )

        raw_response = await self.llm_adapter.chat_completion(
            role="lab_generator",
            prompt=f"{SYSTEM_PROMPT}\n\n{prompt}",
        )

        parsed = self._extract_and_parse_json(raw_response)
        normalized = self._normalize_lab(
            parsed,
            module_name=module_name,
            module_description=module_description,
            module_objective=module_objective,
            approved_sources=approved_sources,
            detected_tools=detected_tools,
        )

        await self.save_lab_files(route_id, module_id, normalized)
        normalized["groundingStatus"] = "kb-grounded" if kb_hits else "module-grounded"
        normalized["provenance"] = {
            "approved_sources": approved_sources,
            "grounding_hits": [
                {
                    "title": getattr(hit.citation, "title", None),
                    "url": getattr(hit.citation, "url", None),
                    "score": getattr(hit.citation, "score", None),
                }
                for hit in kb_hits
            ],
            "detected_tools": detected_tools,
        }
        return normalized

    async def save_lab_files(self, route_id: UUID | str, module_id: str, lab: Dict[str, Any]) -> Dict[str, Any]:
        txt_content = (lab.get("classroomText") or self._build_classroom_text(lab)).strip()
        lab["classroomText"] = txt_content
        pdf_bytes = self._generate_pdf_bytes(txt_content)

        filename_prefix = f"{route_id}_{module_id}_lab"
        base_path = f"{route_id}/{module_id}/lab"
        lab["txtUrl"] = await self.storage.upload_file(
            settings.storage_bucket,
            f"{base_path}/{filename_prefix}.txt",
            txt_content.encode("utf-8"),
        )
        lab["pdfUrl"] = await self.storage.upload_file(
            settings.storage_bucket,
            f"{base_path}/{filename_prefix}.pdf",
            pdf_bytes,
        )
        lab["storagePath"] = f"{base_path}/{filename_prefix}.pdf"

        json_bytes = json.dumps(lab, ensure_ascii=False, indent=2).encode("utf-8")
        lab["jsonUrl"] = await self.storage.upload_file(
            settings.storage_bucket,
            f"{base_path}/{filename_prefix}.json",
            json_bytes,
        )
        return lab

    def _build_prompt(
        self,
        *,
        route_name: str,
        route_objective: str,
        module_name: str,
        module_description: str,
        module_objective: str,
        company_name: str,
        customer_context: Dict[str, Any],
        approved_sources: List[Dict[str, Any]],
        grounded_text: str,
        detected_tools: List[Dict[str, Any]],
        user_prompt: str | None,
    ) -> str:
        sources_json = json.dumps(approved_sources[:5], ensure_ascii=False, indent=2)
        tools_json = json.dumps(detected_tools[:MAX_TOOLS], ensure_ascii=False, indent=2)
        customer_json = json.dumps(customer_context or {}, ensure_ascii=False, indent=2)

        parts = [
            f"RUTA: {route_name}",
            f"OBJETIVO DE LA RUTA: {route_objective}",
            f"MÓDULO: {module_name}",
            f"DESCRIPCIÓN DEL MÓDULO: {module_description}",
            f"OBJETIVO DE APRENDIZAJE DEL MÓDULO: {module_objective}",
            f"EMPRESA / CUSTOMER CONTEXT PRINCIPAL: {company_name}",
            f"CUSTOMER CONTEXT JSON:\n{customer_json}",
            f"HERRAMIENTAS / TECNOLOGÍAS DETECTADAS:\n{tools_json}",
            f"FUENTES APROBADAS Y VERIFICADAS DISPONIBLES:\n{sources_json}",
        ]
        if grounded_text:
            parts.append(f"CONTENIDO RELEVANTE DE KNOWLEDGE BASE / RAG:\n{grounded_text}")
        else:
            parts.append("CONTENIDO RELEVANTE DE KNOWLEDGE BASE / RAG: no disponible.")
        parts.append(
            "Diseña un laboratorio práctico compacto que ayude al alumno a aplicar lo enseñado en este módulo. "
            "Usa el largo y ritmo de una tarea de Classroom: intro breve, pasos accionables, un entregable claro "
            "y tips puntuales. El campo classroomText debe ser el material principal para Google Classroom: una sola "
            "pieza de texto, con ritmo de laboratorio, lista para copiar y pegar. Debe sentirse propio de este cliente "
            "y de estas herramientas, no una plantilla genérica."
        )
        if user_prompt:
            parts.append(f"INSTRUCCIÓN ADICIONAL DE REFINAMIENTO (Prioridad alta): {user_prompt}")
        return "\n\n".join(parts)

    def _detect_tools(self, text: str) -> List[Dict[str, Any]]:
        haystack = (text or "").lower()
        detected: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for tool in TOOL_REGISTRY:
            if any(alias in haystack for alias in tool["aliases"]):
                detected.append(
                    {
                        "name": tool["tool"],
                        "vendor": tool["vendor"],
                        "url": tool.get("official_doc") or tool.get("official_article"),
                    }
                )
                seen.add(tool["tool"].lower())

        for name, aliases in TECHNOLOGY_ALIASES.items():
            if name.lower() in seen:
                continue
            if any(alias in haystack for alias in aliases):
                detected.append({"name": name, "vendor": "General", "url": None})
                seen.add(name.lower())

        return detected

    def _extract_and_parse_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        try:
            fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            candidate = fenced.group(1) if fenced else None
            if candidate is None:
                start, end = text.find("{"), text.rfind("}")
                if start != -1 and end > start:
                    candidate = text[start : end + 1]
            if candidate:
                return json.loads(candidate)
        except Exception as e:
            print(f"Error parsing JSON from lab generator: {e}")
        return {}

    def _normalize_lab(
        self,
        raw: Dict[str, Any],
        *,
        module_name: str,
        module_description: str,
        module_objective: str,
        approved_sources: List[Dict[str, Any]],
        detected_tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        instructions_raw = raw.get("instructions")
        if not isinstance(instructions_raw, list) or len(instructions_raw) == 0:
            return self._fallback_lab(
                module_name=module_name,
                module_description=module_description,
                module_objective=module_objective,
                approved_sources=approved_sources,
                detected_tools=detected_tools,
            )

        difficulty = str(raw.get("difficulty") or "intermediate").lower()
        if difficulty not in {"beginner", "intermediate", "advanced"}:
            difficulty = "intermediate"

        normalized_tools = []
        for item in (raw.get("tools") or [])[:MAX_TOOLS]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            purpose = str(item.get("purpose") or "").strip()
            if not name:
                continue
            normalized_tools.append(
                {
                    "name": name,
                    "purpose": self._compact_text(purpose or f"Aplicar {name} dentro del laboratorio.", max_words=18),
                    "url": item.get("url"),
                }
            )

        if not normalized_tools and detected_tools:
            normalized_tools = [
                {
                    "name": tool["name"],
                    "purpose": f"Aplicar {tool['name']} en el contexto práctico del módulo.",
                    "url": tool.get("url"),
                }
                for tool in detected_tools[:MAX_TOOLS]
            ]

        normalized_instructions = []
        for index, item in enumerate(instructions_raw[:MAX_INSTRUCTIONS], start=1):
            if not isinstance(item, dict):
                continue
            title = self._compact_text(str(item.get("title") or "").strip() or f"Paso {index}", max_words=9)
            description = self._compact_text(str(item.get("description") or "").strip(), max_words=80)
            if not description:
                continue
            normalized_instructions.append(
                {
                    "step": index,
                    "title": title,
                    "description": description,
                    "expectedResult": self._compact_text(str(item.get("expectedResult") or "").strip(), max_words=18) or None,
                    "tip": self._compact_text(str(item.get("tip") or "").strip(), max_words=24) or None,
                }
            )

        if not normalized_instructions:
            return self._fallback_lab(
                module_name=module_name,
                module_description=module_description,
                module_objective=module_objective,
                approved_sources=approved_sources,
                detected_tools=detected_tools,
            )

        prerequisites = [
            self._compact_text(str(item).strip(), max_words=16)
            for item in (raw.get("prerequisites") or [])[:MAX_PREREQUISITES]
            if str(item).strip()
        ]
        reflection_questions = [
            self._compact_text(str(item).strip(), max_words=18)
            for item in (raw.get("reflectionQuestions") or [])[:MAX_REFLECTION_QUESTIONS]
            if str(item).strip()
        ]
        safety_notes = [
            self._compact_text(str(item).strip(), max_words=24)
            for item in (raw.get("safetyNotes") or [])[:MAX_SAFETY_NOTES]
            if str(item).strip()
        ]

        deliverable = raw.get("deliverable") if isinstance(raw.get("deliverable"), dict) else {}
        deliverable_norm = {
            "description": self._compact_text(str(deliverable.get("description") or "Entrega una evidencia del ejercicio resuelto.").strip(), max_words=28),
            "format": self._compact_text(str(deliverable.get("format") or "Documento breve o captura").strip(), max_words=8),
            "successCriteria": [
                self._compact_text(str(item).strip(), max_words=18)
                for item in (deliverable.get("successCriteria") or [])[:MAX_SUCCESS_CRITERIA]
                if str(item).strip()
            ] or ["La entrega demuestra aplicación correcta del módulo."],
        }

        source_references = []
        for source in (raw.get("sourceReferences") or [])[:MAX_SOURCE_REFERENCES]:
            if not isinstance(source, dict):
                continue
            title = self._compact_text(str(source.get("title") or "").strip(), max_words=12)
            if not title:
                continue
            source_references.append(
                {
                    "sourceId": str(source.get("sourceId") or "").strip() or None,
                    "title": title,
                    "url": str(source.get("url") or "").strip() or None,
                }
            )

        if not source_references:
            source_references = self._default_source_references(approved_sources)

        steps = [
            {
                "title": instruction["title"],
                "desc": instruction["description"],
                "tool": normalized_tools[0]["name"] if normalized_tools else None,
                "tip": instruction.get("tip"),
            }
            for instruction in normalized_instructions
        ]

        lab = {
            "title": self._compact_text(str(raw.get("title") or f"Laboratorio práctico · {module_name}").strip(), max_words=12),
            "objective": self._compact_text(str(raw.get("objective") or module_objective or module_description or "").strip(), max_words=28),
            "scenario": self._compact_text(str(raw.get("scenario") or module_description or "").strip(), max_words=90),
            "estimatedTimeMinutes": self._safe_int(raw.get("estimatedTimeMinutes"), fallback=25, min_value=10, max_value=60),
            "difficulty": difficulty,
            "tools": normalized_tools,
            "prerequisites": prerequisites,
            "instructions": normalized_instructions,
            "deliverable": deliverable_norm,
            "reflectionQuestions": reflection_questions,
            "sourceReferences": source_references,
            "safetyNotes": safety_notes,
            "steps": steps,
            "console": [f"[ ] {instruction['title']}" for instruction in normalized_instructions],
        }
        classroom_text = self._compact_multiline_text(str(raw.get("classroomText") or "").strip(), max_words=650)
        lab["classroomText"] = classroom_text or self._build_classroom_text(lab)
        return lab

    def _fallback_lab(
        self,
        *,
        module_name: str,
        module_description: str,
        module_objective: str,
        approved_sources: List[Dict[str, Any]],
        detected_tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        tool_name = detected_tools[0]["name"] if detected_tools else "la herramienta del módulo"
        tool_url = detected_tools[0].get("url") if detected_tools else None
        objective = module_objective or f"Aplicar {module_name} en un caso práctico guiado."
        scenario = (
            f"En este laboratorio vas a aplicar {module_name} en una actividad breve y concreta. "
            f"La meta es pasar de entender el concepto a producir una evidencia útil para el contexto del cliente."
        )
        instructions = [
            {
                "step": 1,
                "title": "Define el desafio",
                "description": f"Elige una situacion real del equipo donde {tool_name} pueda ayudar. Escribe en una frase que quieres resolver y para quien.",
                "expectedResult": "Un desafio claro y contextualizado.",
                "tip": "Hazlo especifico: audiencia, objetivo y restriccion.",
            },
            {
                "step": 2,
                "title": "Ejecuta la practica",
                "description": f"Usa {tool_name} o simula su uso con este prompt base: \"Ayudame a resolver [DESAFIO] para [AUDIENCIA] usando [CRITERIOS DEL MODULO]\".",
                "expectedResult": "Una primera respuesta o prototipo.",
                "tip": "Cambia los corchetes antes de correrlo.",
            },
            {
                "step": 3,
                "title": "Refina el resultado",
                "description": "Pide una mejora concreta: mas claro, mas visual, mas accionable o mejor alineado al contexto de la empresa.",
                "expectedResult": "Una version mejorada.",
                "tip": "No cambies todo el prompt; conversa con la herramienta.",
            },
            {
                "step": 4,
                "title": "Guarda tu evidencia",
                "description": "Exporta o copia el resultado final y agrega una nota breve explicando por que cumple el objetivo del modulo.",
                "expectedResult": "Una entrega lista para revisar.",
                "tip": "Incluye captura, enlace o texto final.",
            },
        ]
        lab = {
            "title": f"Laboratorio práctico · {module_name}",
            "objective": objective,
            "scenario": scenario,
            "estimatedTimeMinutes": 20,
            "difficulty": "intermediate",
            "tools": (
                [{"name": tool_name, "purpose": "Aplicar el concepto central del módulo.", "url": tool_url}]
                if tool_name
                else []
            ),
            "prerequisites": [
                "Haber revisado el contenido principal del módulo.",
                f"Tener acceso a {tool_name} o una forma de simularlo.",
            ],
            "instructions": instructions,
            "deliverable": {
                "description": "Evidencia breve de la práctica realizada y la decisión tomada.",
                "format": "Documento breve, captura o enlace",
                "successCriteria": [
                    "Aplica el concepto central del módulo.",
                    "Está conectada al contexto del cliente.",
                    "Incluye una mejora o refinamiento.",
                ],
            },
            "reflectionQuestions": [
                "¿Qué cambió entre tu primer resultado y el refinado?",
                "¿Cómo lo aplicarías en una situación real?",
            ],
            "sourceReferences": self._default_source_references(approved_sources),
            "safetyNotes": [],
            "steps": [
                {
                    "title": item["title"],
                    "desc": item["description"],
                    "tool": tool_name,
                    "tip": item.get("tip"),
                }
                for item in instructions
            ],
            "console": [f"[ ] {item['title']}" for item in instructions],
        }
        lab["classroomText"] = self._build_classroom_text(lab)
        return lab

    def _default_source_references(self, approved_sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        refs = []
        for source in approved_sources[:MAX_SOURCE_REFERENCES]:
            refs.append(
                {
                    "sourceId": str(source.get("id") or "").strip() or None,
                    "title": self._compact_text(source.get("title") or source.get("url") or "Fuente aprobada", max_words=12),
                    "url": source.get("url"),
                }
            )
        return refs

    def _compact_text(self, value: str, *, max_words: int) -> str:
        text = re.sub(r"\s+", " ", value or "").strip()
        if not text:
            return ""
        words = text.split(" ")
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]).rstrip(".,;:") + "..."

    def _compact_multiline_text(self, value: str, *, max_words: int) -> str:
        text = re.sub(r"\n{3,}", "\n\n", (value or "").strip())
        if not text:
            return ""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]).rstrip(".,;:") + "..."

    def _safe_int(self, value: Any, *, fallback: int, min_value: int, max_value: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        return max(min_value, min(max_value, parsed))

    def _build_classroom_text(self, lab: Dict[str, Any]) -> str:
        title = lab.get("title") or "Laboratorio práctico"
        objective = lab.get("objective") or ""
        scenario = lab.get("scenario") or ""
        minutes = lab.get("estimatedTimeMinutes")
        tools = lab.get("tools") or []
        instructions = lab.get("instructions") or []
        deliverable = lab.get("deliverable") or {}
        tips = [item.get("tip") for item in instructions if item.get("tip")]

        lines = [f"🧪 Laboratorio: {title}"]
        if minutes:
            lines.append(f"Tiempo estimado: {minutes} minutos")
        lines.append("")
        if objective:
            lines.append(objective)
        if scenario:
            lines.extend(["", scenario])

        tool_names = ", ".join(tool.get("name", "") for tool in tools if tool.get("name"))
        if tool_names:
            lines.extend(["", f"Herramienta principal: {tool_names}"])

        lines.extend(["", "1. Desafío"])
        lines.append("Aterriza el caso: define qué vas a crear, resolver o decidir usando el contenido del módulo.")

        for instruction in instructions:
            step = int(instruction.get("step") or 0) + 1
            lines.extend(["", f"{step}. {instruction.get('title', 'Paso de práctica')}"])
            lines.append(instruction.get("description", ""))
            if instruction.get("expectedResult"):
                lines.append(f"Resultado esperado: {instruction['expectedResult']}")

        if deliverable:
            lines.extend(["", "Entrega"])
            lines.append(deliverable.get("description") or "Entrega una evidencia breve del laboratorio.")
            if deliverable.get("format"):
                lines.append(f"Formato: {deliverable['format']}")
            criteria = deliverable.get("successCriteria") or []
            if criteria:
                lines.append("Debe mostrar:")
                for criterion in criteria[:MAX_SUCCESS_CRITERIA]:
                    lines.append(f"- {criterion}")

        if tips:
            lines.extend(["", "✨ Tips de oro"])
            for tip in tips[:2]:
                lines.append(f"- {tip}")

        if lab.get("safetyNotes"):
            lines.extend(["", f"⚠️ Nota clave: {lab['safetyNotes'][0]}"])

        if lab.get("reflectionQuestions"):
            lines.extend(["", "Cierre rápido"])
            for question in lab.get("reflectionQuestions")[:MAX_REFLECTION_QUESTIONS]:
                lines.append(f"- {question}")

        return "\n".join(line for line in lines if line is not None).strip()

    def _generate_pdf_bytes(self, text: str) -> bytes:
        printable_text = self._plain_text_for_pdf(text)
        lines = self._pdf_layout_lines(printable_text)

        page_width = 612
        page_height = 792
        margin_x = 54
        margin_top = 58
        margin_bottom = 54
        line_height = 15
        heading_line_height = 20

        pages: List[List[tuple[str, bool]]] = []
        current_page: List[tuple[str, bool]] = []
        y = page_height - margin_top
        first_line = True

        for line, is_heading in lines:
            needed = heading_line_height if is_heading else line_height
            if y - needed < margin_bottom and current_page:
                pages.append(current_page)
                current_page = []
                y = page_height - margin_top
            current_page.append((line, is_heading or first_line))
            y -= needed
            first_line = False

        if current_page:
            pages.append(current_page)
        if not pages:
            pages = [[("Laboratorio práctico", True)]]

        objects: List[bytes] = []
        objects.append(b'')  # 1 catalog, filled after page ids are known
        objects.append(b'')  # 2 pages tree
        objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')

        page_ids: List[int] = []
        for page_lines in pages:
            page_id = len(objects) + 1
            content_id = page_id + 1
            page_ids.append(page_id)
            content = self._pdf_page_content(page_lines, page_height, margin_x, margin_top)
            objects.append(
                f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] '
                f'/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode('ascii')
            )
            objects.append(b'<< /Length ' + str(len(content)).encode('ascii') + b' >>\nstream\n' + content + b'\nendstream')

        kids = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
        objects[0] = b'<< /Type /Catalog /Pages 2 0 R >>'
        objects[1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'.encode('ascii')

        output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f'{index} 0 obj\n'.encode('ascii'))
            output.extend(obj)
            output.extend(b'\nendobj\n')

        xref_offset = len(output)
        output.extend(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
        output.extend(b'0000000000 65535 f \n')
        for offset in offsets[1:]:
            output.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
        output.extend(
            f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n'.encode('ascii')
        )
        return bytes(output)

    def _plain_text_for_pdf(self, text: str) -> str:
        clean = re.sub(r"\r\n?", "\n", text or "")
        clean = re.sub(r"^#{1,6}\s+", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"^>\s?", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"^[-*]\s+", "- ", clean, flags=re.MULTILINE)
        clean = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", clean)
        clean = re.sub(r"\*\*\*([^*]+)\*\*\*", r"\1", clean)
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
        clean = re.sub(r"__([^_]+)__", r"\1", clean)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        clean = re.sub(r"[\U00010000-\U0010ffff]", "", clean)
        return re.sub(r"\n{3,}", "\n\n", clean).strip()

    def _pdf_layout_lines(self, text: str) -> List[tuple[str, bool]]:
        import textwrap

        wrapped: List[tuple[str, bool]] = []
        for paragraph_index, paragraph in enumerate(text.split("\n")):
            stripped = paragraph.strip()
            if not stripped:
                if wrapped and wrapped[-1][0]:
                    wrapped.append(("", False))
                continue

            is_heading = paragraph_index == 0 or self._looks_like_heading(stripped)
            prefix = ""
            body = stripped
            bullet_match = re.match(r"^([-•])\s+(.+)$", stripped)
            numbered_match = re.match(r"^(\d+\.\s+)(.+)$", stripped)
            if bullet_match:
                prefix = "- "
                body = bullet_match.group(2)
            elif numbered_match:
                prefix = numbered_match.group(1)
                body = numbered_match.group(2)

            width = 72 if is_heading else 88
            lines = textwrap.wrap(
                body,
                width=width,
                initial_indent=prefix,
                subsequent_indent=" " * len(prefix),
                break_long_words=False,
                replace_whitespace=True,
            ) or [prefix.rstrip() or body]
            wrapped.extend((line, is_heading and index == 0) for index, line in enumerate(lines))

        return wrapped

    def _looks_like_heading(self, value: str) -> bool:
        normalized = value.strip().rstrip(":")
        if len(normalized) > 55 or normalized.endswith((".", ",", ";")):
            return False
        return normalized.lower() in {
            "tu desafío",
            "tu desafio",
            "tu misión",
            "tu mision",
            "manos a la obra",
            "pasos a seguir",
            "entregable",
            "tu entregable",
            "criterios de éxito",
            "criterios de exito",
            "tips rápidos",
            "tips rapidos",
            "tips pro",
            "cierre rápido",
            "cierre rapido",
        }

    def _pdf_page_content(self, page_lines: List[tuple[str, bool]], page_height: int, margin_x: int, margin_top: int) -> bytes:
        commands: List[bytes] = []
        y = page_height - margin_top
        for line, is_heading in page_lines:
            if not line:
                y -= 10
                continue
            font_size = 16 if is_heading else 11
            leading = 20 if is_heading else 15
            escaped = self._pdf_escape_text(line)
            commands.append(
                f'BT /F1 {font_size} Tf 1 0 0 1 {margin_x} {y} Tm '.encode('ascii')
                + b'('
                + escaped
                + b') Tj ET'
            )
            y -= leading
        return b'\n'.join(commands)

    def _pdf_escape_text(self, text: str) -> bytes:
        encoded = text.encode("cp1252", errors="replace")
        return encoded.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")

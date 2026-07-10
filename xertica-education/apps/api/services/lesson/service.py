import os
import io
import re
import json
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, List

from adapters.llm.base import BaseLLMAdapter
from services.kb.interface import KnowledgeBaseInterface
from .interface import LessonServiceInterface
from config.settings import settings
from prompts.lesson import SYSTEM_PROMPT


class LessonService(LessonServiceInterface):
    def __init__(self, llm_adapter: BaseLLMAdapter, kb: KnowledgeBaseInterface):
        self.llm_adapter = llm_adapter
        self.kb = kb

    async def generate_lesson(
        self,
        route_id: UUID,
        module_id: str,
        module_name: str,
        module_description: str,
        company_name: str,
        user_prompt: str | None = None
    ) -> Dict[str, Any]:
        """
        Generates a lesson based on module details, grounding references, and return JSON content with TXT/PDF files.
        """
        # 1) Search vector DB for grounding references
        grounded_text = ""
        try:
            hits = await self.kb.query(
                learning_path_id=route_id,
                text=f"{module_name} {module_description}",
                k=5
            )
            if hits:
                grounded_text = "\n\n".join([h.content for h in hits])
        except Exception as e:
            print(f"Warning: RAG query failed during lesson generation: {e}")

        # 2) Construct prompt
        user_msg = (
            f"EMPRESA DEL CLIENTE: {company_name}\n"
            f"MÓDULO: {module_name}\n"
            f"DESCRIPCIÓN: {module_description}\n\n"
        )
        if grounded_text:
            user_msg += f"REFERENCIA / INFORMACIÓN DE RESPALDO:\n{grounded_text}\n\n"
        else:
            user_msg += f"REFERENCIA: (usa conocimiento general sobre {module_name} adaptado al cliente).\n\n"

        if user_prompt:
            user_msg += f"INSTRUCCIÓN ADICIONAL DE REFINAMIENTO (Prioridad alta): {user_prompt}\n"

        # 3) Call LLM
        raw_response = await self.llm_adapter.chat_completion(
            role="lesson_generator",
            prompt=f"{SYSTEM_PROMPT}\n\n{user_msg}"
        )

        # 4) Parse JSON
        lesson_data = self._extract_and_parse_json(raw_response)
        
        # 5) Fallback check
        sections = lesson_data.get("sections", [])
        terms = lesson_data.get("terms", [])
        if not isinstance(sections, list) or len(sections) == 0:
            fallback = self._get_fallback_lesson(module_name, module_description)
            sections = fallback["sections"]
            terms = fallback["terms"]
            
        # 6) Generate TXT file
        txt_content = self._generate_txt_content(module_name, company_name, sections, terms)
        
        # 7) Generate PDF file using Pillow
        pdf_bytes = self._generate_pdf_bytes(module_name, company_name, sections, terms)

        # 8) Save files locally
        local_dir = os.path.join(os.getcwd(), "static", "lessons")
        os.makedirs(local_dir, exist_ok=True)
        
        filename_prefix = f"{route_id}_{module_id}_lesson"
        local_txt_path = os.path.join(local_dir, f"{filename_prefix}.txt")
        local_pdf_path = os.path.join(local_dir, f"{filename_prefix}.pdf")

        with open(local_txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)
        with open(local_pdf_path, "wb") as f:
            f.write(pdf_bytes)

        return {
            "pdfUrl": f"http://localhost:8000/static/lessons/{filename_prefix}.pdf",
            "txtUrl": f"http://localhost:8000/static/lessons/{filename_prefix}.txt",
            "sections": sections,
            "terms": terms
        }

    def _extract_and_parse_json(self, text: str) -> dict:
        """Extracts the first JSON block from text."""
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
            print(f"Error parsing JSON from lesson generator: {e}")
        return {}

    def _get_fallback_lesson(self, module_name: str, module_description: str) -> Dict[str, Any]:
        return {
            "sections": [
                {
                    "heading": f"Introducción a {module_name}",
                    "body": f"En esta sección abordamos los fundamentos de {module_name}. {module_description}. Ejemplo Práctico: Configura y corre un hola mundo de {module_name} en tu máquina."
                },
                {
                    "heading": "Conceptos Clave y Contexto",
                    "body": "Es de vital importancia entender cómo se aplican estos conceptos dentro de la arquitectura técnica. Ejemplo de Código: print('Fundamentos de ' + name)"
                }
            ],
            "terms": [
                {
                    "term": "Fundamentos",
                    "def": f"Conceptos básicos e iniciales del tema {module_name}."
                }
            ]
        }

    def _generate_txt_content(self, module_name: str, company_name: str, sections: List[dict], terms: List[dict]) -> str:
        lines = [
            f"LECCIÓN DE ESTUDIO",
            f"Módulo: {module_name}",
            f"Cliente: {company_name}",
            f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            ""
        ]

        for i, sec in enumerate(sections, start=1):
            lines.append(f"{i}. {sec['heading']}")
            lines.append("-" * len(sec['heading']))
            lines.append(sec['body'])
            lines.append("")

        if terms:
            lines.append("TÉRMINOS CLAVE (GLOSARIO)")
            lines.append("=" * 25)
            for t in terms:
                lines.append(f"* {t['term']}: {t['def']}")
            lines.append("")

        return "\n".join(lines)

    def _generate_pdf_bytes(self, module_name: str, company_name: str, sections: List[dict], terms: List[dict]) -> bytes:
        from PIL import Image, ImageDraw, ImageFont
        width = 800
        image = Image.new("RGB", (width, 4000), color="#FFFFFF")
        draw = ImageDraw.Draw(image)

        # Fonts configuration
        try:
            font_title = ImageFont.truetype("arial.ttf", 20)
            font_header = ImageFont.truetype("arial.ttf", 14)
            font_body = ImageFont.truetype("arial.ttf", 12)
            font_glossary = ImageFont.truetype("arial.ttf", 11)
        except IOError:
            font_title = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_glossary = ImageFont.load_default()

        margin = 50
        y = 50
        line_height = 20
        dark_slate = "#0F172A"
        gray_body = "#334155"
        accent_color = "#3B82F6"

        # Draw Title
        draw.text((margin, y), "LECCIÓN DE ESTUDIO", fill=accent_color, font=font_title)
        y += 35
        draw.text((margin, y), f"Módulo: {module_name}  |  Cliente: {company_name}", fill=dark_slate, font=font_header)
        y += 25
        draw.line([(margin, y), (width - margin, y)], fill="#E2E8F0", width=2)
        y += 30

        def draw_wrapped_text(text: str, start_x: int, start_y: int, max_w: int, fill: str, font) -> int:
            lines = text.split("\n")
            curr_y = start_y
            for line in lines:
                words = line.split(" ")
                curr_line = ""
                for word in words:
                    test_line = curr_line + (" " if curr_line else "") + word
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    w = bbox[2] - bbox[0]
                    if w < max_w:
                        curr_line = test_line
                    else:
                        draw.text((start_x, curr_y), curr_line, fill=fill, font=font)
                        curr_y += line_height
                        curr_line = word
                if curr_line:
                    draw.text((start_x, curr_y), curr_line, fill=fill, font=font)
                    curr_y += line_height
            return curr_y

        # Draw Sections
        for i, sec in enumerate(sections, start=1):
            draw.text((margin, y), f"{i}. {sec['heading']}", fill=accent_color, font=font_header)
            y += 22
            y = draw_wrapped_text(sec["body"], margin + 15, y, width - 2 * margin - 15, dark_slate, font_body)
            y += 25

        # Draw Glossary/Terms
        if terms:
            draw.line([(margin, y), (width - margin, y)], fill="#E2E8F0", width=1)
            y += 25
            draw.text((margin, y), "GLOSARIO DE TÉRMINOS CLAVE", fill=dark_slate, font=font_header)
            y += 25
            for t in terms:
                draw.text((margin + 10, y), f"• {t['term']}:", fill=accent_color, font=font_body)
                y += 18
                y = draw_wrapped_text(t["def"], margin + 25, y, width - 2 * margin - 25, gray_body, font_glossary)
                y += 12

        # Crop to actual height
        y += 20
        final_image = image.crop((0, 0, width, y))
        
        pdf_io = io.BytesIO()
        final_image.save(pdf_io, "PDF", resolution=100.0)
        return pdf_io.getvalue()

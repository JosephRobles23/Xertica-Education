import os
import io
import re
import json
import base64
from html import escape
from pathlib import Path
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, List

from adapters.llm.base import BaseLLMAdapter
from adapters.storage import get_storage_adapter
from services.kb.interface import KnowledgeBaseInterface
from .interface import LessonServiceInterface
from config.settings import settings
from prompts.lesson import SYSTEM_PROMPT
from services.branding import XERTICA_BRAND


class LessonService(LessonServiceInterface):
    def __init__(self, llm_adapter: BaseLLMAdapter, kb: KnowledgeBaseInterface, storage=None):
        self.llm_adapter = llm_adapter
        self.kb = kb
        self.storage = storage or get_storage_adapter()

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
        markdown = lesson_data.get("markdown", "")
        if not isinstance(markdown, str):
            markdown = ""
        if not isinstance(sections, list) or len(sections) == 0:
            fallback = self._get_fallback_lesson(module_name, module_description)
            sections = fallback["sections"]
            terms = fallback["terms"]
            
        # 6) Generate TXT file
        txt_content = self._generate_txt_content(module_name, company_name, sections, terms)
        
        # 7) Generate PDF file using Pillow
        pdf_bytes = self._generate_pdf_bytes(module_name, company_name, sections, terms)

        # 8) Persist artifacts via storage adapter (ADR-0022): bucket con
        # fallback local en dev; el path sigue la convención del Spine.
        filename_prefix = f"{route_id}_{module_id}_lesson"
        base_path = f"{route_id}/{module_id}/lesson"
        txt_url = await self.storage.upload_file(
            settings.storage_bucket, f"{base_path}/{filename_prefix}.txt", txt_content.encode("utf-8")
        )
        pdf_url = await self.storage.upload_file(
            settings.storage_bucket, f"{base_path}/{filename_prefix}.pdf", pdf_bytes
        )

        return {
            "pdfUrl": pdf_url,
            "txtUrl": txt_url,
            "storagePath": f"{base_path}/{filename_prefix}.pdf",
            "groundingStatus": "kb-grounded" if grounded_text else "module-grounded",
            "sections": sections,
            "terms": terms,
            "markdown": markdown,
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

    def _build_lesson_pdf_html(
        self, module_name: str, company_name: str, sections: List[dict], terms: List[dict]
    ) -> str:
        """Build the branded, printable HTML document used by the PDF renderer."""
        asset_path = Path(__file__).resolve().parents[2] / "assets" / "xertica-favicon.png"
        logo_uri = ""
        if asset_path.exists():
            logo_uri = "data:image/png;base64," + base64.b64encode(asset_path.read_bytes()).decode("ascii")

        section_cards = []
        accents = ["#5c3a8a", "#1899af", "#c45baa", "#2e8b5a", "#d9503b", "#e8651e"]
        for index, section in enumerate(sections, start=1):
            heading = escape(str(section.get("heading", "")))
            body = escape(str(section.get("body", ""))).replace("\n", "<br>")
            accent = accents[(index - 1) % len(accents)]
            section_cards.append(
                f'<article class="lesson-card" style="--accent:{accent}">'
                f'<div class="card-index">{index:02d}</div>'
                f'<div><h2>{heading}</h2><p>{body}</p></div></article>'
            )

        glossary = ""
        if terms:
            glossary_items = "".join(
                f'<div class="term"><dt>{escape(str(term.get("term", "")))}</dt>'
                f'<dd>{escape(str(term.get("def", "")))}</dd></div>'
                for term in terms
            )
            glossary = f'<section class="glossary"><p class="eyebrow">VOCABULARIO</p><h2>Glosario esencial</h2><dl>{glossary_items}</dl></section>'

        logo = f'<img src="{logo_uri}" alt="Xertica.ai" class="logo-mark">' if logo_uri else ""
        return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:18mm 16mm 17mm; @bottom-left {{ content:"Xertica Education · Documento de aprendizaje"; color:#5c574f; font-size:8pt; }} @bottom-right {{ content:counter(page); color:#1a1814; font-size:9pt; }} }}
:root {{ --surface:#fffef8; --cream:#f2edd8; --ink:#1a1814; --muted:#5c574f; --purple:#5c3a8a; --cyan:#1899af; --pink:#c45baa; --green:#2e8b5a; --red:#d9503b; --yellow:#faf338; --orange:#e8651e; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--surface); color:var(--ink); font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:10.5pt; line-height:1.55; }}
.masthead {{ display:flex; justify-content:space-between; align-items:center; padding-bottom:14px; border-bottom:2px solid var(--ink); }}
.brand {{ display:flex; align-items:center; gap:9px; font-weight:800; font-size:16pt; letter-spacing:-.06em; }} .logo-mark {{ width:34px; height:34px; object-fit:contain; }}
.brand-dot {{ color:var(--pink); }} .edition {{ color:var(--muted); font-size:8pt; letter-spacing:.16em; text-transform:uppercase; }}
.geometry {{ display:grid; grid-template-columns:2fr 1fr 1fr 1fr; height:13px; margin:20px 0 32px; }} .geometry i:nth-child(1){{background:var(--purple)}} .geometry i:nth-child(2){{background:var(--cyan)}} .geometry i:nth-child(3){{background:var(--yellow)}} .geometry i:nth-child(4){{background:var(--green)}}
.eyebrow {{ margin:0 0 9px; color:var(--purple); font-size:8pt; font-weight:800; letter-spacing:.16em; }}
h1 {{ max-width:610px; margin:0; font-size:32pt; line-height:1.02; letter-spacing:-.065em; }} .subtitle {{ margin:14px 0 25px; max-width:560px; color:var(--muted); font-size:12pt; }}
.meta {{ display:flex; gap:10px; margin-bottom:29px; }} .pill {{ padding:5px 9px; border:1px solid #d7d0bd; border-radius:999px; color:var(--muted); font-size:8pt; text-transform:uppercase; letter-spacing:.08em; }}
.lesson-card {{ display:grid; grid-template-columns:47px 1fr; gap:14px; break-inside:avoid; margin:0 0 13px; padding:17px 19px 18px; border:1px solid #ded8c8; border-left:5px solid var(--accent); background:#fff; }}
.card-index {{ color:var(--accent); font-size:13pt; font-weight:800; letter-spacing:-.04em; }} .lesson-card h2 {{ margin:0 0 6px; font-size:14pt; letter-spacing:-.035em; }} .lesson-card p {{ margin:0; color:#3d3933; }}
.glossary {{ break-inside:avoid; margin-top:29px; padding:21px; background:var(--cream); border-top:5px solid var(--yellow); }} .glossary h2 {{ margin:0 0 15px; font-size:20pt; letter-spacing:-.05em; }} .glossary dl {{ display:grid; grid-template-columns:1fr 1fr; gap:13px 22px; margin:0; }} .term {{ break-inside:avoid; }} .term dt {{ color:var(--purple); font-weight:800; }} .term dd {{ margin:2px 0 0; color:#4b463e; font-size:9pt; }}
.closing {{ margin-top:30px; padding-top:12px; border-top:1px solid #d7d0bd; color:var(--muted); font-size:8.5pt; }}
</style></head><body>
<header class="masthead"><div class="brand">{logo}<span>Xertica<span class="brand-dot">.</span>ai</span></div><div class="edition">Lesson · {escape(company_name)}</div></header>
<div class="geometry"><i></i><i></i><i></i><i></i></div>
<main><p class="eyebrow">LECCIÓN DE ESTUDIO</p><h1>{escape(module_name)}</h1><p class="subtitle">Una lectura visual para comprender los conceptos clave, conectarlos y llevarlos a la práctica.</p><div class="meta"><span class="pill">Xertica Education</span><span class="pill">Contenido guiado</span><span class="pill">{len(sections)} secciones</span></div>
{''.join(section_cards)}{glossary}<p class="closing">Aprende con contexto, claridad y trazabilidad. Este material fue generado para acompañar tu ruta de aprendizaje.</p></main></body></html>"""

    def _generate_pdf_bytes(self, module_name: str, company_name: str, sections: List[dict], terms: List[dict]) -> bytes:
        """Render the branded HTML template to PDF, with a Pillow safety fallback."""
        html = self._build_lesson_pdf_html(module_name, company_name, sections, terms)
        try:
            from weasyprint import HTML
            return HTML(string=html).write_pdf()
        except Exception as error:
            print(f"Warning: branded HTML PDF renderer failed; using legacy fallback: {error}")
            return self._generate_legacy_pdf_bytes(module_name, company_name, sections, terms)

    def _generate_legacy_pdf_bytes(self, module_name: str, company_name: str, sections: List[dict], terms: List[dict]) -> bytes:
        """Minimal fallback kept for environments without HTML/PDF system libraries."""
        from PIL import Image, ImageDraw, ImageFont
        image = Image.new("RGB", (800, 4000), color=XERTICA_BRAND["surface"])
        draw = ImageDraw.Draw(image)
        try:
            font_title = ImageFont.truetype("arial.ttf", 28)
            font_header = ImageFont.truetype("arial.ttf", 16)
            font_body = ImageFont.truetype("arial.ttf", 12)
        except IOError:
            font_title = font_header = font_body = ImageFont.load_default()
        y, margin = 55, 50
        draw.text((margin, y), "Xertica.ai", fill=XERTICA_BRAND["ink"], font=font_title); y += 45
        draw.text((margin, y), module_name, fill=XERTICA_BRAND["morado"], font=font_header); y += 35
        for index, section in enumerate(sections, start=1):
            draw.text((margin, y), f"{index:02d}  {section.get('heading', '')}", fill=XERTICA_BRAND["ink"], font=font_header); y += 25
            draw.text((margin, y), str(section.get("body", ""))[:170], fill=XERTICA_BRAND["ink_soft"], font=font_body); y += 35
        output = io.BytesIO(); image.crop((0, 0, 800, min(y + 35, 4000))).save(output, "PDF", resolution=100.0); return output.getvalue()

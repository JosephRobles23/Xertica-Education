import os
import io
import re
import json
import base64
import httpx
from uuid import UUID
from datetime import datetime, timezone
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

from adapters.llm.base import BaseLLMAdapter
from adapters.storage import get_storage_adapter
from services.kb.interface import KnowledgeBaseInterface
from .interface import QuizServiceInterface
from config.settings import settings
from prompts.quiz import SYSTEM_PROMPT


class QuizService(QuizServiceInterface):
    def __init__(self, llm_adapter: BaseLLMAdapter, kb: KnowledgeBaseInterface, storage=None):
        self.llm_adapter = llm_adapter
        self.kb = kb
        self.storage = storage or get_storage_adapter()

    async def generate_quiz(
        self,
        route_id: UUID,
        module_id: str,
        module_name: str,
        module_description: str,
        company_name: str,
        user_prompt: str | None = None
    ) -> Dict[str, Any]:
        """
        Generates a quiz based on module details, grounding references, and saves TXT/PDF.
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
            print(f"Warning: RAG query failed during quiz generation: {e}")

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
            role="quiz_generator",
            prompt=f"{SYSTEM_PROMPT}\n\n{user_msg}"
        )

        # 4) Parse JSON
        quiz_data = self._extract_and_parse_json(raw_response)
        questions = quiz_data.get("questions", [])
        if not isinstance(questions, list) or len(questions) == 0:
            # Fallback mock questions in case of failure or empty list
            questions = self._get_fallback_questions(module_name)

        # 5) Generate TXT file
        txt_content = self._generate_txt_content(module_name, company_name, questions)
        
        # 6) Generate PDF file using Pillow
        pdf_bytes = self._generate_pdf_bytes(module_name, company_name, questions)

        # 7) Persist artifacts via storage adapter (ADR-0022): bucket con
        # fallback local en dev; el path sigue la convención del Spine.
        filename_prefix = f"{route_id}_{module_id}_quiz"
        base_path = f"{route_id}/{module_id}/quiz"
        txt_url = await self.storage.upload_file(
            settings.storage_bucket, f"{base_path}/{filename_prefix}.txt", txt_content.encode("utf-8")
        )
        pdf_url = await self.storage.upload_file(
            settings.storage_bucket, f"{base_path}/{filename_prefix}.pdf", pdf_bytes
        )

        # 8) Return URLs and questions
        return {
            "pdfUrl": pdf_url,
            "txtUrl": txt_url,
            "storagePath": f"{base_path}/{filename_prefix}.pdf",
            "groundingStatus": "kb-grounded" if grounded_text else "module-grounded",
            "questions": questions
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
            print(f"Error parsing JSON from quiz generator: {e}")
        return {}

    def _get_fallback_questions(self, module_name: str) -> List[Dict[str, Any]]:
        return [
            {
                "q": f"¿Cuál es el objetivo principal del módulo '{module_name}'?",
                "opts": [
                    "Alinear los conceptos técnicos con las metas del negocio",
                    "Aprender sintaxis de memoria sin comprender su uso",
                    "Reemplazar el juicio humano por herramientas automáticas",
                    "Evitar realizar cualquier tipo de práctica real"
                ],
                "correct": 0,
                "explanation": "El objetivo principal siempre es alinear los fundamentos con las metas del negocio para tomar mejores decisiones."
            }
        ]

    def _generate_txt_content(self, module_name: str, company_name: str, questions: List[dict]) -> str:
        lines = [
            f"EVALUACIÓN DE CONOCIMIENTO (QUIZ)",
            f"Módulo: {module_name}",
            f"Cliente: {company_name}",
            f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            ""
        ]

        for i, q in enumerate(questions, start=1):
            lines.append(f"Pregunta {i}: {q['q']}")
            for oi, opt in enumerate(q['opts']):
                letter = chr(65 + oi)
                lines.append(f"  {letter}) {opt}")
            
            correct_letter = chr(65 + q['correct'])  # correct index to A, B, C, D
            lines.append("")
            lines.append(f"  [Respuesta Correcta: {correct_letter}]")
            lines.append(f"  [Explicación: {q.get('explanation', 'Sin explicación disponible.')}]")
            lines.append("-" * 70)
            lines.append("")

        return "\n".join(lines)

    def _generate_pdf_bytes(self, module_name: str, company_name: str, questions: List[dict]) -> bytes:
        # Create a clean white canvas for printing (width 800, height 3200 max, crop later)
        width = 800
        image = Image.new("RGB", (width, 3200), color="#FFFFFF")
        draw = ImageDraw.Draw(image)

        # Fonts configuration
        try:
            font_title = ImageFont.truetype("arial.ttf", 20)
            font_header = ImageFont.truetype("arial.ttf", 14)
            font_body = ImageFont.truetype("arial.ttf", 12)
            font_explanation = ImageFont.truetype("arial.ttf", 11)
        except IOError:
            # Fallback to default
            font_title = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_explanation = ImageFont.load_default()

        # Margins & colors
        margin = 50
        y = 50
        line_height = 20
        dark_slate = "#0F172A"
        gray_body = "#334155"
        correct_green = "#16A34A"
        accent_color = "#3B82F6"

        # Draw Title
        draw.text((margin, y), "EVALUACIÓN DE CONOCIMIENTO (QUIZ)", fill=accent_color, font=font_title)
        y += 35
        draw.text((margin, y), f"Módulo: {module_name}  |  Cliente: {company_name}", fill=dark_slate, font=font_header)
        y += 25
        draw.line([(margin, y), (width - margin, y)], fill="#E2E8F0", width=2)
        y += 30

        # Text wrapping helper
        def draw_wrapped_text(text: str, start_x: int, start_y: int, max_w: int, fill: str, font) -> int:
            words = text.split(" ")
            curr_y = start_y
            curr_line = ""
            for word in words:
                test_line = curr_line + (" " if curr_line else "") + word
                # Measure text width
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

        # Draw Questions
        for i, q in enumerate(questions, start=1):
            # Question Header
            draw.text((margin, y), f"Pregunta {i}:", fill=accent_color, font=font_header)
            y += line_height
            
            # Question Body
            y = draw_wrapped_text(q["q"], margin + 15, y, width - 2 * margin - 15, dark_slate, font_body)
            y += 8
            
            # Options
            for oi, opt in enumerate(q["opts"]):
                letter = chr(65 + oi)
                is_correct = oi == q["correct"]
                opt_color = correct_green if is_correct else gray_body
                opt_font = font_body
                opt_text = f"{letter}) {opt}"
                if is_correct:
                    opt_text += "  ✓"
                y = draw_wrapped_text(opt_text, margin + 30, y, width - 2 * margin - 30, opt_color, opt_font)
            
            y += 10
            # Explanation (italic look or distinct color)
            exp_text = f"Explicación: {q.get('explanation', 'Sin explicación.')}"
            y = draw_wrapped_text(exp_text, margin + 30, y, width - 2 * margin - 30, "#64748B", font_explanation)
            
            y += 15
            draw.line([(margin, y), (width - margin, y)], fill="#F1F5F9", width=1)
            y += 25

        # Crop to actual height
        y += 20
        final_image = image.crop((0, 0, width, y))
        
        # Save to PDF bytes
        pdf_io = io.BytesIO()
        final_image.save(pdf_io, "PDF", resolution=100.0)
        return pdf_io.getvalue()

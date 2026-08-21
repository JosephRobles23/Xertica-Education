import unittest
import os
import sys
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.storage.memory import InMemoryStorageAdapter
from config.settings import settings
from services.lesson.service import LessonService

class TestLessonGeneration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.llm_mock = MagicMock()
        self.llm_mock.chat_completion = AsyncMock()
        self.kb_mock = MagicMock()
        self.kb_mock.query = AsyncMock()
        self.storage = InMemoryStorageAdapter()
        self.service = LessonService(llm_adapter=self.llm_mock, kb=self.kb_mock, storage=self.storage)

    async def test_lesson_generation_flow(self):
        # Mock LLM response containing JSON sections and terms
        llm_response = """
        ```json
        {
          "sections": [
            {
              "heading": "Conceptos Fundamentales",
              "body": "Esta sección describe la lección detallada sobre el tema."
            }
          ],
          "terms": [
            {
              "term": "Python",
              "def": "Un lenguaje de programación interpretado de alto nivel."
            }
          ]
        }
        ```
        """
        self.llm_mock.chat_completion.return_value = llm_response
        self.kb_mock.query.return_value = [
            MagicMock(content="Python documentation grounding info")
        ]

        route_id = uuid4()
        res = await self.service.generate_lesson(
            route_id=route_id,
            module_id="r1m1",
            module_name="Introducción",
            module_description="Fundamentos de Python",
            company_name="Google"
        )

        # Assertions
        self.assertIn("sections", res)
        self.assertIn("terms", res)
        self.assertEqual(len(res["sections"]), 1)
        self.assertEqual(res["sections"][0]["heading"], "Conceptos Fundamentales")
        self.assertEqual(len(res["terms"]), 1)
        self.assertEqual(res["terms"][0]["term"], "Python")
        self.assertIn("pdfUrl", res)
        self.assertIn("txtUrl", res)
        self.assertEqual(res["groundingStatus"], "kb-grounded")

        # Los artefactos van al storage adapter (ADR-0022) con path del Spine.
        base_path = f"{route_id}/r1m1/lesson"
        filename_prefix = f"{route_id}_r1m1_lesson"
        self.assertEqual(res["storagePath"], f"{base_path}/{filename_prefix}.pdf")
        self.assertIn((settings.storage_bucket, f"{base_path}/{filename_prefix}.txt"), self.storage._store)
        self.assertIn((settings.storage_bucket, f"{base_path}/{filename_prefix}.pdf"), self.storage._store)

    def test_fallback_lesson(self):
        fallback = self.service._get_fallback_lesson("Módulo de prueba", "Alguna descripción de prueba")
        self.assertEqual(len(fallback["sections"]), 2)
        self.assertEqual(fallback["sections"][0]["heading"], "Introducción a Módulo de prueba")
        self.assertEqual(len(fallback["terms"]), 1)

    def test_json_extraction(self):
        valid_json_str = '{"sections": [{"heading": "Header", "body": "Body Text"}], "terms": [{"term": "T", "def": "D"}]}'
        parsed = self.service._extract_and_parse_json(f"Some prefix ```json\n{valid_json_str}\n``` suffix")
        self.assertEqual(parsed.get("sections")[0]["heading"], "Header")
        self.assertEqual(parsed.get("terms")[0]["term"], "T")

    def test_json_extraction_preserves_optional_mermaid_markdown(self):
        valid_json_str = '{"sections": [], "terms": [], "markdown": "## Mapa\\n\\n```mermaid\\nmindmap\\n  root((Tema))\\n```"}'
        parsed = self.service._extract_and_parse_json(valid_json_str)
        self.assertIn("```mermaid", parsed.get("markdown", ""))

    def test_lesson_pdf_uses_branded_html_template(self):
        html = self.service._build_lesson_pdf_html(
            "Fundamentos de IA", "Xertica", [{"heading": "Conceptos", "body": "Texto"}], [{"term": "IA", "def": "Definición"}]
        )
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("#fffef8", html)
        self.assertIn("Xertica.ai", html)
        self.assertIn("data:image/png;base64", html)
        self.assertIn("lesson-card", html)

    def test_lesson_pdf_is_a_pdf(self):
        pdf = self.service._generate_pdf_bytes(
            "Fundamentos", "Xertica", [{"heading": "Conceptos", "body": "Texto"}], []
        )
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_mermaid_labels_are_quoted(self):
        # Paréntesis y comas sin comillas rompen el parser de Mermaid: deben quedar entrecomillados.
        src = "flowchart LR\n  A[Datos (Ventas, Gastos)] --> B[Análisis]"
        safe = self.service._quote_mermaid_labels(src)
        self.assertIn('A["Datos (Ventas, Gastos)"]', safe)
        self.assertIn('B["Análisis"]', safe)

    def test_mermaid_already_quoted_is_untouched(self):
        src = 'flowchart LR\n  A["Ya seguro"] --> B["Fin"]'
        self.assertEqual(self.service._quote_mermaid_labels(src), src)

    def test_extract_mermaid_from_markdown(self):
        md = "## Mapa\n\n```mermaid\nflowchart LR\n  A[Inicio] --> B[Fin]\n```\n\nTexto"
        block = self.service._extract_mermaid(md)
        self.assertIsNotNone(block)
        self.assertIn("flowchart LR", block)
        self.assertIsNone(self.service._extract_mermaid("## Sin diagrama"))

    def test_sanitize_mermaid_in_markdown_quotes_labels(self):
        md = "```mermaid\nflowchart LR\n  A[Datos (a, b)] --> B[Fin]\n```"
        out = self.service._sanitize_mermaid_in_markdown(md)
        self.assertIn('A["Datos (a, b)"]', out)

if __name__ == "__main__":
    unittest.main()

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

if __name__ == "__main__":
    unittest.main()

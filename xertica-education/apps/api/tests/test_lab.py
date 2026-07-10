import os
import sys
import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.storage.memory import InMemoryStorageAdapter
from config.settings import settings
from services.lab.service import LabService


class TestLabGeneration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.llm_mock = MagicMock()
        self.llm_mock.chat_completion = AsyncMock()
        self.kb_mock = MagicMock()
        self.kb_mock.query = AsyncMock()
        self.storage = InMemoryStorageAdapter()
        self.service = LabService(llm_adapter=self.llm_mock, kb=self.kb_mock, storage=self.storage)

    async def test_lab_generation_flow(self):
        llm_response = """
        ```json
        {
          "title": "Laboratorio con Gemini",
          "classroomText": "🧪 Laboratorio: Laboratorio con Gemini\\n\\nUsa Gemini para mejorar una propuesta real del cliente.\\n\\n1. Desafío\\nDefine la propuesta que quieres mejorar.\\n\\n2. Preparar el prompt\\nDefine el objetivo y el contexto del cliente.\\n\\nEntrega\\nUna propuesta refinada.",
          "objective": "Aplicar Gemini a un caso del cliente",
          "scenario": "Un equipo necesita preparar una propuesta mejorada.",
          "estimatedTimeMinutes": 35,
          "difficulty": "intermediate",
          "tools": [
            { "name": "Gemini", "purpose": "Idear y refinar entregables", "url": "https://ai.google.dev/gemini-api/docs" }
          ],
          "prerequisites": ["Leer el módulo"],
          "instructions": [
            {
              "step": 1,
              "title": "Preparar el prompt",
              "description": "Define el objetivo y el contexto del cliente.",
              "expectedResult": "Prompt listo",
              "tip": "Incluye audiencia y tono"
            }
          ],
          "deliverable": {
            "description": "Una propuesta refinada",
            "format": "Documento",
            "successCriteria": ["Aterriza el caso del cliente"]
          },
          "reflectionQuestions": ["¿Qué mejoró con Gemini?"],
          "sourceReferences": [
            { "title": "Docs de Gemini", "url": "https://ai.google.dev/gemini-api/docs" }
          ],
          "safetyNotes": ["No compartas datos sensibles."]
        }
        ```
        """
        self.llm_mock.chat_completion.return_value = llm_response
        self.kb_mock.query.return_value = [
            MagicMock(
                content="Gemini sirve para idear, resumir y refinar propuestas.",
                citation=MagicMock(title="Docs Gemini", url="https://ai.google.dev/gemini-api/docs", score=0.92),
            )
        ]

        route_id = uuid4()
        result = await self.service.generate_lab(
            route_id=route_id,
            module_id="r1m3",
            route_name="Ruta Gemini",
            route_objective="Ensenar Gemini",
            module_name="Laboratorio de Gemini",
            module_description="Practica con prompts y refinamiento",
            module_objective="Aplicar Gemini",
            company_name="Xertica",
            customer_context={"industry": "Educacion"},
            approved_sources=[
                {
                    "id": "src-1",
                    "title": "Docs de Gemini",
                    "url": "https://ai.google.dev/gemini-api/docs",
                    "status": "approved",
                    "verified": True,
                }
            ],
        )

        self.assertEqual(result["title"], "Laboratorio con Gemini")
        self.assertIn("Usa Gemini", result["classroomText"])
        self.assertEqual(result["difficulty"], "intermediate")
        self.assertEqual(len(result["instructions"]), 1)
        self.assertEqual(result["steps"][0]["title"], "Preparar el prompt")
        self.assertIn("txtUrl", result)
        self.assertIn("pdfUrl", result)
        self.assertIn("jsonUrl", result)

        self.assertEqual(result["groundingStatus"], "kb-grounded")

        # Los artefactos van al storage adapter (ADR-0022) con path del Spine.
        base_path = f"{route_id}/r1m3/lab"
        filename_prefix = f"{route_id}_r1m3_lab"
        self.assertEqual(result["storagePath"], f"{base_path}/{filename_prefix}.pdf")
        for extension in ("txt", "pdf", "json"):
            self.assertIn(
                (settings.storage_bucket, f"{base_path}/{filename_prefix}.{extension}"),
                self.storage._store,
            )
        txt_bytes = self.storage._store[(settings.storage_bucket, f"{base_path}/{filename_prefix}.txt")]
        self.assertIn("Usa Gemini", txt_bytes.decode("utf-8"))

    def test_fallback_lab_uses_detected_tool(self):
        fallback = self.service._fallback_lab(
            module_name="Canva aplicado",
            module_description="Disenar una pieza de comunicacion",
            module_objective="Aplicar Canva al contexto del cliente",
            approved_sources=[],
            detected_tools=[{"name": "Canva", "url": "https://www.canva.com/help/"}],
        )
        self.assertEqual(fallback["tools"][0]["name"], "Canva")
        self.assertIn("Laboratorio", fallback["classroomText"])
        self.assertGreaterEqual(len(fallback["instructions"]), 3)


if __name__ == "__main__":
    unittest.main()

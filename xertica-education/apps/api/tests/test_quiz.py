import unittest
import io
import os
import sys
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.quiz.service import QuizService

class TestQuizGeneration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.llm_mock = MagicMock()
        self.llm_mock.chat_completion = AsyncMock()
        self.kb_mock = MagicMock()
        self.kb_mock.query = AsyncMock()
        self.service = QuizService(llm_adapter=self.llm_mock, kb=self.kb_mock)

    async def test_quiz_generation_flow(self):
        # Mock LLM response containing JSON questions
        llm_response = """
        ```json
        {
          "questions": [
            {
              "q": "What is 2+2?",
              "opts": ["3", "4", "5", "6"],
              "correct": 1,
              "explanation": "Because basic math tells us 2+2=4."
            }
          ]
        }
        ```
        """
        self.llm_mock.chat_completion.return_value = llm_response
        self.kb_mock.query.return_value = [
            MagicMock(content="Grounding math details")
        ]

        route_id = uuid4()
        res = await self.service.generate_quiz(
            route_id=route_id,
            module_id="r1m1",
            module_name="Introducción",
            module_description="Fundamentos de Python",
            company_name="Google"
        )

        # Assertions
        self.assertIn("questions", res)
        self.assertEqual(len(res["questions"]), 1)
        self.assertEqual(res["questions"][0]["q"], "What is 2+2?")
        self.assertIn("pdfUrl", res)
        self.assertIn("txtUrl", res)
        
        # Verify files were created
        filename_prefix = f"{route_id}_r1m1_quiz"
        local_dir = os.path.join(os.getcwd(), "static", "quizzes")
        local_txt_path = os.path.join(local_dir, f"{filename_prefix}.txt")
        local_pdf_path = os.path.join(local_dir, f"{filename_prefix}.pdf")
        
        self.assertTrue(os.path.exists(local_txt_path))
        self.assertTrue(os.path.exists(local_pdf_path))

        # Cleanup files
        try:
            os.remove(local_txt_path)
            os.remove(local_pdf_path)
        except Exception:
            pass

    def test_fallback_questions(self):
        fallback = self.service._get_fallback_questions("Módulo de prueba")
        self.assertEqual(len(fallback), 1)
        self.assertIn("Módulo de prueba", fallback[0]["q"])

    def test_json_extraction(self):
        valid_json_str = '{"questions": [{"q": "Test", "opts": ["a", "b", "c", "d"], "correct": 0}]}'
        parsed = self.service._extract_and_parse_json(f"Some text before ```json\n{valid_json_str}\n``` and after")
        self.assertEqual(parsed.get("questions")[0]["q"], "Test")

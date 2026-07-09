import unittest
import io
import os
import base64
import asyncio
from uuid import uuid4
from unittest.mock import patch, MagicMock
from PIL import Image

# Add root folder to sys.path so we can import from apps/api
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.infographic.service import (
    extract_grounded_points,
    build_image_prompt,
    build_fallback_prompt,
    InfographicService
)

class TestInfographicGeneration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sources = [
            {"title": "Intro logic", "quote": "Reasoning models are cool."},
            {"title": "Deep Dive", "quote": "They solve complex problems step by step."}
        ]
        self.company = "OpenAI"
        self.service = InfographicService()

    def test_extract_grounded_points_respects_budget(self):
        # Total words in sources is around 15 words
        # Budget of 5 words
        points = extract_grounded_points(self.sources, word_budget=5)
        text = " ".join(points)
        word_count = len(text.split())
        self.assertLessEqual(word_count, 10) # rough check, budget limits
        self.assertTrue(len(points) >= 1)

    def test_build_prompt_includes_branding(self):
        points = ["Logic unit", "Flow diagram"]
        prompt = build_image_prompt(points, self.company)
        self.assertIn("OpenAI", prompt)
        self.assertIn("logotipo oficial", prompt)
        self.assertIn("paleta de colores", prompt)

    def test_fallback_prompt_removes_logo(self):
        points = ["Logic unit", "Flow diagram"]
        prompt = build_fallback_prompt(points, self.company)
        self.assertIn("OpenAI", prompt)
        self.assertNotIn("logotipo oficial", prompt) # Should not request logo

    def test_convert_png_to_pdf(self):
        # Create a simple red PNG in memory
        img = Image.new("RGB", (100, 100), color="red")
        img_io = io.BytesIO()
        img.save(img_io, "PNG")
        png_bytes = img_io.getvalue()
        
        # Test converting PNG bytes to PDF bytes
        image = Image.open(io.BytesIO(png_bytes))
        pdf_io = io.BytesIO()
        image.save(pdf_io, "PDF", resolution=100.0)
        pdf_bytes = pdf_io.getvalue()
        
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    @patch("config.settings.settings.openai_api_key", "placeholder-key")
    @patch("config.settings.settings.supabase_url", "placeholder-url")
    @patch("config.settings.settings.supabase_key", "placeholder-key")
    async def test_mock_generation_flow(self):
        # Running when key is placeholder should fail with ValueError
        comp_id = uuid4()
        with self.assertRaises(ValueError):
            await self.service.generate_infographic(
                component_id=comp_id,
                sources=self.sources,
                company_name=self.company,
                word_budget=100
            )

    @patch("httpx.AsyncClient.post")
    @patch("config.settings.settings.openai_api_key", "real-valid-api-key")
    @patch("config.settings.settings.supabase_url", "placeholder-url")
    @patch("config.settings.settings.supabase_key", "placeholder-key")
    async def test_retry_mechanism_on_moderation_error(self, mock_post):
        # Mock standard Image response
        mock_image_b64 = base64.b64encode(b"fake-png-data").decode("utf-8")
        
        # Mock 1st call: safety violation error
        # Mock 2nd call: success response
        response_1 = MagicMock()
        response_1.status_code = 400
        response_1.text = "Your prompt was blocked by safety policy (trademark/logo violation)."
        response_1.request = MagicMock()
        
        response_2 = MagicMock()
        response_2.status_code = 200
        response_2.json.return_value = {
            "created": 12345,
            "data": [{"b64_json": mock_image_b64}]
        }
        
        mock_post.side_effect = [response_1, response_2]
        
        # Mock Pillow Image loading to bypass real PNG check
        mock_image = MagicMock()
        mock_image.mode = 'RGB'
        
        with patch("PIL.Image.open") as mock_open:
            mock_open.return_value = mock_image
            
            comp_id = uuid4()
            res = await self.service.generate_infographic(
                component_id=comp_id,
                sources=self.sources,
                company_name=self.company,
                word_budget=100
            )
            
            self.assertTrue(res["requires_manual_review"]) # Retried successfully with fallback
            self.assertEqual(mock_post.call_count, 2)
            
            # 1st call prompt should contain the logo requirement
            first_call_payload = mock_post.call_args_list[0][1]["json"]
            self.assertIn("logotipo oficial", first_call_payload["prompt"])
            
            # 2nd call prompt should NOT contain the logo requirement
            second_call_payload = mock_post.call_args_list[1][1]["json"]
            self.assertNotIn("logotipo oficial", second_call_payload["prompt"])

if __name__ == "__main__":
    unittest.main()

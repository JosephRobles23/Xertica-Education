import unittest
import io
import os
import base64
import asyncio
import tempfile
import httpx
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from PIL import Image
from fastapi.testclient import TestClient

# Add root folder to sys.path so we can import from apps/api
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.infographic.service import (
    extract_grounded_points,
    build_image_prompt,
    build_fallback_prompt,
    InfographicGenerationError,
    InfographicService
)
import main
from config.dependencies import get_infographic_service, get_route_service, get_video_service

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
        
        with tempfile.TemporaryDirectory() as tmpdir, patch("os.getcwd", return_value=tmpdir), patch("PIL.Image.open") as mock_open:
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

    @patch("asyncio.sleep", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.post")
    @patch("config.settings.settings.openai_api_key", "real-valid-api-key")
    @patch("config.settings.settings.supabase_url", "placeholder-url")
    @patch("config.settings.settings.supabase_key", "placeholder-key")
    async def test_retries_transient_ssl_read_error(self, mock_post, mock_sleep):
        mock_image_b64 = base64.b64encode(b"fake-png-data").decode("utf-8")
        request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "created": 12345,
            "data": [{"b64_json": mock_image_b64}]
        }

        mock_post.side_effect = [
            httpx.ReadError("[SSL] record layer failure", request=request),
            response,
        ]

        mock_image = MagicMock()
        mock_image.mode = 'RGB'

        with tempfile.TemporaryDirectory() as tmpdir, patch("os.getcwd", return_value=tmpdir), patch("PIL.Image.open") as mock_open:
            mock_open.return_value = mock_image

            comp_id = uuid4()
            res = await self.service.generate_infographic(
                component_id=comp_id,
                sources=self.sources,
                company_name=self.company,
                word_budget=100
            )

        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_awaited_once_with(1)
        self.assertEqual(res["model"], "gpt-image-2")

    def test_endpoint_returns_clear_error_and_preserves_previous_infographic(self):
        class FakeRouteService:
            def __init__(self):
                self.update_called = False

            async def get_route(self, route_id):
                return {
                    "id": route_id,
                    "name": "Ruta con infografía",
                    "customerContext": {},
                    "modules": [],
                    "pack": {
                        "infografia": {
                            "title": "Infografía anterior",
                            "imageUrl": "http://localhost:8000/static/infographics/previous.png",
                            "pdfUrl": "http://localhost:8000/static/infographics/previous.pdf",
                        }
                    },
                }

            async def update_route(self, route_id, data):
                self.update_called = True
                return {"id": route_id, **data}

        class FailingInfographicService:
            async def generate_infographic(self, **kwargs):
                raise InfographicGenerationError(
                    "No se pudo generar la infografía por un fallo temporal del proveedor de imágenes.",
                    retryable=True,
                )

        route_service = FakeRouteService()
        main.app.dependency_overrides[get_route_service] = lambda: route_service
        main.app.dependency_overrides[get_infographic_service] = lambda: FailingInfographicService()
        try:
            client = TestClient(main.app)
            response = client.post("/learning-paths/01/infographic/regenerate", json={})
        finally:
            main.app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 503)
        self.assertFalse(route_service.update_called)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "infographic_generation_failed")
        self.assertTrue(detail["previous_asset_preserved"])
        self.assertTrue(detail["retryable"])

    def test_video_job_can_be_created_while_infographic_regenerates(self):
        route_id = "13acb8bf-d291-4797-8d89-c6ab42485922"
        video_job_id = uuid4()

        class FakeRouteService:
            def __init__(self):
                self.update_payloads = []

            async def get_route(self, _route_id):
                return {
                    "id": route_id,
                    "name": "Ruta concurrente",
                    "customerContext": {},
                    "modules": [
                        {
                            "id": "r1m1",
                            "name": "Modulo uno",
                            "description": "Modulo con video e infografia.",
                            "contents": [
                                {"kind": "video", "status": "borrador", "summary": "Video"},
                                {"kind": "infografia", "status": "borrador", "summary": "Infografia"},
                            ],
                        }
                    ],
                    "pack": {
                        "infografia": {
                            "title": "Infografía anterior",
                            "imageUrl": "http://localhost:8000/static/infographics/previous.png",
                            "pdfUrl": "http://localhost:8000/static/infographics/previous.pdf",
                        }
                    },
                }

            async def update_route(self, route_id, data):
                self.update_payloads.append(data)
                return {"id": route_id, **data}

        class SlowInfographicService:
            async def generate_infographic(self, **kwargs):
                await asyncio.sleep(0.05)
                return {
                    "local_png_url": "http://localhost:8000/static/infographics/new.png",
                    "local_pdf_url": "http://localhost:8000/static/infographics/new.pdf",
                }

        class FakeVideoService:
            async def generate_video(self, **kwargs):
                return video_job_id

        route_service = FakeRouteService()
        main.app.dependency_overrides[get_route_service] = lambda: route_service
        main.app.dependency_overrides[get_infographic_service] = lambda: SlowInfographicService()
        main.app.dependency_overrides[get_video_service] = lambda: FakeVideoService()
        try:
            client = TestClient(main.app)
            with ThreadPoolExecutor(max_workers=2) as executor:
                video_future = executor.submit(
                    client.post,
                    "/videos/generate",
                    json={
                        "route_id": route_id,
                        "module_id": "r1m1",
                        "component_kind": "video",
                        "component_id": None,
                        "use_mock": False,
                    },
                )
                infographic_future = executor.submit(
                    client.post,
                    f"/learning-paths/{route_id}/infographic/regenerate",
                    json={"aspect_ratio": "vertical"},
                )
                video_response = video_future.result()
                infographic_response = infographic_future.result()
        finally:
            main.app.dependency_overrides.clear()

        self.assertEqual(video_response.status_code, 200)
        self.assertEqual(video_response.json()["job_id"], str(video_job_id))
        self.assertEqual(infographic_response.status_code, 200)
        self.assertEqual(len(route_service.update_payloads), 1)
        self.assertIn("pack", route_service.update_payloads[0])

if __name__ == "__main__":
    unittest.main()

import unittest
from fastapi.testclient import TestClient
from uuid import UUID
from main import app

class TestVideoAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_generate_video_mock_returns_job_id(self):
        """POST /videos/generate with custom storyboard returns a valid job ID."""
        payload = {
            "component_id": None,
            "custom_storyboard": {
                "title": "Test Title",
                "total_word_budget": 150,
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration": "Hello world.",
                        "visual_type": "text_card",
                        "visual_config": {"title": "Welcome", "bullets": ["First point"]}
                    }
                ]
            },
            "use_mock": True
        }
        response = self.client.post("/videos/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("job_id", data)
        # Verify it is a valid UUID string
        job_id_str = data["job_id"]
        job_id = UUID(job_id_str)
        self.assertIsInstance(job_id, UUID)

    def test_get_video_job_status(self):
        """GET /videos/jobs/{job_id} returns status and progress updates."""
        # First trigger generation to get a real job ID
        payload = {
            "component_id": None,
            "use_mock": True
        }
        gen_response = self.client.post("/videos/generate", json=payload)
        self.assertEqual(gen_response.status_code, 200)
        job_id = gen_response.json()["job_id"]
        
        # Poll status
        status_response = self.client.get(f"/videos/jobs/{job_id}")
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.json()
        self.assertEqual(status_data["job_id"], job_id)
        self.assertIn("status", status_data)
        self.assertIn("progress", status_data)

if __name__ == "__main__":
    unittest.main()

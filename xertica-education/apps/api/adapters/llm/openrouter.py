import json
import httpx
from typing import Dict, Any, Optional
from config.settings import settings
from adapters.llm.base import BaseLLMAdapter

class OpenRouterLLMAdapter(BaseLLMAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openrouter_key
        self.is_placeholder = not self.api_key or "placeholder" in self.api_key

    async def chat_completion(self, role: str, prompt: str, **kwargs) -> str:
        if self.is_placeholder:
            return self._get_mock_response(role, prompt)

        # Map role to commercial model name
        model_name = settings.model_names.get(role, "gemini-2.5-pro")
        # Map simple name to openrouter commercial name
        openrouter_model = self._map_model_name(model_name)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": openrouter_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            **kwargs
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    print(f"OpenRouter API error (status {response.status_code}): {response.text}")
        except Exception as e:
            print(f"OpenRouter request failed: {e}")

        # Fallback to mock on failure
        return self._get_mock_response(role, prompt)

    def _map_model_name(self, model: str) -> str:
        mapping = {
            "gemini-2.5-pro": "google/gemini-2.5-pro",
            "gemini-2.5-flash": "google/gemini-2.5-flash",
            "claude-sonnet": "anthropic/claude-3-sonnet",
        }
        return mapping.get(model, model)

    def _get_mock_response(self, role: str, prompt: str) -> str:
        """Returns mock content if OpenRouter is disabled or fails."""
        if role == "scriptwriter":
            mock_storyboard = {
                "title": "Mock Educational Video",
                "total_word_budget": 300,
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration": "¿Alguna vez te has preguntado cómo funciona esta tecnología? En esta cápsula, lo descubrirás paso a paso.",
                        "visual_type": "ai_video",
                        "visual_config": {
                            "prompt": "Luminous data streams flowing through a dark digital landscape, forming interconnected nodes, cinematic slow motion, blue and purple bioluminescent trails, abstract, no faces, 4K"
                        }
                    },
                    {
                        "scene_number": 2,
                        "narration": "Esta plataforma utiliza inteligencia artificial para generar contenido educativo de alta calidad, siempre verificado por expertos humanos.",
                        "visual_type": "ai_illustration",
                        "visual_config": {
                            "prompt": "Clean technical diagram of an AI-powered educational platform, central hub connected to satellite modules, flat design, dark navy background, blue and purple accents, 16:9, no text",
                            "title": "Plataforma Educativa",
                            "bullets": ["IA generativa", "Verificación humana", "Contenido personalizado"]
                        }
                    },
                    {
                        "scene_number": 3,
                        "narration": "El proceso comienza con la definición de un tema. La plataforma genera una estructura automática que el equipo puede revisar y aprobar.",
                        "visual_type": "animated_slide",
                        "visual_config": {
                            "title": "Flujo de Trabajo",
                            "bullets": ["Definir tema", "Generar estructura", "Revisar y aprobar", "Publicar"]
                        }
                    },
                    {
                        "scene_number": 4,
                        "narration": "En resumen, esta solución combina velocidad de la IA con precisión del juicio humano.",
                        "visual_type": "animated_slide",
                        "visual_config": {
                            "title": "Puntos Clave",
                            "bullets": ["IA + Supervisión humana", "Contenido verificable", "Listo para el aula"]
                        }
                    }
                ]
            }
            return json.dumps(mock_storyboard)
        return "Mock response for role: " + role

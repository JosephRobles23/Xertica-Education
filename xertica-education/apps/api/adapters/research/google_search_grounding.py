"""Gemini on Vertex AI adapter for documentation discovery with Google Search."""

import json
from typing import Any
from urllib.parse import urlparse

import httpx


class GoogleSearchGroundingClient:
    def __init__(self, project: str, location: str, model: str) -> None:
        self._project = project
        self._location = location
        self._model = model
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self._project and "placeholder" not in self._project.lower())

    def _get_client(self):
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                vertexai=True,
                project=self._project,
                location=self._location,
                http_options=types.HttpOptions(api_version="v1"),
            )
        return self._client

    def search(self, technology: str, context: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []

        from google.genai import types

        response = self._get_client().models.generate_content(
            model=self._model,
            contents=(
                f"Find documentation useful for creating an educational module about {technology}. "
                "Prioritize official product documentation, API documentation, official developer "
                "documentation, help-center articles, and official product pages. Also include highly "
                f"relevant third-party documentation when useful. Route context: {context}"
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.0,
            ),
        )

        metadata = response.candidates[0].grounding_metadata if response.candidates else None
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for chunk in getattr(metadata, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            url = getattr(web, "uri", None)
            if not url or url in seen:
                continue
            url = self._resolve_grounding_redirect(url)
            seen.add(url)
            search_entry_point = getattr(metadata, "search_entry_point", None)
            results.append({
                "title": getattr(web, "title", None) or technology,
                "url": url,
                "metadata": {
                    "webSearchQueries": list(getattr(metadata, "web_search_queries", None) or []),
                    "searchEntryPoint": getattr(search_entry_point, "rendered_content", None),
                },
            })
        return results

    @staticmethod
    def _resolve_grounding_redirect(url: str) -> str:
        if (urlparse(url).hostname or "").lower() != "vertexaisearch.cloud.google.com":
            return url
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                response = client.head(url)
                if response.status_code >= 400:
                    response = client.get(url)
                response.raise_for_status()
                return str(response.url)
        except Exception:
            return url

    def detect_technologies(self, context: str) -> list[str]:
        if not self.enabled:
            return []
        from google.genai import types

        response = self._get_client().models.generate_content(
            model=self._model,
            contents=(
                "Identify every named technology, product, platform, API, framework, or software "
                f"skill that requires documentation in this learning route. Context: {context}"
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[str],
                temperature=0.0,
            ),
        )
        return [str(value) for value in json.loads(response.text or "[]") if value]

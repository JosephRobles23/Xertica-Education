"""Gemini on Vertex AI adapter for documentation discovery with Google Search."""

import asyncio
import json
from typing import Any
from urllib.parse import urlparse

import httpx

from prompts.research import (
    RESEARCH_SYSTEM,
    detect_technologies_prompt,
    rank_sources_prompt,
    search_prompt,
)


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
            contents=search_prompt(technology, context),
            config=types.GenerateContentConfig(
                system_instruction=RESEARCH_SYSTEM,
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
    async def resolve_redirects(urls: list[str]) -> dict[str, str]:
        """Resolve vertexaisearch.cloud.google.com proxy URLs to their real targets.

        Concurrent, best-effort: an unresolvable URL maps to itself. Non-proxy
        URLs are returned untouched without any network call.
        """
        proxied = [
            url for url in urls
            if (urlparse(url).hostname or "").lower() == "vertexaisearch.cloud.google.com"
        ]
        resolved = {url: url for url in urls}
        if not proxied:
            return resolved

        async def _resolve(client: httpx.AsyncClient, url: str) -> None:
            try:
                response = await client.head(url)
                if response.status_code >= 400:
                    response = await client.get(url)
                response.raise_for_status()
                resolved[url] = str(response.url)
            except Exception:
                pass

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            await asyncio.gather(*(_resolve(client, url) for url in proxied))
        return resolved

    def rank_sources(self, sources: list[dict[str, Any]], context: str) -> dict[int, int]:
        """Score each candidate 0-100 on relevance to the route context.

        Returns a {index: score} mapping. Empty dict when disabled or on any
        failure, so the caller keeps the deterministic positional scores.
        """
        if not self.enabled or not sources:
            return {}
        from google.genai import types

        catalog = [
            {
                "index": index,
                "title": source.get("title", ""),
                "url": source.get("url", ""),
                "tool": source.get("toolName", ""),
                "kind": source.get("kind", ""),
            }
            for index, source in enumerate(sources)
        ]
        response = self._get_client().models.generate_content(
            model=self._model,
            contents=rank_sources_prompt(context, json.dumps(catalog, ensure_ascii=False)),
            config=types.GenerateContentConfig(
                system_instruction=RESEARCH_SYSTEM,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        try:
            data = json.loads(response.text or "[]")
        except (json.JSONDecodeError, TypeError):
            return {}
        rows = data if isinstance(data, list) else data.get("scores", [])
        scores: dict[int, int] = {}
        for row in rows:
            try:
                index = int(row["index"])
                score = int(row["score"])
            except (KeyError, TypeError, ValueError):
                continue
            if 0 <= index < len(sources):
                scores[index] = max(0, min(100, score))
        return scores

    def detect_technologies(self, context: str) -> list[str]:
        if not self.enabled:
            return []
        from google.genai import types

        response = self._get_client().models.generate_content(
            model=self._model,
            contents=detect_technologies_prompt(context),
            config=types.GenerateContentConfig(
                system_instruction=RESEARCH_SYSTEM,
                response_mime_type="application/json",
                response_schema=list[str],
                temperature=0.0,
            ),
        )
        return [str(value) for value in json.loads(response.text or "[]") if value]

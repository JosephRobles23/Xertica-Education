"""Tavily adapter for documentation discovery.

Tavily hace la búsqueda web (URLs limpias, sin redirects proxy) y un LLM de
chat vía OpenRouter cubre el ranking y la detección de tecnologías. Expone la
misma interfaz que GoogleSearchGroundingClient (enabled/search/rank_sources/
detect_technologies), así que ResearchService no distingue entre ambos.
"""

import json
from typing import Any

import httpx

from prompts.research import (
    RESEARCH_SYSTEM,
    detect_technologies_prompt,
    rank_sources_prompt,
)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


def _is_placeholder(value: str) -> bool:
    return not value or "placeholder" in value.lower()


class TavilySearchClient:
    def __init__(
        self,
        api_key: str,
        llm_api_key: str = "",
        llm_model: str = "openai/gpt-4o-mini",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._llm_api_key = llm_api_key
        self._llm_model = llm_model
        self._transport = transport  # inyectable en tests (httpx.MockTransport)

    @property
    def enabled(self) -> bool:
        return not _is_placeholder(self._api_key)

    def _http_client(self, timeout: float) -> httpx.Client:
        return httpx.Client(timeout=timeout, transport=self._transport)

    def search(self, technology: str, context: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        # Tavily espera una query de buscador, no una instrucción: nombre de la
        # herramienta + intención; el contexto de la ruta acota el dominio.
        query = f"{technology} official documentation tutorial {context}"[:380]
        with self._http_client(timeout=15.0) as client:
            response = client.post(
                TAVILY_SEARCH_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 8,
                    "exclude_domains": ["youtube.com", "youtu.be"],
                },
            )
            response.raise_for_status()
            payload = response.json()

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in payload.get("results", []):
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            results.append({
                "title": item.get("title") or technology,
                "url": url,
                "metadata": {
                    "tavilyScore": item.get("score"),
                    "snippet": (item.get("content") or "")[:300],
                },
            })
        return results

    def _chat_json(self, prompt: str) -> Any:
        """Una llamada de chat con salida JSON vía OpenRouter. None si está deshabilitado."""
        if _is_placeholder(self._llm_api_key):
            return None
        with self._http_client(timeout=30.0) as client:
            response = client.post(
                OPENROUTER_CHAT_URL,
                headers={"Authorization": f"Bearer {self._llm_api_key}"},
                json={
                    "model": self._llm_model,
                    "messages": [
                        {"role": "system", "content": RESEARCH_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content or "null")
        except json.JSONDecodeError:
            return None

    def rank_sources(self, sources: list[dict[str, Any]], context: str) -> dict[int, int]:
        """Score 0-100 por candidato ({index: score}); {} si falla, para que el
        caller conserve los scores posicionales (misma semántica que grounding)."""
        if not self.enabled or not sources:
            return {}
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
        data = self._chat_json(rank_sources_prompt(context, json.dumps(catalog, ensure_ascii=False)))
        if data is None:
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
        data = self._chat_json(
            detect_technologies_prompt(context)
            + ' Return a JSON object {"technologies": ["..."]}.'
        )
        if data is None:
            return []
        values = data if isinstance(data, list) else data.get("technologies", [])
        return [str(value) for value in values if value]

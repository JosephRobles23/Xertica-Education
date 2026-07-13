"""Tests del adaptador Tavily (búsqueda con URLs limpias + ranking vía OpenRouter)."""

import json

import httpx

from adapters.research.tavily import TavilySearchClient


def _transport(handler):
    return httpx.MockTransport(handler)


def test_disabled_with_placeholder_key():
    client = TavilySearchClient(api_key="placeholder-key")
    assert not client.enabled
    assert client.search("Gemini", "contexto") == []
    assert client.rank_sources([{"url": "https://x.dev"}], "contexto") == {}
    assert client.detect_technologies("contexto") == []


def test_search_maps_tavily_results_and_dedupes():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://api.tavily.com/search")
        assert request.headers["Authorization"] == "Bearer tvly-test"
        body = json.loads(request.content)
        assert "Canva" in body["query"]
        return httpx.Response(200, json={
            "results": [
                {"title": "Canva Help", "url": "https://www.canva.com/help/", "content": "Guía oficial", "score": 0.91},
                {"title": "Duplicada", "url": "https://www.canva.com/help/", "content": "", "score": 0.5},
                {"title": None, "url": "https://developers.canva.com/", "content": "API docs", "score": 0.8},
            ]
        })

    client = TavilySearchClient(api_key="tvly-test", transport=_transport(handler))
    results = client.search("Canva", "curso de diseño")

    assert [r["url"] for r in results] == [
        "https://www.canva.com/help/",
        "https://developers.canva.com/",
    ]
    assert results[0]["title"] == "Canva Help"
    assert results[1]["title"] == "Canva"  # fallback al nombre de la tecnología
    assert results[0]["metadata"]["tavilyScore"] == 0.91


def test_rank_sources_parses_openrouter_json_and_clamps():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["messages"][0]["role"] == "system"
        content = json.dumps({"scores": [
            {"index": 0, "score": 150},
            {"index": 1, "score": 40},
            {"index": 9, "score": 80},
        ]})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = TavilySearchClient(
        api_key="tvly-test", llm_api_key="sk-or-test", transport=_transport(handler)
    )
    scores = client.rank_sources(
        [{"url": "https://a.dev", "title": "A"}, {"url": "https://b.dev", "title": "B"}],
        "contexto",
    )
    assert scores == {0: 100, 1: 40}  # clampeado a 100 y el índice 9 (fuera de rango) ignorado


def test_rank_sources_returns_empty_without_llm_key():
    client = TavilySearchClient(api_key="tvly-test", llm_api_key="placeholder-key")
    assert client.rank_sources([{"url": "https://a.dev"}], "contexto") == {}

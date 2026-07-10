from config.settings import settings

from .google_search_grounding import GoogleSearchGroundingClient
from .tavily import TavilySearchClient


def get_documentation_client():
    """Tavily si hay API key configurada; si no, Gemini + Google Search Grounding.

    Misma interfaz (enabled/search/rank_sources/detect_technologies), así que
    ResearchService no distingue entre ambos.
    """
    if "placeholder" not in settings.tavily_api_key.lower():
        return TavilySearchClient(
            api_key=settings.tavily_api_key,
            llm_api_key=settings.openrouter_key,
            llm_model=settings.research_rank_model,
        )
    return GoogleSearchGroundingClient(
        project=settings.google_cloud_project,
        location=settings.research_location,
        model=settings.research_model,
    )


__all__ = ["GoogleSearchGroundingClient", "TavilySearchClient", "get_documentation_client"]

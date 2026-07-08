"""Factory del generador de Estructura Propuesta (ADR-0014).

Con key real → LLMRouteStructurer (Haiku 4.5 vía OpenRouter). Con placeholder →
MockRouteStructurer determinista (regla de oro #1). El router captura los fallos del
service real y marca el Job failed (no cae al mock en prod · ADR-0014).
"""
from config.settings import settings
from .interface import RouteStructurerInterface
from .mock import MockRouteStructurer


def get_route_structurer() -> RouteStructurerInterface:
    key = settings.openrouter_key
    if not key or "placeholder" in key:
        return MockRouteStructurer()
    from adapters.llm.openrouter import OpenRouterLLMAdapter  # lazy
    from .service import LLMRouteStructurer

    return LLMRouteStructurer(OpenRouterLLMAdapter(api_key=key))


__all__ = ["RouteStructurerInterface", "MockRouteStructurer", "get_route_structurer"]

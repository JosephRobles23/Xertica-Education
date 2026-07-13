"""Prompts del pipeline de Deep Research: búsqueda, ranking y detección de tecnologías.

Los consumen los adaptadores de investigación (Tavily / Gemini grounding); el
system prompt es deliberadamente neutral respecto a proveedores para que la
prioridad la marque la herramienta detectada en el brief, no un vendor fijo.
"""

RESEARCH_SYSTEM = (
    "You are a vendor-neutral research assistant for corporate training content. "
    "You find and evaluate learning resources (documentation, articles, videos) for "
    "educational modules. Always prioritize the official documentation of whichever "
    "vendor makes the tool detected in the brief — never favor a fixed vendor — and "
    "complement with high-quality third-party sources when they add value."
)


def search_prompt(technology: str, context: str) -> str:
    return (
        f"Find documentation useful for creating an educational module about {technology}. "
        "Prioritize official product documentation, API documentation, official developer "
        "documentation, help-center articles, and official product pages. Also include highly "
        f"relevant third-party documentation when useful. Route context: {context}"
    )


def rank_sources_prompt(context: str, catalog_json: str) -> str:
    return (
        "You rank candidate learning resources by their relevance to a training route. "
        "For each candidate return a score from 0 (irrelevant) to 100 (highly relevant "
        "and authoritative). Reward official documentation and specific, on-topic videos; "
        "penalize generic channel or search-result pages and off-topic results. "
        "Return a JSON array of objects with keys 'index' and 'score'.\n\n"
        f"Route context:\n{context}\n\n"
        f"Candidates:\n{catalog_json}"
    )


def detect_technologies_prompt(context: str) -> str:
    return (
        "Identify every named technology, product, platform, API, framework, or software "
        f"skill that requires documentation in this learning route. Context: {context}"
    )

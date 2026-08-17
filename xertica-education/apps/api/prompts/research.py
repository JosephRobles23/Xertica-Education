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


def detect_tools_prompt(context: str) -> str:
    """Detección abierta de herramientas (ADR-0024): conjunto abierto, sin sugerir nada
    que el usuario no haya nombrado. Lo consume ResearchService vía el rol 'researcher'."""
    return (
        "Extract the tools, products, platforms or software EXPLICITLY mentioned in the "
        "following learning-route text. Rules: (1) only include something if it is actually "
        "named in the text — never infer, suggest or add a tool the author did not write; "
        "(2) do not treat generic words (prompt, image, data, design, video) as tools; "
        "(3) any vendor is valid, there is no preferred one; (4) if no tool is named, "
        "return an empty array.\n"
        'Answer ONLY with a JSON array like [{"tool":"Figma","vendor":"Figma"}] '
        "(use null for vendor when unknown).\n\n"
        f"Text:\n{context}"
    )


def detect_technologies_prompt(context: str) -> str:
    return (
        "Identify every named technology, product, platform, API, framework, or software "
        f"skill that requires documentation in this learning route. Context: {context}"
    )

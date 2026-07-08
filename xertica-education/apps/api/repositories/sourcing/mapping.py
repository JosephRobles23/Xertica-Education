"""Mapeo de las fuentes del deep-research (route["sources"], dicts) a `Source` (ADR-0007).

Persiste TODAS las candidatas con su `estado` (decisión #3); el id lo asigna el repo.
"""
from models.common import as_uuid
from models.domain.source import Source

# kind del deep-research → tipo canónico de Source (ADR-0005)
_KIND_TO_TIPO = {
    "youtube": "youtube",
    "documentation": "blog_oficial",
    "article": "blog_oficial",
}


def route_sources_to_domain(route_sources: list[dict], learning_path_id) -> list[Source]:
    lp = as_uuid(learning_path_id)
    out: list[Source] = []
    for raw in route_sources or []:
        url = raw.get("url")
        if not url:
            continue
        out.append(Source(
            learning_path_id=lp,
            url=url,
            title=raw.get("title"),
            tipo=_KIND_TO_TIPO.get(raw.get("kind"), "blog_oficial"),
            estado=raw.get("status"),
            verificada_google=bool(raw.get("verified")),
        ))
    return out

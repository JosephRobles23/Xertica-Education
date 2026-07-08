"""RealLinker: asigna Source↔Módulo con un LLM de chat vía OpenRouter (OpenAI-compatible).

Recibe módulos + pool de fuentes y pide al modelo la mejor asignación en JSON. Best-effort:
ante cualquier fallo (red, parseo, clave) cae a `MockLinker` para no bloquear (regla de oro
#1). NO re-busca fuentes — solo re-rankea el pool dado (ADR-0012).
"""
import json

from models.common import as_uuid
from models.domain.source import Source
from models.domain.source_module_link import SourceModuleLink
from .base import BaseLinker
from .mock import MockLinker

_SYSTEM = (
    "Eres un diseñador instruccional. Asigna a cada módulo la fuente más pertinente del "
    "pool dado (por tema/relevancia). NO inventes fuentes ni módulos. Responde SOLO un JSON "
    '{"links":[{"module_id":"...","source_id":"...","score":0.0,"why":"..."}]}. '
    "score en [0,1]. Omite un módulo si ninguna fuente aplica."
)


class RealLinker(BaseLinker):
    def __init__(self, api_key: str, base_url: str, model: str):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._fallback = MockLinker()

    async def link(
        self, learning_path_id, modules: list[dict], sources: list[Source]
    ) -> list[SourceModuleLink]:
        lp = as_uuid(learning_path_id)
        try:
            from openai import OpenAI  # lazy: SDK real solo con clave

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            user = json.dumps({
                "modules": [
                    {"id": m.get("id"), "name": m.get("name"), "type": m.get("type"),
                     "summaries": [c.get("summary") for c in m.get("contents", []) or []]}
                    for m in modules or []
                ],
                "sources": [
                    {"id": str(s.id), "title": s.title, "url": s.url,
                     "tipo": s.tipo, "verificada_google": s.verificada_google}
                    for s in sources or [] if s.id is not None
                ],
            }, ensure_ascii=False)
            resp = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": _SYSTEM},
                          {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            valid_ids = {str(s.id) for s in sources if s.id is not None}
            valid_modules = {str(m.get("id")) for m in modules or []}
            links: list[SourceModuleLink] = []
            for raw in data.get("links", []):
                sid, mid = str(raw.get("source_id")), str(raw.get("module_id"))
                if sid not in valid_ids or mid not in valid_modules:
                    continue  # el modelo no puede inventar ids fuera del pool
                links.append(SourceModuleLink(
                    learning_path_id=lp, source_id=as_uuid(sid), module_id=mid,
                    score=raw.get("score"), origin="llm", why=raw.get("why"),
                ))
            return links or await self._fallback.link(lp, modules, sources)
        except Exception:
            # Nunca bloquea: cae a la heurística determinista.
            return await self._fallback.link(lp, modules, sources)

"""MockLinker (regla de oro #1): asigna Source↔Módulo con una heurística determinista,
espejo de `findRecommendedYoutubeSource` del frontend. Sirve sin clave de LLM y da un
resultado estable para tests. El `RealLinker` (OpenRouter) lo reemplaza cuando hay clave.
"""
import re

from models.common import as_uuid
from models.domain.source import Source
from models.domain.source_module_link import SourceModuleLink
from .base import BaseLinker

_WORD = re.compile(r"[a-záéíóúñ0-9]+", re.IGNORECASE)
_STOP = {"de", "la", "el", "los", "las", "un", "una", "para", "con", "y", "en", "del", "al", "a"}


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP and len(w) > 2}


def _module_text(module: dict) -> str:
    parts = [module.get("name", ""), module.get("type", "")]
    parts += [c.get("summary", "") for c in module.get("contents", []) or []]
    return " ".join(p for p in parts if p)


def _score(module: dict, source: Source) -> float:
    """Overlap Jaccard-ish título↔módulo + bonus por verificada/youtube. Rango ~[0,1.3]."""
    m_tok = _tokens(_module_text(module))
    s_tok = _tokens(f"{source.title or ''} {source.url or ''}")
    if not m_tok or not s_tok:
        overlap = 0.0
    else:
        overlap = len(m_tok & s_tok) / len(m_tok | s_tok)
    bonus = (0.2 if source.verificada_google else 0.0) + (0.1 if source.tipo == "youtube" else 0.0)
    return round(overlap + bonus, 4)


class MockLinker(BaseLinker):
    async def link(
        self, learning_path_id, modules: list[dict], sources: list[Source]
    ) -> list[SourceModuleLink]:
        lp = as_uuid(learning_path_id)
        links: list[SourceModuleLink] = []
        for module in modules or []:
            module_id = module.get("id")
            if not module_id or not sources:
                continue
            best = max(sources, key=lambda s: _score(module, s))
            score = _score(module, best)
            if score <= 0 or best.id is None:
                continue
            links.append(SourceModuleLink(
                learning_path_id=lp, source_id=best.id, module_id=str(module_id),
                score=score, origin="llm",
                why=f"heurística: mejor overlap título↔módulo ({score})",
            ))
        return links

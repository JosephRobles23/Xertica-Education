"""Validación y normalización de la estructura del LLM → shape de route/frontend (ADR-0014).

Clampa a los enums de dominio (ModuleType/ComponentType), descarta lo inválido y asigna
id/num/status deterministas. Es la frontera que impide que el LLM meta tipos inventados.
"""
from models.domain.module import ModuleType
from models.domain.component import ComponentType

_MODULE_TYPES = {t.value for t in ModuleType}          # intro·capsula·lab·evaluacion·cierre
_COMPONENT_KINDS = {t.value for t in ComponentType}    # lesson·video·lab·infografia·quiz
_MIN_MODULES, _MAX_MODULES = 1, 8


def to_route_modules(raw_modules: list[dict]) -> list[dict]:
    """Normaliza la salida cruda del LLM a la shape de route.modules. Lanza ValueError si
    no queda ningún módulo válido (→ el Job marca failed · ADR-0014)."""
    out: list[dict] = []
    for i, raw in enumerate(raw_modules[:_MAX_MODULES], start=1):
        name = (raw.get("name") or raw.get("titulo") or "").strip()
        if not name:
            continue
        mtype = str(raw.get("type") or raw.get("tipo") or "capsula").lower()
        if mtype not in _MODULE_TYPES:
            mtype = "capsula"

        contents: list[dict] = []
        seen_kinds: set[str] = set()
        for comp in raw.get("components") or raw.get("contents") or []:
            kind = str(comp.get("kind") or comp.get("tipo") or "").lower()
            if kind not in _COMPONENT_KINDS or kind in seen_kinds:
                continue  # descarta inválidos y duplicados dentro del módulo
            seen_kinds.add(kind)
            contents.append({
                "kind": kind,
                "status": "borrador",
                "summary": (comp.get("summary") or comp.get("tema") or "").strip(),
            })
        if not contents:
            continue  # un módulo sin componentes válidos no aporta

        description = (raw.get("description") or raw.get("descripcion") or "").strip()
        
        component_durations = {
            "lesson": 5,
            "video": 3,
            "infografia": 2,
            "quiz": 4,
            "lab": 15
        }
        computed_minutes = sum(component_durations.get(c["kind"], 5) for c in contents)
        target_minutes = int(raw.get("target_minutes") or raw.get("duracion_objetivo_min") or raw.get("min") or computed_minutes)

        out.append({
            "id": f"r1m{i}",
            "num": f"{i:02d}",
            "name": name,
            "description": description,
            "descripcion": description,
            "type": mtype,
            "status": "borrador",
            "target_minutes": target_minutes,
            "duracion_objetivo_min": target_minutes,
            "contents": contents,
        })

    if len(out) < _MIN_MODULES:
        raise ValueError("La estructura del LLM no produjo módulos válidos")
    # re-numera por si se descartaron intermedios
    for i, mod in enumerate(out, start=1):
        mod["id"], mod["num"] = f"r1m{i}", f"{i:02d}"
    return out

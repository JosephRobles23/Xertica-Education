"""Generador real de la Estructura Propuesta con LLM (ADR-0014).

Material-first: los documentos ingestados (parsed_docs) son el esqueleto; brief y
customerContext encuadran/personalizan. Usa el OpenRouterLLMAdapter con role
'route_structurer' (→ claude-haiku-4.5). Parseo estricto + normalización de enums.
"""
import json
import re

from adapters.llm.base import BaseLLMAdapter
from .interface import RouteStructurerInterface
from .normalize import to_route_modules

_MAX_DOC_CHARS = 12000  # cota por documento para no reventar el contexto

_SYSTEM = """Eres un diseñador instruccional. A partir del MATERIAL del cliente, diseña
la estructura de una ruta de aprendizaje: entre 3 y 8 módulos, cada uno con 2 a 4
componentes. El MATERIAL manda: los módulos deben cubrir su contenido en orden pedagógico.
El brief da el objetivo y el contexto personaliza (área/industria/audiencia).

Responde SOLO un JSON válido, sin texto alrededor:
{"modules":[{"name":"...","type":"<intro|capsula|lab|evaluacion|cierre>",
"components":[{"kind":"<lesson|video|infografia|quiz|lab>","summary":"..."}]}]}

Reglas: 'name' en español, conciso. El primer módulo suele ser 'intro' y el último
'evaluacion' o 'cierre'. 'summary' describe qué cubre el componente (1 frase)."""


class LLMRouteStructurer(RouteStructurerInterface):
    def __init__(self, llm: BaseLLMAdapter):
        self._llm = llm

    async def generate(
        self, brief: str, customer_context: dict, parsed_docs: list[str]
    ) -> list[dict]:
        prompt = self._build_prompt(brief, customer_context, parsed_docs)
        raw = await self._llm.chat_completion(role="route_structurer", prompt=prompt)
        data = _extract_json(raw)
        modules = data.get("modules") if isinstance(data, dict) else None
        if not isinstance(modules, list):
            raise ValueError("El LLM no devolvió 'modules' como lista")
        return to_route_modules(modules)  # valida/clampa; lanza si nada válido

    def _build_prompt(self, brief: str, ctx: dict, parsed_docs: list[str]) -> str:
        area = ctx.get("area") or "General"
        industry = ctx.get("industry") or "no especificada"
        audience = ctx.get("audienceLevel") or "audiencia general"
        if parsed_docs:
            material = "\n\n---\n\n".join(d[:_MAX_DOC_CHARS] for d in parsed_docs)
            material_block = f"MATERIAL DEL CLIENTE (fuente principal):\n{material}"
        else:
            # sin material → brief-driven (ADR-0014 · decisión 4)
            material_block = "MATERIAL DEL CLIENTE: (no se subió material; usa el brief como base)."
        return (
            f"{_SYSTEM}\n\n"
            f"CONTEXTO: área={area} · industria={industry} · audiencia={audience}.\n"
            f"BRIEF/OBJETIVO: {brief or '(sin brief)'}\n\n"
            f"{material_block}"
        )


def _extract_json(text: str) -> dict:
    """Extrae el primer objeto JSON del texto (tolera fences ```json y prosa alrededor)."""
    if not text:
        raise ValueError("Respuesta vacía del LLM")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No se encontró JSON en la respuesta del LLM")
        candidate = text[start : end + 1]
    return json.loads(candidate)

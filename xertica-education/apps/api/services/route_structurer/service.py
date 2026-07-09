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
la estructura de una ruta de aprendizaje: un título, tema y objetivo para la ruta, y entre
3 y 8 módulos, cada uno con 2 a 4 componentes. El MATERIAL manda: los módulos deben cubrir
su contenido en orden pedagógico. El brief da la intención y el contexto personaliza
(área/industria/audiencia).

Responde SOLO un JSON válido, sin texto alrededor:
{"title":"...","tema":"...","objective":"...","modules":[{"name":"...","description":"...","type":"<intro|capsula|lab|evaluacion|cierre>","target_minutes":10,
"components":[{"kind":"<lesson|video|infografia|quiz|lab>","summary":"..."}]}]}

Reglas: 'title' es el nombre atractivo y conciso de la ruta en español (máx ~60 caracteres).
NO copies el brief literal: sintetiza un nombre apropiado (ej. herramienta + propósito, como
"Nano Banana para Marketing"). Si el brief indica explícitamente un nombre/título deseado para
la ruta, respétalo tal cual.
'tema' es la materia o disciplina central en 1-4 palabras en español.
'objective' es el objetivo de aprendizaje de la ruta en 1-2 frases en español, redactado de
forma profesional (qué logrará el estudiante). NO copies el brief literal: reformúlalo como un
objetivo claro. Si el brief indica explícitamente un objetivo concreto, respétalo.
'name' de cada módulo en español, conciso.
'description' describe el objetivo del módulo en 1-2 frases en español.
El primer módulo suele ser 'intro' y el último 'evaluacion' o 'cierre'.
'target_minutes' es la duración total del módulo en minutos (entero).
'summary' describe qué cubre el componente (1 frase)."""


class LLMRouteStructurer(RouteStructurerInterface):
    def __init__(self, llm: BaseLLMAdapter):
        self._llm = llm

    async def generate(
        self, brief: str, customer_context: dict, parsed_docs: list[str]
    ) -> dict:
        prompt = self._build_prompt(brief, customer_context, parsed_docs)
        raw = await self._llm.chat_completion(role="route_structurer", prompt=prompt)
        data = _extract_json(raw)
        modules = data.get("modules") if isinstance(data, dict) else None
        if not isinstance(modules, list):
            raise ValueError("El LLM no devolvió 'modules' como lista")
        route_modules = to_route_modules(modules)  # valida/clampa; lanza si nada válido
        title = (data.get("title") or "").strip() or _fallback_title(brief)
        tema = (data.get("tema") or "").strip() or _fallback_tema(brief, customer_context)
        objective = (data.get("objective") or "").strip() or _fallback_objective(brief)
        return {"title": title, "tema": tema, "objective": objective, "modules": route_modules}

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


def _fallback_title(brief: str) -> str:
    """Título provisional si el LLM no devolvió 'title': primera línea del brief acotada."""
    first = (brief or "").strip().splitlines()[0].strip() if (brief or "").strip() else ""
    if not first:
        return "Nueva ruta de aprendizaje"
    words = first.split()
    title = " ".join(words[:9])
    return (title[:57].rstrip() + "…") if len(title) > 60 else title


def _fallback_tema(brief: str, ctx: dict) -> str:
    """Tema provisional si el LLM no devolvió 'tema': industria del contexto o genérico."""
    industry = (ctx or {}).get("industry")
    if industry:
        return str(industry).strip()
    return "General"


def _fallback_objective(brief: str) -> str:
    """Objetivo provisional si el LLM no devolvió 'objective': el brief tal cual (mejor que
    vacío). En prod el LLM redacta uno apropiado; esto es solo la red de seguridad."""
    text = (brief or "").strip()
    return text or "Objetivo de aprendizaje por definir."


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

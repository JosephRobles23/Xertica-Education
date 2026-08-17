"""Spec de la detección abierta de herramientas del deep research (ADR-0024).

La detección deja de forzar el registro de vendors: el LLM detecta lo que el usuario
realmente mencionó y TOOL_REGISTRY pasa a ser capa de verificación.
"""
import asyncio
import json

from adapters.llm.base import BaseLLMAdapter
from services.research.service import ResearchService, TOOL_REGISTRY


class _NoYoutube:
    enabled = False

    def search(self, *args, **kwargs):
        return []


class _FakeLLM(BaseLLMAdapter):
    """Devuelve una lista fija de herramientas, como haría el rol 'researcher'."""

    def __init__(self, tools, *, fail=False):
        self._tools = tools
        self._fail = fail
        self.calls = 0

    async def chat_completion(self, role: str, prompt: str, **kwargs) -> str:
        self.calls += 1
        assert role == "researcher"
        if self._fail:
            raise RuntimeError("LLM caído")
        return json.dumps(self._tools)


def _service(llm=None):
    return ResearchService(youtube_client=_NoYoutube(), documentation_client=None, llm=llm)


# ── poda de aliases genéricos ──────────────────────────────────────────────
def test_generic_spanish_words_no_longer_match_vendor_tools():
    """'prompt', 'imagen', 'datos'… disparaban Gemini/Nano Banana/BigQuery por substring."""
    brief = (
        "Curso de prompting para dueños de bodegas: cómo escribir un buen prompt, "
        "generar una imagen para redes y ordenar los datos de ventas con diseño simple."
    )
    detected = _service().detect_tools(brief)
    assert detected == [], f"falsos positivos: {[t['tool'] for t in detected]}"


def test_registry_still_matches_real_product_names():
    detected = _service().detect_tools("Taller práctico de Canva y BigQuery para el equipo")
    assert {tool["tool"] for tool in detected} == {"Canva", "BigQuery"}


# ── detección abierta con LLM ──────────────────────────────────────────────
def test_llm_detects_tools_outside_the_registry():
    llm = _FakeLLM([{"tool": "Figma", "vendor": "Figma"}, {"tool": "Excel", "vendor": "Microsoft"}])
    detected = asyncio.run(_service(llm).detect_tools_async("Curso de Figma y Excel"))

    assert llm.calls == 1
    by_name = {tool["tool"]: tool for tool in detected}
    assert set(by_name) == {"Figma", "Excel"}
    # No registradas → sin canales/dominios oficiales, se verifican por búsqueda.
    assert by_name["Figma"]["vendor"] == "Figma"
    assert by_name["Figma"]["channels"] == [] and by_name["Figma"]["domains"] == []


def test_llm_hit_on_registry_keeps_official_sources():
    llm = _FakeLLM([{"tool": "Canva", "vendor": "Canva"}])
    detected = asyncio.run(_service(llm).detect_tools_async("Diseño de piezas en Canva"))

    assert len(detected) == 1
    canva = detected[0]
    registry_entry = next(t for t in TOOL_REGISTRY if t["tool"] == "Canva")
    assert canva["domains"] == registry_entry["domains"]
    assert canva["official_doc"] == registry_entry["official_doc"]


def test_falls_back_to_registry_matching_when_llm_fails():
    llm = _FakeLLM([], fail=True)
    detected = asyncio.run(_service(llm).detect_tools_async("Taller de Canva para marketing"))
    assert [tool["tool"] for tool in detected] == ["Canva"]


def test_falls_back_when_llm_returns_garbage():
    class _GarbageLLM(BaseLLMAdapter):
        async def chat_completion(self, role: str, prompt: str, **kwargs) -> str:
            return "lo siento, no puedo ayudarte con eso"

    detected = asyncio.run(_service(_GarbageLLM()).detect_tools_async("Taller de Canva"))
    assert [tool["tool"] for tool in detected] == ["Canva"]


def test_without_llm_uses_deterministic_registry_matching():
    detected = asyncio.run(_service().detect_tools_async("Taller de Canva"))
    assert [tool["tool"] for tool in detected] == ["Canva"]


# ── sin fallback forzado a Gemini ──────────────────────────────────────────
def test_no_tools_detected_returns_empty_instead_of_forcing_gemini():
    llm = _FakeLLM([])
    result = asyncio.run(_service(llm).run({
        "route_name": "Atención al cliente en veterinarias",
        "brief": "Enseñar a recepcionistas a atender clientes con empatía.",
        "modules": [],
        "customer_context": {"industry": "Veterinaria", "audienceLevel": "recepcionistas"},
    }))
    assert result["detected_tools"] == []
    blob = json.dumps(result, ensure_ascii=False).lower()
    assert "gemini" not in blob


def test_run_survives_unregistered_tool_and_marks_it_for_review():
    """Una herramienta fuera del registro no tiene canales ni fuentes oficiales:
    debe degradar a revisión humana (ADR-0017), no romper el pipeline."""
    llm = _FakeLLM([{"tool": "Figma", "vendor": "Figma"}])
    result = asyncio.run(_service(llm).run({
        "route_name": "Diseño de interfaces",
        "brief": "Enseñar Figma al equipo de producto.",
        "modules": [],
        "customer_context": {"industry": "SaaS", "audienceLevel": "diseñadores"},
    }))

    assert [tool["tool"] for tool in result["detected_tools"]] == ["Figma"]
    figma_sources = [s for s in result["sources"] if s.get("toolName") == "Figma"]
    assert figma_sources, "debe emitir al menos una fuente candidata"
    assert all(s["status"] == "requires-review" for s in figma_sources)
    assert all(s.get("url") for s in figma_sources), "ninguna fuente puede tener url vacía"


# ── haystack de detección acotado ──────────────────────────────────────────
def test_customer_url_does_not_leak_into_detection():
    """El customerContext completo (incl. URL) contaminaba la detección."""
    service = _service()
    text = service._detection_text(
        route_name="Curso de atención",
        brief="Atender mejor a los clientes",
        modules=[],
        customer_context={
            "url": "https://veo-imagen-datos.example.com",
            "industry": "Retail",
            "audienceLevel": "vendedores",
        },
    )
    assert "veo-imagen-datos" not in text
    assert "Retail" in text and "vendedores" in text

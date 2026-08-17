"""Spec del generador de Estructura Propuesta (ADR-0014): normalización, mock y LLM."""
import asyncio
import json

import pytest

from services.route_structurer.normalize import to_route_modules
from services.route_structurer.mock import MockRouteStructurer
from services.route_structurer.service import LLMRouteStructurer, _extract_json
from adapters.llm.base import BaseLLMAdapter


# ── normalize ──────────────────────────────────────────────────────────────
def test_normalize_clamps_invalid_enums_and_shapes():
    mods = to_route_modules([
        {"name": "Intro", "type": "INTRO", "description": "Desc intro", "target_minutes": 10, "components": [
            {"kind": "lesson", "summary": "a"},
            {"kind": "inventado", "summary": "x"},   # kind inválido → descartado
            {"kind": "lesson", "summary": "dup"},    # duplicado → descartado
        ]},
        {"name": "Mod raro", "type": "no-existe", "components": [{"kind": "quiz", "summary": "q"}]},
    ])
    assert [m["id"] for m in mods] == ["r1m1", "r1m2"]
    assert [m["num"] for m in mods] == ["01", "02"]
    assert mods[0]["type"] == "intro"           # clampa mayúsculas
    assert len(mods[0]["contents"]) == 1        # solo el lesson válido
    assert mods[0]["description"] == "Desc intro"
    assert mods[0]["target_minutes"] == 10
    assert mods[1]["type"] == "capsula"         # tipo inválido → default capsula
    assert mods[1]["target_minutes"] == 4       # quiz fallback = 4 min


def test_normalize_drops_modules_without_valid_components():
    mods = to_route_modules([
        {"name": "Vacío", "type": "intro", "components": [{"kind": "zzz", "summary": "x"}]},
        {"name": "Bueno", "type": "capsula", "components": [{"kind": "video", "summary": "v"}]},
    ])
    assert len(mods) == 1 and mods[0]["name"] == "Bueno" and mods[0]["id"] == "r1m1"


def test_normalize_raises_when_nothing_valid():
    with pytest.raises(ValueError):
        to_route_modules([{"name": "", "components": []}])


# ── mock ───────────────────────────────────────────────────────────────────
def test_mock_produces_valid_structure():
    result = asyncio.run(MockRouteStructurer().generate("Ruta de nanobanana para marketing", {"area": "TI"}, ["doc"]))
    assert result["title"] and result["tema"] and result["objective"]
    mods = result["modules"]
    assert len(mods) == 2
    assert all("id" in m and "num" in m and m["contents"] for m in mods)
    assert all(c["status"] == "borrador" for m in mods for c in m["contents"])


def test_mock_title_derives_from_brief():
    result = asyncio.run(MockRouteStructurer().generate("Nano Banana para Marketing", {"industry": "Retail"}, []))
    assert "Nano Banana" in result["title"]
    assert result["tema"] == "Retail"


# ── LLM service ────────────────────────────────────────────────────────────
class _FakeLLM(BaseLLMAdapter):
    def __init__(self, reply: str):
        self._reply = reply

    async def chat_completion(self, role: str, prompt: str, **kwargs) -> str:
        assert role == "route_structurer"
        return self._reply


def test_extract_json_handles_fences_and_prose():
    assert _extract_json('```json\n{"a":1}\n```') == {"a": 1}
    assert _extract_json('claro:\n{"a":2}\ngracias') == {"a": 2}


def test_llm_structurer_parses_and_normalizes():
    reply = json.dumps({"title": "Ruta Nano Banana", "tema": "Marketing",
                        "objective": "El estudiante creará campañas visuales con Nano Banana.", "modules": [
        {"name": "Fundamentos", "type": "intro", "components": [{"kind": "lesson", "summary": "s"}]},
    ]})
    result = asyncio.run(LLMRouteStructurer(_FakeLLM(reply)).generate("b", {}, ["material"]))
    assert result["title"] == "Ruta Nano Banana" and result["tema"] == "Marketing"
    assert result["objective"] == "El estudiante creará campañas visuales con Nano Banana."
    assert result["modules"][0]["name"] == "Fundamentos" and result["modules"][0]["id"] == "r1m1"


def test_llm_structurer_falls_back_when_fields_missing():
    reply = json.dumps({"modules": [
        {"name": "Fundamentos", "type": "intro", "components": [{"kind": "lesson", "summary": "s"}]},
    ]})
    result = asyncio.run(LLMRouteStructurer(_FakeLLM(reply)).generate("Curso de Veo 3", {"industry": "Media"}, []))
    assert result["title"] == "Curso de Veo 3"   # fallback: primera línea del brief
    assert result["tema"] == "Media"              # fallback: industria del contexto
    assert result["objective"] == "Curso de Veo 3"  # fallback: el brief tal cual


def test_llm_structurer_raises_on_garbage():
    with pytest.raises(Exception):
        asyncio.run(LLMRouteStructurer(_FakeLLM("no soy json")).generate("b", {}, []))


# ── ADR-0024: brief unificado, contexto y fallo honesto ────────────────────
class _SpyLLM(BaseLLMAdapter):
    """Captura prompt y kwargs de la llamada para poder afirmar sobre ellos."""

    def __init__(self, reply: str):
        self._reply = reply
        self.prompt = ""
        self.kwargs: dict = {}

    async def chat_completion(self, role: str, prompt: str, **kwargs) -> str:
        self.prompt, self.kwargs = prompt, kwargs
        return self._reply


_MINIMAL_REPLY = json.dumps({"modules": [
    {"name": "M1", "type": "intro", "components": [{"kind": "lesson", "summary": "s"}]},
]})


def test_structurer_requests_strict_mode_and_long_timeout():
    """El fallo del LLM debe propagarse (ADR-0024), no degradarse a mock silencioso."""
    llm = _SpyLLM(_MINIMAL_REPLY)
    asyncio.run(LLMRouteStructurer(llm).generate("b", {}, []))
    assert llm.kwargs.get("strict") is True
    assert llm.kwargs.get("timeout") == 90.0


def test_prompt_includes_company_name():
    llm = _SpyLLM(_MINIMAL_REPLY)
    asyncio.run(LLMRouteStructurer(llm).generate("b", {"companyName": "Acme Corp"}, []))
    assert "Acme Corp" in llm.prompt


def test_prompt_carries_brief_and_material_without_truncating_long_structures():
    """40k por documento (ADR-0024): una estructura larga pegada llega entera."""
    long_doc = "Módulo X. " * 3000  # ~30k caracteres
    llm = _SpyLLM(_MINIMAL_REPLY)
    asyncio.run(LLMRouteStructurer(llm).generate("mi brief", {}, [long_doc]))
    assert "mi brief" in llm.prompt
    assert llm.prompt.count("Módulo X.") == 3000


def test_llm_error_propagates_instead_of_falling_back():
    class _FailingLLM(BaseLLMAdapter):
        async def chat_completion(self, role: str, prompt: str, **kwargs) -> str:
            raise RuntimeError("OpenRouter 429: rate limit")

    with pytest.raises(RuntimeError, match="rate limit"):
        asyncio.run(LLMRouteStructurer(_FailingLLM()).generate("b", {}, []))


def test_mock_is_vendor_neutral():
    """El mock no debe inyectar herramientas que el usuario no pidió (ADR-0024)."""
    result = asyncio.run(MockRouteStructurer().generate(
        "Atención al cliente en una veterinaria",
        {"area": "General", "usesGoogleWorkspace": "yes"},
        [],
    ))
    blob = json.dumps(result, ensure_ascii=False).lower()
    assert "google" not in blob and "workspace" not in blob


def test_system_prompt_is_vendor_neutral_and_states_hierarchy():
    from prompts.route_structurer import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    for vendor_term in ("nano banana", "gemini", "google", "canva", "bigquery"):
        assert vendor_term not in lowered, f"el prompt no debe nombrar {vendor_term}"
    assert "brief" in lowered and "material" in lowered

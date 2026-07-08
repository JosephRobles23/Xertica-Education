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
        {"name": "Intro", "type": "INTRO", "components": [
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
    assert mods[1]["type"] == "capsula"         # tipo inválido → default capsula


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
    mods = asyncio.run(MockRouteStructurer().generate("brief", {"area": "TI"}, ["doc"]))
    assert len(mods) == 2
    assert all("id" in m and "num" in m and m["contents"] for m in mods)
    assert all(c["status"] == "borrador" for m in mods for c in m["contents"])


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
    reply = json.dumps({"modules": [
        {"name": "Fundamentos", "type": "intro", "components": [{"kind": "lesson", "summary": "s"}]},
    ]})
    mods = asyncio.run(LLMRouteStructurer(_FakeLLM(reply)).generate("b", {}, ["material"]))
    assert mods[0]["name"] == "Fundamentos" and mods[0]["id"] == "r1m1"


def test_llm_structurer_raises_on_garbage():
    with pytest.raises(Exception):
        asyncio.run(LLMRouteStructurer(_FakeLLM("no soy json")).generate("b", {}, []))

"""Spec de la materialización perezosa del Spine (ADR-0020) y aprobaciones (ADR-0021)."""
import asyncio

from repositories.spine.materializer import SpineMaterializer
from repositories.learning_path.repository import SupabaseLearningPathRepository
from routers.learning_paths import review_content_approval, update_route_approvals
from services.route.service import RouteService

import pytest


def test_deterministic_ids_converge_across_reruns_and_id_forms():
    a = SpineMaterializer()
    # El id corto '01' y su UUID resuelto producen las mismas filas.
    assert a.module_uuid("01", "r1m1") == a.module_uuid("00000000-0000-0000-0000-000000000001", "r1m1")
    assert a.asset_uuid("01", "r1m1", "lesson") == a.asset_uuid("01", "r1m1", "lesson")
    assert a.asset_uuid("01", "r1m1", "lesson") != a.asset_uuid("01", "r1m1", "quiz")


def test_upsert_asset_materializes_chain_and_merges_provenance():
    spine = SpineMaterializer()  # credenciales placeholder → memoria
    first = spine.upsert_asset(
        "01", "r1m1", "lesson",
        estado="generado",
        storage_path="01/r1m1/lesson/x.pdf",
        provenance={"grounding_status": "module-grounded"},
        module_name="Introducción", module_type="intro",
    )
    assert first["persisted"] is False  # visible: quedó en memoria, no en Supabase
    assert first["estado"] == "generado"

    # La aprobación posterior no pisa storage_path y mergea provenance.
    second = spine.upsert_asset("01", "r1m1", "lesson", estado="aprobado", provenance={"who": "grill"})
    assert second["id"] == first["id"]
    assert second["estado"] == "aprobado"
    assert second["storage_path"] == "01/r1m1/lesson/x.pdf"
    assert second["provenance"] == {"grounding_status": "module-grounded", "who": "grill"}

    # module + component materializados en memoria con la cadena de FKs coherente.
    modules = list(spine._memory["modules"].values())
    components = list(spine._memory["components"].values())
    assert modules[0]["titulo"] == "Introducción" and modules[0]["tipo"] == "intro"
    assert components[0]["modulo_id"] == modules[0]["id"]
    assert first["componente_id"] == components[0]["id"]


def test_upsert_asset_rejects_invalid_kind_and_estado():
    spine = SpineMaterializer()
    with pytest.raises(ValueError):
        spine.upsert_asset("01", "r1m1", "podcast")
    with pytest.raises(ValueError):
        spine.upsert_asset("01", "r1m1", "lesson", estado="publicado")


def _route_service_with_module():
    service = RouteService(SupabaseLearningPathRepository())
    route = asyncio.run(service.create_route("Ruta test", "IA", "brief"))
    asyncio.run(service.update_route(route["id"], {
        "modules": [{
            "id": "m1", "name": "Módulo 1", "type": "capsula",
            "contents": [{"kind": "lesson", "status": "generado"}],
        }],
    }))
    return service, route["id"]


def test_content_approval_updates_asset_and_mirrors_json():
    service, route_id = _route_service_with_module()
    result = asyncio.run(review_content_approval(
        route_id, "m1", "lesson", {"status": "aprobado"}, route_service=service,
    ))
    assert result["asset"]["estado"] == "aprobado"
    module = result["route"]["modules"][0]
    # Espejo para la rehidratación del frontend (lee contents[].status).
    assert module["contents"][0]["status"] == "aprobado"
    assert module["approvals"]["lesson"] == "aprobado"


def test_content_approval_validates_kind_and_status():
    from fastapi import HTTPException

    service, route_id = _route_service_with_module()
    with pytest.raises(HTTPException):
        asyncio.run(review_content_approval(route_id, "m1", "podcast", {"status": "aprobado"}, route_service=service))
    with pytest.raises(HTTPException):
        asyncio.run(review_content_approval(route_id, "m1", "lesson", {"status": "ok"}, route_service=service))


def test_route_approvals_merge_flags_and_discarded_urls():
    service, route_id = _route_service_with_module()
    first = asyncio.run(update_route_approvals(
        route_id, {"storyboard": True, "discardedSourceUrls": ["https://a.dev"]}, route_service=service,
    ))
    assert first["approvals"] == {"storyboard": True, "discardedSourceUrls": ["https://a.dev"]}

    # Merge acumulativo: no pisa flags previos y agrega URLs sin duplicar.
    second = asyncio.run(update_route_approvals(
        route_id, {"labGuide": True, "discardedSourceUrls": ["https://a.dev", "https://b.dev"]},
        route_service=service,
    ))
    assert second["approvals"]["storyboard"] is True
    assert second["approvals"]["labGuide"] is True
    assert second["approvals"]["discardedSourceUrls"] == ["https://a.dev", "https://b.dev"]

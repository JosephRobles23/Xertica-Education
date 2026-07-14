"""Materialización perezosa del Spine (ADR-0020).

Los módulos/componentes viven en el JSON `learning_paths.details`; este
materializador crea on-demand las filas normalizadas (`modules`, `components`)
que un `Asset` necesita para satisfacer sus FKs, con UUIDs deterministas para
que regeneraciones converjan en las mismas filas. Nunca propaga errores: en
dev (credenciales placeholder) o ante fallo de Supabase, opera sobre un store
in-memory y reporta `persisted: False` (patrón ADR-0004, pero visible).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from config.settings import settings

logger = logging.getLogger(__name__)

# Namespace propio del proyecto para uuid5 (derivado del DNS namespace estándar).
_SPINE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "xertica-education.spine")

MODULE_TYPES = {"intro", "capsula", "lab", "evaluacion", "cierre"}
COMPONENT_KINDS = {"lesson", "video", "lab", "infografia", "quiz"}
ASSET_STATES = {"draft", "generado", "en_revision", "aprobado"}

# Pseudo-módulo para assets a nivel ruta (ej. la infografía de la ruta completa).
ROUTE_LEVEL_MODULE_ID = "route"


def _normalize_route_id(route_id: str) -> str:
    """Mismo esquema de resolución que RouteService._resolve_id, para que todos
    los callers (pasen el id corto '01' o el UUID real) converjan en la misma fila."""
    value = str(route_id)
    try:
        return str(uuid.UUID(value))
    except ValueError:
        pass
    try:
        return str(uuid.UUID(int=int(value)))
    except (ValueError, OverflowError):
        import hashlib

        return str(uuid.UUID(hashlib.md5(value.encode("utf-8")).hexdigest()))


class SpineMaterializer:
    def __init__(self, client=None) -> None:
        self._client = client
        self._checked = client is not None
        # Fallback in-memory: {tabla: {id: row}}
        self._memory: dict[str, dict[str, dict]] = {"modules": {}, "components": {}, "assets": {}}

    def _supabase(self):
        if not self._checked:
            self._checked = True
            url, key = settings.supabase_url, settings.supabase_key
            if url and "placeholder" not in url and key and "placeholder" not in key:
                try:
                    from supabase import create_client

                    self._client = create_client(url, key)
                except Exception as exc:
                    logger.warning("Spine: no se pudo crear el cliente Supabase: %s", exc)
        return self._client

    # ── IDs deterministas ────────────────────────────────────────────
    @staticmethod
    def module_uuid(route_id: str, module_id: str) -> uuid.UUID:
        return uuid.uuid5(_SPINE_NAMESPACE, f"module:{_normalize_route_id(route_id)}:{module_id}")

    @staticmethod
    def component_uuid(route_id: str, module_id: str, kind: str) -> uuid.UUID:
        return uuid.uuid5(_SPINE_NAMESPACE, f"component:{_normalize_route_id(route_id)}:{module_id}:{kind}")

    @staticmethod
    def asset_uuid(route_id: str, module_id: str, kind: str) -> uuid.UUID:
        return uuid.uuid5(_SPINE_NAMESPACE, f"asset:{_normalize_route_id(route_id)}:{module_id}:{kind}")

    # ── Upserts ──────────────────────────────────────────────────────
    def _upsert(self, table: str, row: dict) -> bool:
        """Upsert por id. True si quedó en Supabase; False si quedó en memoria."""
        client = self._supabase()
        if client is not None:
            try:
                client.table(table).upsert(row, on_conflict="id").execute()
                return True
            except Exception as exc:
                logger.warning("Spine: upsert %s falló, usando memoria: %s", table, exc)
        existing = self._memory[table].get(row["id"], {})
        self._memory[table][row["id"]] = {**existing, **row}
        return False

    def _get(self, table: str, row_id: str) -> Optional[dict]:
        client = self._supabase()
        if client is not None:
            try:
                res = client.table(table).select("*").eq("id", row_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as exc:
                logger.warning("Spine: lectura de %s falló, usando memoria: %s", table, exc)
        return self._memory[table].get(row_id)

    def ensure_component(
        self,
        route_id: str,
        module_id: str,
        kind: str,
        *,
        module_name: Optional[str] = None,
        module_type: Optional[str] = None,
        orden: int = 0,
    ) -> uuid.UUID:
        """Garantiza module + component (upsert determinista) y devuelve el component_id."""
        if kind not in COMPONENT_KINDS:
            raise ValueError(f"kind inválido para el Spine: {kind}")
        now = datetime.now(timezone.utc).isoformat()
        mod_id = self.module_uuid(route_id, module_id)
        comp_id = self.component_uuid(route_id, module_id, kind)

        # Sin metadata nueva, preserva la existente (un upsert posterior — p.ej.
        # una aprobación — no debe pisar titulo/tipo materializados antes).
        existing_module = self._get("modules", str(mod_id)) or {}
        tipo = (
            module_type
            if module_type in MODULE_TYPES
            else existing_module.get("tipo") or "capsula"
        )
        titulo = (
            module_name
            or existing_module.get("titulo")
            or ("Ruta completa" if module_id == ROUTE_LEVEL_MODULE_ID else module_id)
        )
        self._upsert("modules", {
            "id": str(mod_id),
            "learning_path_id": _normalize_route_id(route_id),
            "titulo": titulo,
            "tipo": tipo,
            "orden": orden,
            "updated_at": now,
        })
        self._upsert("components", {
            "id": str(comp_id),
            "modulo_id": str(mod_id),
            "titulo": kind.capitalize(),
            "tipo": kind,
            "orden": 0,
            "updated_at": now,
        })
        return comp_id

    def get_asset(self, route_id: str, module_id: str, kind: str) -> Optional[dict]:
        asset_id = str(self.asset_uuid(route_id, module_id, kind))
        client = self._supabase()
        if client is not None:
            try:
                res = client.table("assets").select("*").eq("id", asset_id).execute()
                if res.data:
                    return res.data[0]
            except Exception as exc:
                logger.warning("Spine: lectura de asset falló, usando memoria: %s", exc)
        return self._memory["assets"].get(asset_id)

    def upsert_asset(
        self,
        route_id: str,
        module_id: str,
        kind: str,
        *,
        estado: Optional[str] = None,
        storage_path: Optional[str] = None,
        word_budget: Optional[int] = None,
        provenance: Optional[dict[str, Any]] = None,
        module_name: Optional[str] = None,
        module_type: Optional[str] = None,
        orden: int = 0,
    ) -> dict:
        """Upsertea el Asset determinista de (ruta, módulo, kind), materializando
        module/component si faltan. Merge de provenance; solo pisa campos provistos.
        Devuelve la fila resultante con `persisted` (bool)."""
        if estado is not None and estado not in ASSET_STATES:
            raise ValueError(f"estado inválido para Asset: {estado}")

        comp_id = self.ensure_component(
            route_id, module_id, kind,
            module_name=module_name, module_type=module_type, orden=orden,
        )
        existing = self.get_asset(route_id, module_id, kind) or {}
        now = datetime.now(timezone.utc).isoformat()
        merged_provenance = {
            **(existing.get("provenance") or {}),
            **(provenance or {}),
        }
        row = {
            "id": str(self.asset_uuid(route_id, module_id, kind)),
            "componente_id": str(comp_id),
            "tipo": kind,
            "estado": estado or existing.get("estado") or "draft",
            "storage_path": storage_path if storage_path is not None else existing.get("storage_path"),
            "word_budget": word_budget if word_budget is not None else existing.get("word_budget"),
            "provenance": merged_provenance,
            "updated_at": now,
        }
        persisted = self._upsert("assets", row)
        return {**row, "persisted": persisted}


_materializer: Optional[SpineMaterializer] = None


def get_spine_materializer() -> SpineMaterializer:
    global _materializer
    if _materializer is None:
        _materializer = SpineMaterializer()
    return _materializer

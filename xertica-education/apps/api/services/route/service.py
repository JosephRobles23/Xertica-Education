from uuid import UUID
from typing import Dict, Any, List, Optional
from models.domain.learning_path import LearningPath
from repositories.learning_path.interface import LearningPathRepositoryInterface

def _empty_pack() -> Dict[str, Any]:
    return {
        "lesson": { "sections": [], "terms": [] },
        "video": { "duration": "00:00", "caption": "", "gradient": "", "emoji": "", "segments": [] },
        "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
        "quiz": { "questions": [] },
        "lab": { "steps": [], "console": [] }
    }

def _default_details(tema: str) -> Dict[str, Any]:
    return {
        "objective": f"Aprender sobre {tema}",
        "customerContext": {},
        "sources": [],
        "pack": _empty_pack(),
        "modules": []
    }

class RouteService:
    def __init__(self, repository: LearningPathRepositoryInterface):
        self.repository = repository

    def _resolve_id(self, route_id: str) -> UUID:
        """Helper to convert route_id to a stable UUID."""
        try:
            return UUID(route_id)
        except ValueError:
            try:
                val = int(route_id)
                return UUID(int=val)
            except Exception:
                import hashlib
                h = hashlib.md5(route_id.encode('utf-8')).hexdigest()
                return UUID(h)

    def _get_short_id(self, u: UUID) -> str:
        """Helper to convert UUID back to a short route_id if it matches our mock pattern."""
        val = u.int
        if 0 < val < 100:
            return str(val).zfill(2)
        return str(u)

    def _to_route(self, path: LearningPath) -> Dict[str, Any]:
        det = path.details or _default_details(path.tema)
        return {
            "id": self._get_short_id(path.id),
            "name": path.titulo,
            "status": path.estado,
            **det
        }

    async def list_routes(self) -> List[Dict[str, Any]]:
        paths = await self.repository.list_all()
        return [self._to_route(path) for path in paths]

    async def create_route(
        self,
        title: str,
        tema: str,
        brief: str,
        customer_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        details = _default_details(tema)
        if brief:
            details["objective"] = brief
        details["customerContext"] = customer_context or {}

        path = LearningPath(titulo=title, tema=tema, estado="borrador", details=details)
        created_path = await self.repository.create(path)
        return self._to_route(created_path)

    async def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        u_id = self._resolve_id(route_id)
        path = await self.repository.get_by_id(u_id)
        if not path:
            return None
        return self._to_route(path)

    async def update_route(self, route_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        u_id = self._resolve_id(route_id)
        path = await self.repository.get_by_id(u_id)
        if not path:
            return None

        db_updates = {}
        if "name" in data:
            db_updates["titulo"] = data["name"]
        if "status" in data:
            db_updates["estado"] = data["status"]
        if "tema" in data:
            db_updates["tema"] = data["tema"]

        _COLUMN_KEYS = ("name", "status", "tema")
        detail_updates = {k: v for k, v in data.items() if k not in _COLUMN_KEYS}
        details = path.details or _default_details(path.tema)
        if detail_updates:
            details.update(detail_updates)
            db_updates["details"] = details

        if db_updates:
            updated = await self.repository.update(u_id, db_updates)
            if updated:
                path = updated

        return {
            "id": self._get_short_id(u_id),
            "name": path.titulo,
            "status": path.estado,
            **details
        }

    async def delete_route(self, route_id: str) -> bool:
        u_id = self._resolve_id(route_id)
        return await self.repository.delete(u_id)

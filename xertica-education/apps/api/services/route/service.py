from uuid import UUID
from typing import Dict, Any, List, Optional
from models.domain.learning_path import LearningPath
from repositories.learning_path.interface import LearningPathRepositoryInterface

class RouteService:
    def __init__(self, repository: LearningPathRepositoryInterface):
        self.repository = repository
        self._details: Dict[UUID, Dict[str, Any]] = {}
        
        # Seed details for initial 01 and 02 paths
        id1 = UUID("00000000-0000-0000-0000-000000000001")
        id2 = UUID("00000000-0000-0000-0000-000000000002")
        
        self._details[id1] = {
            "objective": "Formar a los equipos para diseñar, evaluar y desplegar sistemas de razonamiento avanzado con criterio.",
            "sources": [
                { "title": "Cómo razonan los modelos de última generación", "plat": "YouTube", "verified": True, "quote": "El razonamiento en cadena permite..." },
                { "title": "Gemini para educadores", "plat": "Google Docs", "verified": True, "quote": "..." }
            ],
            "pack": {
                "lesson": { "sections": [], "terms": [] },
                "video": { "duration": "02:04", "caption": "", "gradient": "", "emoji": "", "segments": [] },
                "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
                "quiz": { "questions": [] },
                "lab": { "steps": [], "console": [] }
            },
            "modules": [
                { "id": "r1m1", "num": "01", "name": "Introducción", "type": "intro", "status": "aprobado", "contents": [] }
            ]
        }
        
        self._details[id2] = {
            "objective": "Explorar la generación creativa con criterio.",
            "sources": [],
            "pack": {
                "lesson": { "sections": [], "terms": [] },
                "video": { "duration": "01:48", "caption": "", "gradient": "", "emoji": "", "segments": [] },
                "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
                "quiz": { "questions": [] },
                "lab": { "steps": [], "console": [] }
            },
            "modules": []
        }

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

    async def list_routes(self) -> List[Dict[str, Any]]:
        paths = await self.repository.list_all()
        routes = []
        for path in paths:
            u_id = path.id
            short_id = self._get_short_id(u_id)
            det = self._details.get(u_id, {
                "objective": f"Aprender sobre {path.tema}",
                "sources": [],
                "pack": {
                    "lesson": { "sections": [], "terms": [] },
                    "video": { "duration": "00:00", "caption": "", "gradient": "", "emoji": "", "segments": [] },
                    "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
                    "quiz": { "questions": [] },
                    "lab": { "steps": [], "console": [] }
                },
                "modules": []
            })
            routes.append({
                "id": short_id,
                "name": path.titulo,
                "status": path.estado,
                **det
            })
        return routes

    async def create_route(self, title: str, tema: str, brief: str) -> Dict[str, Any]:
        path = LearningPath(titulo=title, tema=tema, estado="borrador")
        created_path = await self.repository.create(path)
        u_id = created_path.id
        short_id = self._get_short_id(u_id)
        
        self._details[u_id] = {
            "objective": brief or f"Aprender sobre {tema}",
            "sources": [],
            "pack": {
                "lesson": { "sections": [], "terms": [] },
                "video": { "duration": "00:00", "caption": "", "gradient": "", "emoji": "", "segments": [] },
                "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
                "quiz": { "questions": [] },
                "lab": { "steps": [], "console": [] }
            },
            "modules": []
        }
        
        return {
            "id": short_id,
            "name": created_path.titulo,
            "status": created_path.estado,
            **self._details[u_id]
        }

    async def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        u_id = self._resolve_id(route_id)
        path = await self.repository.get_by_id(u_id)
        if not path:
            return None
            
        short_id = self._get_short_id(u_id)
        det = self._details.get(u_id, {
            "objective": f"Aprender sobre {path.tema}",
            "sources": [],
            "pack": {
                "lesson": { "sections": [], "terms": [] },
                "video": { "duration": "00:00", "caption": "", "gradient": "", "emoji": "", "segments": [] },
                "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
                "quiz": { "questions": [] },
                "lab": { "steps": [], "console": [] }
            },
            "modules": []
        })
        
        return {
            "id": short_id,
            "name": path.titulo,
            "status": path.estado,
            **det
        }

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
            
        if db_updates:
            path = await self.repository.update(u_id, db_updates)

        if u_id not in self._details:
            self._details[u_id] = {
                "objective": f"Aprender sobre {path.tema}",
                "sources": [],
                "pack": {
                    "lesson": { "sections": [], "terms": [] },
                    "video": { "duration": "00:00", "caption": "", "gradient": "", "emoji": "", "segments": [] },
                    "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
                    "quiz": { "questions": [] },
                    "lab": { "steps": [], "console": [] }
                },
                "modules": []
            }
            
        for k, v in data.items():
            if k not in ["name", "status"]:
                self._details[u_id][k] = v

        short_id = self._get_short_id(u_id)
        return {
            "id": short_id,
            "name": path.titulo,
            "status": path.estado,
            **self._details[u_id]
        }

    async def delete_route(self, route_id: str) -> bool:
        u_id = self._resolve_id(route_id)
        success = await self.repository.delete(u_id)
        if success and u_id in self._details:
            del self._details[u_id]
        return success

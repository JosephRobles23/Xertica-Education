from uuid import UUID, uuid4
from typing import Dict, Any, List, Optional
from supabase import create_client
from config.settings import settings
from models.domain.learning_path import LearningPath
from repositories.learning_path.interface import LearningPathRepositoryInterface

def _row_to_path(d: Dict[str, Any]) -> LearningPath:
    return LearningPath(
        id=UUID(d["id"]),
        titulo=d["titulo"],
        tema=d["tema"],
        industria=d["industria"],
        estado=d["estado"],
        details=d.get("details")
    )

class SupabaseLearningPathRepository(LearningPathRepositoryInterface):
    def __init__(self):
        self._fallback_store: Dict[UUID, LearningPath] = {}
        self._supabase = None

        # Seed fallback store with initial 01 and 02 paths
        id1 = UUID("00000000-0000-0000-0000-000000000001")
        id2 = UUID("00000000-0000-0000-0000-000000000002")
        self._fallback_store[id1] = LearningPath(
            id=id1,
            titulo="Inteligencia avanzada",
            tema="Razonamiento",
            estado="en-revision",
            details={
                "objective": "Formar a los equipos para diseñar, evaluar y desplegar sistemas de razonamiento avanzado con criterio.",
                "customerContext": {},
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
        )
        self._fallback_store[id2] = LearningPath(
            id=id2,
            titulo="El lado creativo",
            tema="Creatividad",
            estado="generado",
            details={
                "objective": "Explorar la generación creativa con criterio.",
                "customerContext": {},
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
        )

        url = settings.supabase_url
        key = settings.supabase_key
        if url and "placeholder" not in url and key and "placeholder" not in key:
            try:
                self._supabase = create_client(url, key)
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client: {e}")

    async def create(self, path: LearningPath) -> LearningPath:
        if not path.id:
            path.id = uuid4()

        payload = {
            "id": str(path.id),
            "titulo": path.titulo,
            "tema": path.tema,
            "industria": path.industria,
            "estado": path.estado,
            "details": path.details
        }

        if self._supabase:
            try:
                res = self._supabase.table("learning_paths").insert(payload).execute()
                if res.data:
                    return _row_to_path(res.data[0])
            except Exception as e:
                print(f"Supabase create learning path error, falling back to memory: {e}")

        self._fallback_store[path.id] = path
        return path

    async def get_by_id(self, path_id: UUID) -> Optional[LearningPath]:
        if self._supabase:
            try:
                res = self._supabase.table("learning_paths").select("*").eq("id", str(path_id)).execute()
                if res.data:
                    return _row_to_path(res.data[0])
            except Exception as e:
                print(f"Supabase get learning path error, falling back to memory: {e}")

        return self._fallback_store.get(path_id)

    async def list_all(self) -> List[LearningPath]:
        if self._supabase:
            try:
                # Orden por creación: da un "número de orden" estable en el frontend
                # (la última ruta creada queda al final).
                res = self._supabase.table("learning_paths").select("*").order("created_at").execute()
                if res.data:
                    return [_row_to_path(d) for d in res.data]
            except Exception as e:
                print(f"Supabase list learning paths error, falling back to memory: {e}")

        return list(self._fallback_store.values())

    async def update(self, path_id: UUID, data: Dict[str, Any]) -> Optional[LearningPath]:
        if isinstance(path_id, str):
            path_id = UUID(path_id)

        payload = {}
        for k, v in data.items():
            if k in ["titulo", "tema", "industria", "estado", "details"]:
                payload[k] = v

        if self._supabase and payload:
            try:
                res = self._supabase.table("learning_paths").update(payload).eq("id", str(path_id)).execute()
                if res.data:
                    return _row_to_path(res.data[0])
            except Exception as e:
                print(f"Supabase update learning path error, falling back to memory: {e}")

        if path_id in self._fallback_store:
            path = self._fallback_store[path_id]
            for k, v in data.items():
                if hasattr(path, k):
                    setattr(path, k, v)
            return path
        return None

    async def delete(self, path_id: UUID) -> bool:
        if self._supabase:
            try:
                res = self._supabase.table("learning_paths").delete().eq("id", str(path_id)).execute()
                return len(res.data) > 0
            except Exception as e:
                print(f"Supabase delete learning path error, falling back to memory: {e}")

        if path_id in self._fallback_store:
            del self._fallback_store[path_id]
            return True
        return False

from typing import Dict, Any, List

class RouteService:
    def __init__(self):
        # Seed with initial routes 01 and 02
        self._routes: Dict[str, Dict[str, Any]] = {
            "01": {
                "id": "01",
                "name": "Inteligencia avanzada",
                "status": "en-revision",
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
            },
            "02": {
                "id": "02",
                "name": "El lado creativo",
                "status": "generado",
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
        }

    async def list_routes(self) -> List[Dict[str, Any]]:
        """List all learning paths."""
        return list(self._routes.values())

    async def create_route(self, title: str, tema: str, brief: str) -> Dict[str, Any]:
        """Create a new learning path."""
        route_id = str(len(self._routes) + 1).zfill(2)
        new_route = {
            "id": route_id,
            "name": title,
            "status": "borrador",
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
        self._routes[route_id] = new_route
        return new_route

    async def get_route(self, route_id: str) -> Dict[str, Any]:
        """Fetch a single learning path."""
        return self._routes.get(route_id)

    async def update_route(self, route_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Modify fields in a learning path."""
        if route_id not in self._routes:
            return None
        route = self._routes[route_id]
        for k, v in data.items():
            if k in route:
                route[k] = v
        return route

    async def delete_route(self, route_id: str) -> bool:
        """Delete a learning path."""
        if route_id in self._routes:
            del self._routes[route_id]
            return True
        return False

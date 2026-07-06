from fastapi import APIRouter, Depends, HTTPException
from config.dependencies import get_route_service
from services.route.service import RouteService
from typing import Dict, Any, List

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])

@router.get("/", response_model=List[Dict[str, Any]])
async def list_learning_paths(
    route_service: RouteService = Depends(get_route_service)
):
    return await route_service.list_routes()

@router.post("/", response_model=Dict[str, Any])
async def create_learning_path(
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service)
):
    title = payload.get("titulo", "")
    tema = payload.get("tema", "")
    brief = payload.get("brief", "")
    return await route_service.create_route(title, tema, brief)

@router.get("/{route_id}", response_model=Dict[str, Any])
async def get_learning_path(
    route_id: str,
    route_service: RouteService = Depends(get_route_service)
):
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return route

@router.patch("/{route_id}", response_model=Dict[str, Any])
async def update_learning_path(
    route_id: str,
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service)
):
    route = await route_service.update_route(route_id, payload)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return route

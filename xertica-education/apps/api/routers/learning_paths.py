# routers/learning_paths.py
#
# API router managing endpoints for learning paths (also referred to as routes).
# Handles CRUD operations, state transitions (draft, under review, generated), and triggering
# AI-based structure generation workflows.
#
# Related files:
# - services/route/service.py: Performs business logic and DB edits for learning paths.
# - services/jobs/service.py: Creates background generation jobs.

from fastapi import APIRouter, Depends, HTTPException
from config.dependencies import get_route_service, get_jobs_service, get_research_service
from services.route.service import RouteService
from services.jobs.service import JobsService
from services.research.service import ResearchService
from typing import Dict, Any, List

# Define the router namespace under `/learning-paths`.
router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])

@router.get("/", response_model=List[Dict[str, Any]])
async def list_learning_paths(
    route_service: RouteService = Depends(get_route_service)
):
    """
    Fetches a list of all existing learning paths.
    """
    return await route_service.list_routes()

@router.post("/", response_model=Dict[str, Any])
async def create_learning_path(
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service)
):
    """
    Creates a new learning path shell.

    Expects Spanish keys in payload:
    - 'titulo': The title of the path.
    - 'tema': The primary subject/topic.
    - 'brief': The design description or objective.
    """
    title = payload.get("titulo", "")
    tema = payload.get("tema", "")
    brief = payload.get("brief", "")
    return await route_service.create_route(title, tema, brief)

@router.get("/{route_id}", response_model=Dict[str, Any])
async def get_learning_path(
    route_id: str,
    route_service: RouteService = Depends(get_route_service)
):
    """
    Retrieves the complete data of a specific learning path by its ID.

    Raises a 404 error if the learning path does not exist.
    """
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
    """
    Updates fields on an existing learning path (e.g. metadata, title, modules).

    Raises a 404 error if the path does not exist.
    """
    route = await route_service.update_route(route_id, payload)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return route

@router.post("/{route_id}/generate-structure", response_model=Dict[str, Any])
async def generate_structure(
    route_id: str,
    route_service: RouteService = Depends(get_route_service),
    jobs_service: JobsService = Depends(get_jobs_service)
):
    """
    Triggers the generation of modules and contents for a learning path.

    Spawns an asynchronous structure generation background job and inserts a pre-defined
    mock structure (two modules with lessons/videos/quizzes) in draft status ('borrador')
    for preview. Returns the job ID to allow the client to track background progress.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    job_id = await jobs_service.create_job("structure_generation")
    
    mock_modules = [
        {
            "id": "r1m1",
            "num": "01",
            "name": "Introducción a la IA avanzada (Generado)",
            "type": "intro",
            "status": "borrador",
            "contents": [
                { "kind": "lesson", "status": "borrador", "summary": "Texto base introductorio." },
                { "kind": "video", "status": "borrador", "summary": "Cápsula de video explicativa." },
                { "kind": "quiz", "status": "borrador", "summary": "Evaluación breve." }
            ]
        },
        {
            "id": "r1m2",
            "num": "02",
            "name": "Cápsulas de concepto (Generado)",
            "type": "cápsulas",
            "status": "borrador",
            "contents": [
                { "kind": "lesson", "status": "borrador", "summary": "Temas de profundidad." },
                { "kind": "infografia", "status": "borrador", "summary": "Infografía resumen." }
            ]
        }
    ]
    
    await route_service.update_route(route_id, {
        "status": "borrador",
        "modules": mock_modules
    })
    
    return {"job_id": job_id}

@router.post("/{route_id}/deep-research", response_model=Dict[str, Any])
async def run_deep_research(
    route_id: str,
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service),
    research_service: ResearchService = Depends(get_research_service)
):
    """
    Runs a tool-aware deep research pass for a learning path.

    The current implementation is deterministic and mock-backed so the full UX can
    be tested before wiring real YouTube/search providers. It detects tools from
    the brief/modules, applies vendor-specific allowlists, and persists the source
    candidates on the route details.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    research = research_service.run({
        "route_name": route.get("name", ""),
        "brief": payload.get("brief", route.get("objective", "")),
        "modules": route.get("modules", []),
    })
    updated = await route_service.update_route(route_id, {
        "sources": research["sources"]
    })

    return {
        "detected_tools": research["detected_tools"],
        "sources": research["sources"],
        "route": updated,
    }

@router.post("/{route_id}/approve", response_model=Dict[str, Any])
async def approve_learning_path(
    route_id: str,
    route_service: RouteService = Depends(get_route_service)
):
    """
    Approves a proposed learning path structure, changing its status to 'en-revision'.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    updated = await route_service.update_route(route_id, {
        "status": "en-revision"
    })
    return updated

@router.post("/{route_id}/sourcing/approve", response_model=Dict[str, Any])
async def approve_sourcing(
    route_id: str,
    route_service: RouteService = Depends(get_route_service)
):
    """
    Finalizes the content sourcing workflow, transitioning the path status to 'generado'.
    
    Represents the completion of RAG/source document indexing for the learning path.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    updated = await route_service.update_route(route_id, {
        "status": "generado"
    })
    return updated

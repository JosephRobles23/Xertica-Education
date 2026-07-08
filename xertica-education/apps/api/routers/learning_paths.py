# routers/learning_paths.py
#
# API router managing endpoints for learning paths (also referred to as routes).
# Handles CRUD operations, state transitions (draft, under review, generated), and triggering
# AI-based structure generation workflows.
#
# Related files:
# - services/route/service.py: Performs business logic and DB edits for learning paths.
# - services/jobs/service.py: Creates background generation jobs.

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from config.dependencies import (
    get_route_service, get_jobs_service, get_research_service, get_knowledge_base,
    get_sourcing_repository, get_storage_adapter, get_documents_repository,
)
from config.settings import settings
from services.route.service import RouteService
from services.jobs.service import JobsService
from services.research.service import ResearchService
from services.kb.interface import KnowledgeBaseInterface
from services.kb.ingestion import KbIngestionCoordinator, RealDocumentProvider
from repositories.sourcing.interface import SourcingRepositoryInterface
from repositories.sourcing.mapping import route_sources_to_domain
from adapters.parser.simple import SimpleParserAdapter
from models.common import JobStatus, as_uuid
from typing import Dict, Any, List


async def _run_kb_ingestion_job(coordinator, jobs_service, job_id, learning_path_id, sources):
    """Corre la ingesta RAG en background sobre las fuentes verificadas ya persistidas.
    Best-effort: si falla (infra no lista), marca el job y NO propaga — Gate 1 no se
    bloquea (regla de oro · CONTEXT §5)."""
    try:
        await coordinator.ingest_sources(learning_path_id, sources)
        await jobs_service.update_job_status(job_id, JobStatus.COMPLETED)
    except Exception:
        await jobs_service.update_job_status(job_id, JobStatus.FAILED)

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
    customer_context = payload.get("customerContext") or payload.get("customer_context") or {}
    return await route_service.create_route(title, tema, brief, customer_context)

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
    payload: Dict[str, Any] | None = None,
    route_service: RouteService = Depends(get_route_service),
    jobs_service: JobsService = Depends(get_jobs_service),
    documents_repo=Depends(get_documents_repository),
):
    """
    Triggers the generation of modules and contents for a learning path.

    Spawns an asynchronous structure generation background job and inserts a pre-defined
    mock structure (two modules with lessons/videos/quizzes) in draft status ('borrador')
    for preview. Returns the job ID to allow the client to track background progress.

    ADR-0013: el contenido de los documentos subidos (Vía 2) se pasa como `parsed_docs`
    para informar la estructura. El generador mock hoy solo cuenta cuántos hay (regla de
    oro 3: la IA real que redacta módulos a partir del texto va al final); el CONTRATO ya
    queda cableado — `parsed_docs` reutiliza `documents.parsed_md` (sin re-parsear).
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    job_id = await jobs_service.create_job("structure_generation")

    # Contexto de documentos del cliente (ADR-0013): parsed_md de cada doc de la ruta.
    documents = await documents_repo.list_by_learning_path(as_uuid(route_id))
    parsed_docs = [d.parsed_md for d in documents if d.parsed_md]

    customer_context = (payload or {}).get("customerContext") or route.get("customerContext", {}) or {}
    area = customer_context.get("area") or "General"
    industry = customer_context.get("industry") or "contexto del cliente"
    audience = customer_context.get("audienceLevel") or "la audiencia objetivo"
    workspace_note = (
        " con Google Workspace"
        if customer_context.get("usesGoogleWorkspace") == "yes"
        else ""
    )
    # El generador real consumirá `parsed_docs`; el mock solo lo referencia.
    docs_note = f" · {len(parsed_docs)} doc(s) de referencia" if parsed_docs else ""

    mock_modules = [
        {
            "id": "r1m1",
            "num": "01",
            "name": f"Fundamentos aplicados para {area} ({industry})",
            "type": "intro",
            "status": "borrador",
            "contents": [
                { "kind": "lesson", "status": "borrador", "summary": f"Conceptos base adaptados a {industry} y {audience}{docs_note}." },
                { "kind": "video", "status": "borrador", "summary": f"Cápsula con ejemplos del área {area}{workspace_note}." },
                { "kind": "quiz", "status": "borrador", "summary": "Evaluación breve con situaciones del cliente." }
            ]
        },
        {
            "id": "r1m2",
            "num": "02",
            "name": f"Laboratorio contextualizado para {area}",
            "type": "laboratorio",
            "status": "borrador",
            "contents": [
                { "kind": "lesson", "status": "borrador", "summary": "Buenas prácticas y criterios de adopción." },
                { "kind": "infografia", "status": "borrador", "summary": f"Mapa visual de casos de uso en {industry}." },
                { "kind": "lab", "status": "borrador", "summary": f"Actividad práctica basada en propuesta, temario o notas del cliente{workspace_note}." }
            ]
        }
    ]
    
    await route_service.update_route(route_id, {
        "status": "borrador",
        "modules": mock_modules,
        "customerContext": customer_context,
    })

    return {"job_id": job_id, "context_docs": len(parsed_docs)}

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
        "customer_context": payload.get("customerContext") or route.get("customerContext", {}),
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
    background_tasks: BackgroundTasks,
    route_service: RouteService = Depends(get_route_service),
    jobs_service: JobsService = Depends(get_jobs_service),
    knowledge_base: KnowledgeBaseInterface = Depends(get_knowledge_base),
    sourcing_repo: SourcingRepositoryInterface = Depends(get_sourcing_repository),
    storage=Depends(get_storage_adapter),
    documents_repo=Depends(get_documents_repository),
):
    """
    Finalizes the content sourcing workflow, transitioning the path status to 'generado'.

    Gate 1: persiste (UPSERT) las fuentes de deep-research (ADR-0007) y dispara la ingesta RAG
    del corpus aprobado — solo documentos subidos (Vía 2, ADR-0011) — como Job en background,
    sin bloquear la aprobación (ADR-0006 §3). Las fuentes de Vía 1 no se ingestan.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    # 1) UPSERT de las fuentes de deep-research (Vía 1); las de Vía 2 ya se persistieron al subir.
    await sourcing_repo.upsert_sources(route_sources_to_domain(route.get("sources", []), route_id))

    # 2) Corpus a ingestar = solo uploads de Vía 2 (ADR-0011, revisa ADR-0008 §6).
    #    Las de Vía 1 (URLs de YouTube) no se ingestan; se vinculan por módulo (ADR-0012).
    all_sources = await sourcing_repo.list_by_learning_path(as_uuid(route_id))
    corpus = [s for s in all_sources if s.origin == "upload"]

    # 3) Ingesta RAG en background (reutiliza documents.parsed_md; parser como fallback).
    job_id = await jobs_service.create_job("kb_ingestion")
    provider = RealDocumentProvider(storage, documents_repo, SimpleParserAdapter(), settings.storage_bucket)
    coordinator = KbIngestionCoordinator(knowledge_base, provider)
    background_tasks.add_task(
        _run_kb_ingestion_job, coordinator, jobs_service, job_id, route_id, corpus,
    )

    updated = await route_service.update_route(route_id, {"status": "generado"})
    if isinstance(updated, dict):
        updated["ingestionJobId"] = str(job_id)
        updated["sourcesPersisted"] = len(all_sources)
    return updated

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
    get_source_link_repository, get_linker, get_route_structurer,
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


async def _run_structure_job(
    structurer, route_service, jobs_service, job_id, route_id,
    brief, customer_context, parsed_docs,
):
    """Genera la Estructura Propuesta con el LLM (ADR-0014) y la persiste en la ruta.
    Si el LLM falla o el JSON no valida, marca el Job failed (el frontend ofrece
    'Regenerar') — en prod NO cae al mock (decisión del grill)."""
    try:
        modules = await structurer.generate(brief, customer_context, parsed_docs)
        await route_service.update_route(route_id, {
            "status": "borrador",
            "modules": modules,
            "customerContext": customer_context,
        })
        await jobs_service.update_job_status(job_id, JobStatus.COMPLETED)
    except Exception:
        await jobs_service.update_job_status(job_id, JobStatus.FAILED)


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
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any] | None = None,
    route_service: RouteService = Depends(get_route_service),
    jobs_service: JobsService = Depends(get_jobs_service),
    documents_repo=Depends(get_documents_repository),
    structurer=Depends(get_route_structurer),
):
    """
    Genera la Estructura Propuesta (módulos + componentes) con el LLM `route_structurer`
    (Haiku 4.5 · ADR-0014) como Job en background, sin bloquear el request.

    Material-first: consolida `parsed_docs` (documents.parsed_md · ADR-0013) como esqueleto,
    con brief + customerContext para encuadre/personalización. El frontend hace polling del
    Job: skeleton mientras genera; al completar lee route.modules; si falla, 'Regenerar'.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    # Contexto de documentos del cliente (ADR-0013): parsed_md de cada doc de la ruta.
    documents = await documents_repo.list_by_learning_path(as_uuid(route_id))
    parsed_docs = [d.parsed_md for d in documents if d.parsed_md]

    customer_context = (payload or {}).get("customerContext") or route.get("customerContext", {}) or {}
    brief = (payload or {}).get("brief") or route.get("objective", "") or ""

    job_id = await jobs_service.create_job("structure_generation")
    background_tasks.add_task(
        _run_structure_job, structurer, route_service, jobs_service, job_id, route_id,
        brief, customer_context, parsed_docs,
    )
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

    Uses YouTube Data API v3 when YOUTUBE_API_KEY is configured and falls back to
    the deterministic registry otherwise. It detects tools from the brief/modules,
    applies vendor-specific channel allowlists, deduplicates video IDs, and
    persists the source candidates on the route details.
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

@router.post("/{route_id}/link-sources", response_model=Dict[str, Any])
async def link_sources(
    route_id: str,
    payload: Dict[str, Any] | None = None,
    route_service: RouteService = Depends(get_route_service),
    sourcing_repo: SourcingRepositoryInterface = Depends(get_sourcing_repository),
    source_link_repo=Depends(get_source_link_repository),
    linker=Depends(get_linker),
):
    """Vinculación Source↔Módulo on-demand (ADR-0012). Re-rankea el pool de fuentes YA
    recolectadas de la ruta y asigna cada módulo a su fuente más pertinente. NO re-busca
    (eso es `deep-research`). Persiste el mapping (`origin='llm'`) y lo devuelve.

    Body opcional `{ "module_id": "r1m1" }` para vincular un solo módulo; sin él, todos.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    # Pool de fuentes persistidas (con id real). Si aún no lo están (pre-Gate 1), se
    # persisten desde route["sources"] para poder referenciarlas.
    sources = await sourcing_repo.list_by_learning_path(as_uuid(route_id))
    if not sources:
        sources = await sourcing_repo.upsert_sources(
            route_sources_to_domain(route.get("sources", []), route_id)
        )

    modules = route.get("modules", []) or []
    module_id = (payload or {}).get("module_id")
    if module_id:
        modules = [m for m in modules if str(m.get("id")) == str(module_id)]
        if not modules:
            raise HTTPException(status_code=404, detail="Module not found in route")

    links = await linker.link(route_id, modules, sources)
    persisted = await source_link_repo.upsert_links(links)
    why_by_key = {(str(l.source_id), l.module_id): l.why for l in links}
    # url/title de cada fuente: el frontend casa el link contra route.sources por url.
    src_by_id = {str(s.id): s for s in sources if s.id is not None}

    return {
        "links": [
            {
                "source_id": str(l.source_id),
                "module_id": l.module_id,
                "score": l.score,
                "origin": l.origin,
                "why": why_by_key.get((str(l.source_id), l.module_id)),
                "url": getattr(src_by_id.get(str(l.source_id)), "url", None),
                "title": getattr(src_by_id.get(str(l.source_id)), "title", None),
            }
            for l in persisted
        ]
    }


@router.get("/{route_id}/source-links", response_model=Dict[str, Any])
async def list_source_links(
    route_id: str,
    route_service: RouteService = Depends(get_route_service),
    source_link_repo=Depends(get_source_link_repository),
    sourcing_repo: SourcingRepositoryInterface = Depends(get_sourcing_repository),
):
    """Devuelve la vinculación Source↔Módulo persistida de la ruta (ADR-0012). El
    frontend la lee y, si un módulo no tiene fila, cae a la heurística client-side.
    Incluye url/title de la fuente para casarla contra route.sources."""
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
    links = await source_link_repo.list_by_learning_path(as_uuid(route_id))
    sources = await sourcing_repo.list_by_learning_path(as_uuid(route_id))
    src_by_id = {str(s.id): s for s in sources if s.id is not None}
    return {
        "links": [
            {"source_id": str(l.source_id), "module_id": l.module_id,
             "score": l.score, "origin": l.origin,
             "url": getattr(src_by_id.get(str(l.source_id)), "url", None),
             "title": getattr(src_by_id.get(str(l.source_id)), "title", None)}
            for l in links
        ]
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

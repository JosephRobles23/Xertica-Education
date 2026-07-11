# routers/learning_paths.py
#
# API router managing endpoints for learning paths (also referred to as routes).
# Handles CRUD operations, state transitions (draft, under review, generated), and triggering
# AI-based structure generation workflows.
#
# Related files:
# - services/route/service.py: Performs business logic and DB edits for learning paths.
# - services/jobs/service.py: Creates background generation jobs.

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from config.dependencies import (
    get_route_service, get_jobs_service, get_research_service, get_knowledge_base,
    get_sourcing_repository, get_storage_adapter, get_documents_repository,
    get_source_link_repository, get_linker, get_route_structurer,
    get_infographic_service,
    get_approved_research_source_repository,
    get_lab_service,
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
from services.infographic.service import InfographicGenerationError, InfographicService
from services.lab.service import LabService
from models.domain.approved_research_source import ApprovedResearchSource
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import urlparse
import hashlib
from uuid import UUID

AUTO_APPROVE_RELEVANCE_SCORE = 90
MIN_REVIEW_RELEVANCE_SCORE = 70
MAX_MANUAL_REVIEW_SOURCES = 5
REVIEWABLE_SOURCE_KINDS = {"documentation", "article"}


def _to_approved_research_source(
    route_id: str,
    source: dict,
    *,
    module_id: str | None,
    approval_source: str,
    approved_by=None,
) -> ApprovedResearchSource:
    url = source["url"]
    return ApprovedResearchSource(
        route_id=as_uuid(route_id),
        module_id=module_id,
        tool_name=source.get("toolName"),
        title=source.get("title") or url,
        url=url,
        domain=(urlparse(url).hostname or "").lower(),
        source_type=source.get("kind") or "documentation",
        is_verified=bool(source.get("verified")),
        approval_source=approval_source,
        approved_by=approved_by,
        approved_at=datetime.now(timezone.utc),
        metadata=source.get("metadata") or {},
    )


def _source_relevance_score(source: dict) -> int:
    score = source.get("relevanceScore")
    try:
        return int(score)
    except (TypeError, ValueError):
        return 0


def _is_reviewable_source(source: dict) -> bool:
    return source.get("kind") in REVIEWABLE_SOURCE_KINDS and bool(source.get("url"))


def _prepare_research_sources_for_route(sources: list[dict]) -> tuple[list[dict], list[dict]]:
    route_sources: list[dict] = []
    auto_approved: list[dict] = []
    manual_candidates: list[dict] = []

    for source in sources:
        if not _is_reviewable_source(source):
            route_sources.append(source)
            continue

        score = _source_relevance_score(source)
        if source.get("verified") or score > AUTO_APPROVE_RELEVANCE_SCORE:
            approved_source = {
                **source,
                "verified": True,
                "status": "approved",
            }
            route_sources.append(approved_source)
            auto_approved.append(approved_source)
        elif score < MIN_REVIEW_RELEVANCE_SCORE:
            route_sources.append({**source, "status": "rejected"})
        else:
            manual_candidates.append({**source, "status": "requires-review"})

    manual_candidates = sorted(
        manual_candidates,
        key=_source_relevance_score,
        reverse=True,
    )
    route_sources.extend(manual_candidates[:MAX_MANUAL_REVIEW_SOURCES])
    route_sources.extend(
        {**source, "status": "rejected"}
        for source in manual_candidates[MAX_MANUAL_REVIEW_SOURCES:]
    )
    return route_sources, auto_approved


def _resolve_company_name(route: dict) -> str:
    cust_ctx = route.get("customerContext", {}) or {}
    company_name = cust_ctx.get("companyName") or cust_ctx.get("company")
    if not company_name:
        url = cust_ctx.get("url", "") or ""
        if url:
            domain = urlparse(url if url.startswith("http") else f"https://{url}").hostname or ""
            parts = domain.replace("www.", "").split(".")
            if parts:
                company_name = parts[0].capitalize()
    if not company_name:
        company_name = cust_ctx.get("industry") or "la empresa del cliente"
    return company_name


def _derive_module_objective(module: dict, route: dict) -> str:
    explicit = module.get("objective") or module.get("learningObjective") or module.get("learning_objective")
    if explicit:
        return explicit

    description = module.get("description") or module.get("descripcion") or ""
    summary = next(
        (
            content.get("summary")
            for content in module.get("contents", [])
            if content.get("summary")
        ),
        "",
    )
    route_objective = route.get("objective") or ""
    return description or summary or route_objective or f"Aplicar {module.get('name', 'el modulo')} de forma practica."


def _approved_route_sources(route: dict) -> list[dict]:
    approved = []
    for source in route.get("sources", []) or []:
        status = source.get("status")
        if source.get("verified") or status == "approved":
            approved.append(source)
    return approved


logger = logging.getLogger(__name__)


async def _run_structure_job(
    structurer, route_service, jobs_service, job_id, route_id,
    brief, customer_context, parsed_docs,
):
    """Genera la Estructura Propuesta con el LLM (ADR-0014) y la persiste en la ruta.
    Si el LLM falla o el JSON no valida, marca el Job failed (el frontend ofrece
    'Regenerar') — en prod NO cae al mock (decisión del grill)."""
    await jobs_service.update_job_status(job_id, JobStatus.RUNNING)
    try:
        structure = await structurer.generate(brief, customer_context, parsed_docs)
        await route_service.update_route(route_id, {
            "status": "borrador",
            "name": structure["title"],        # → learning_paths.titulo
            "tema": structure["tema"],         # → learning_paths.tema
            "objective": structure["objective"],  # → details.objective
            "modules": structure["modules"],
            "customerContext": customer_context,
        })
        await jobs_service.update_job_status(job_id, JobStatus.COMPLETED)
    except Exception as exc:
        logger.exception("Structure generation job %s failed for route %s", job_id, route_id)
        await jobs_service.update_job_status(job_id, JobStatus.FAILED, error=str(exc))


async def _run_kb_ingestion_job(coordinator, jobs_service, job_id, learning_path_id, sources):
    """Corre la ingesta RAG en background sobre las fuentes verificadas ya persistidas.
    Best-effort: si falla (infra no lista), marca el job y NO propaga — Gate 1 no se
    bloquea (regla de oro · CONTEXT §5)."""
    await jobs_service.update_job_status(job_id, JobStatus.RUNNING)
    try:
        await coordinator.ingest_sources(learning_path_id, sources)
        await jobs_service.update_job_status(job_id, JobStatus.COMPLETED)
    except Exception as exc:
        logger.exception("KB ingestion job %s failed for path %s", job_id, learning_path_id)
        await jobs_service.update_job_status(job_id, JobStatus.FAILED, error=str(exc))

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

async def _run_deep_research_job(
    research_service, route_service, approved_sources_repo, jobs_service,
    job_id, route_id, route, payload,
):
    """Corre el deep research en background y persiste fuentes en la ruta.
    El resultado (detected_tools + sources) queda en job.result para que el
    frontend lo lea al completar el polling."""
    await jobs_service.update_job_status(job_id, JobStatus.RUNNING)
    try:
        research = await research_service.run({
            "route_name": route.get("name", ""),
            "brief": payload.get("brief", route.get("objective", "")),
            "modules": route.get("modules", []),
            "customer_context": payload.get("customerContext") or route.get("customerContext", {}),
        })
        reviewed_sources, automatic_source_candidates = _prepare_research_sources_for_route(
            research["sources"]
        )

        replace_url = payload.get("replaceSourceUrl") or payload.get("replace_source_url")
        if replace_url:
            merged_by_url = {
                source.get("url"): source
                for source in [
                    *[
                        source
                        for source in route.get("sources", [])
                        if source.get("url") != replace_url
                    ],
                    *reviewed_sources,
                ]
                if source.get("url")
            }
            route_sources = list(merged_by_url.values())
        else:
            route_sources = reviewed_sources

        await route_service.update_route(route_id, {"sources": route_sources})
        automatic_sources = [
            _to_approved_research_source(
                route_id,
                source,
                module_id=None,
                approval_source="automatic",
            )
            for source in automatic_source_candidates
        ]
        approved = await approved_sources_repo.upsert(automatic_sources)

        await jobs_service.update_job_status(job_id, JobStatus.COMPLETED, result={
            "detected_tools": research["detected_tools"],
            "sources": route_sources,
            "approved_research_sources": [source.model_dump(mode="json") for source in approved],
        })
    except Exception as exc:
        logger.exception("Deep research job %s failed for route %s", job_id, route_id)
        await jobs_service.update_job_status(job_id, JobStatus.FAILED, error=str(exc))


@router.post("/{route_id}/deep-research", response_model=Dict[str, Any])
async def run_deep_research(
    route_id: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    route_service: RouteService = Depends(get_route_service),
    research_service: ResearchService = Depends(get_research_service),
    jobs_service: JobsService = Depends(get_jobs_service),
    approved_sources_repo=Depends(get_approved_research_source_repository),
):
    """
    Kicks off a tool-aware deep research pass for a learning path as a background
    job and returns its `job_id`; the frontend polls `/jobs/{job_id}` and reads
    `detected_tools` + `sources` from `job.result` when it completes.

    Uses YouTube Data API v3 when YOUTUBE_API_KEY is configured and falls back to
    the deterministic registry otherwise. It detects tools from the brief/modules,
    applies vendor-specific channel allowlists, deduplicates video IDs, and
    persists the source candidates on the route details.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    job_id = await jobs_service.create_job("deep_research")
    background_tasks.add_task(
        _run_deep_research_job, research_service, route_service,
        approved_sources_repo, jobs_service, job_id, route_id, route, payload,
    )
    return {"job_id": str(job_id)}


@router.get("/{route_id}/approved-research-sources", response_model=Dict[str, Any])
async def list_approved_research_sources(
    route_id: str,
    module_id: str | None = None,
    route_service: RouteService = Depends(get_route_service),
    approved_sources_repo=Depends(get_approved_research_source_repository),
):
    if not await route_service.get_route(route_id):
        raise HTTPException(status_code=404, detail="Learning path not found")
    sources = await approved_sources_repo.list_by_route(as_uuid(route_id), module_id=module_id)
    return {"sources": [source.model_dump(mode="json") for source in sources]}


@router.post("/{route_id}/research-sources/review", response_model=Dict[str, Any])
async def review_research_source(
    route_id: str,
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service),
    approved_sources_repo=Depends(get_approved_research_source_repository),
):
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    url = payload.get("url")
    action = payload.get("action")
    if action not in {"approve", "reject"} or not url:
        raise HTTPException(status_code=422, detail="action and url are required")

    candidate = next(
        (
            source
            for source in route.get("sources", [])
            if source.get("url") == url and source.get("kind") in {"documentation", "article", "youtube"}
        ),
        None,
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Research source not found")

    saved = []
    if action == "approve":
        source = _to_approved_research_source(
            route_id,
            candidate,
            module_id=None,
            approval_source="manual",
            approved_by=payload.get("approvedBy") or payload.get("approved_by"),
        )
        saved = await approved_sources_repo.upsert([source])

    next_sources = [
        {**source, "status": "approved" if action == "approve" else "rejected"}
        if source.get("url") == url
        else source
        for source in route.get("sources", [])
    ]
    await route_service.update_route(route_id, {"sources": next_sources})
    return {
        "status": "approved" if action == "approve" else "rejected",
        "source": saved[0].model_dump(mode="json") if saved else None,
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
    payload: Dict[str, Any] | None = None,
    route_service: RouteService = Depends(get_route_service),
    jobs_service: JobsService = Depends(get_jobs_service),
    knowledge_base: KnowledgeBaseInterface = Depends(get_knowledge_base),
    sourcing_repo: SourcingRepositoryInterface = Depends(get_sourcing_repository),
    storage=Depends(get_storage_adapter),
    documents_repo=Depends(get_documents_repository),
    infographic_service: InfographicService = Depends(get_infographic_service),
):
    """
    Finalizes the content sourcing workflow, transitioning the path status to 'generado',
    triggering KB/RAG ingestion, and generating the infographic.
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

    # 4) Update route status to 'generado'
    updated = await route_service.update_route(route_id, {
        "status": "generado",
    })

    if isinstance(updated, dict):
        updated["ingestionJobId"] = str(job_id)
        updated["sourcesPersisted"] = len(all_sources)

    return updated

@router.post("/{route_id}/infographic/regenerate", response_model=Dict[str, Any])
async def regenerate_infographic(
    route_id: str,
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service),
    infographic_service: InfographicService = Depends(get_infographic_service)
):
    """
    Regenerates the infographic for a learning path, optionally incorporating user prompt feedback.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    user_prompt = payload.get("user_prompt")
    aspect_ratio = payload.get("aspect_ratio", "auto")
    
    # Generate stable component_id
    h = hashlib.md5(f"{route_id}:infografia".encode('utf-8')).hexdigest()
    component_id = UUID(h)
    
    # Extract customer company name: explicit field → domain from URL → industry → fallback
    cust_ctx = route.get("customerContext", {}) or {}
    company_name = cust_ctx.get("companyName") or cust_ctx.get("company")
    if not company_name:
        # Try to infer from URL (e.g. "Apple.com" → "Apple")
        url = cust_ctx.get("url", "") or ""
        if url:
            from urllib.parse import urlparse
            domain = urlparse(url if url.startswith("http") else f"https://{url}").hostname or ""
            # Strip www. and TLD → "www.apple.com" → "apple"
            parts = domain.replace("www.", "").split(".")
            if parts:
                company_name = parts[0].capitalize()
    if not company_name:
        company_name = cust_ctx.get("industry") or "la empresa del cliente"
    
    # Extract word budget or fallback
    word_budget = cust_ctx.get("wordBudget") or cust_ctx.get("word_budget") or 120
    
    # Call infographic service with user_prompt and aspect_ratio. If generation
    # fails, do not mutate the existing pack so the previous image remains shown.
    try:
        res = await infographic_service.generate_infographic(
            component_id=component_id,
            sources=route.get("modules", []),
            company_name=company_name,
            word_budget=word_budget,
            user_prompt=user_prompt,
            aspect_ratio=aspect_ratio,
            route_name=route.get("name")
        )
    except InfographicGenerationError as exc:
        raise HTTPException(
            status_code=503 if exc.retryable else 502,
            detail={
                "message": str(exc),
                "code": "infographic_generation_failed",
                "retryable": exc.retryable,
                "previous_asset_preserved": True,
            },
        ) from exc
    
    # Update the pack with infographic data, adding a cache-busting query parameter to the URL
    pack = route.get("pack", {}) or {}
    
    import time
    cache_buster = int(time.time())
    local_png_url = f"{res.get('local_png_url')}?cb={cache_buster}"
    local_pdf_url = f"{res.get('local_pdf_url')}?cb={cache_buster}"
    
    pack["infografia"] = {
        "title": f"Infografía - {route.get('name', 'Curso')}",
        "bullets": [
            "Branding corporativo integrado automáticamente por gpt-image-2.",
            "Paleta de colores y logos oficiales de la compañía inferidos.",
            "Visualización de conceptos clave en alta resolución.",
            f"Basado en la estructura del syllabus con presupuesto de {word_budget} palabras."
        ],
        "footer": ["Descargar PNG", "Descargar PDF"],
        "imageUrl": local_png_url,
        "pdfUrl": local_pdf_url,
        "aspectRatio": aspect_ratio
    }
    
    updated = await route_service.update_route(route_id, {
        "pack": pack
    })
    return updated

from services.quiz.service import QuizService
from config.dependencies import get_quiz_service

@router.post("/{route_id}/modules/{module_id}/quiz/regenerate", response_model=Dict[str, Any])
async def regenerate_quiz(
    route_id: str,
    module_id: str,
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service),
    quiz_service: QuizService = Depends(get_quiz_service)
):
    """
    Generates or regenerates a quiz for a specific module of a learning path.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    modules = route.get("modules", [])
    target_module = None
    for m in modules:
        if m.get("id") == module_id:
            target_module = m
            break
            
    if not target_module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    user_prompt = payload.get("user_prompt")
    
    # Extract customer company name: explicit field → domain from URL → industry → fallback
    cust_ctx = route.get("customerContext", {}) or {}
    company_name = cust_ctx.get("companyName") or cust_ctx.get("company")
    if not company_name:
        url = cust_ctx.get("url", "") or ""
        if url:
            from urllib.parse import urlparse
            domain = urlparse(url if url.startswith("http") else f"https://{url}").hostname or ""
            parts = domain.replace("www.", "").split(".")
            if parts:
                company_name = parts[0].capitalize()
    if not company_name:
        company_name = cust_ctx.get("industry") or "la empresa del cliente"

    # Resolve ID
    resolved_route_id = route_service._resolve_id(route_id)

    # Call quiz service
    res = await quiz_service.generate_quiz(
        route_id=resolved_route_id,
        module_id=module_id,
        module_name=target_module.get("name", "Módulo"),
        module_description=target_module.get("description", "Descripción") or target_module.get("descripcion", ""),
        company_name=company_name,
        user_prompt=user_prompt
    )
    
    # Update module's quiz pack content
    target_module["quiz"] = {
        "pdfUrl": res.get("pdfUrl"),
        "txtUrl": res.get("txtUrl"),
        "questions": res.get("questions")
    }
    
    # Also update module's quiz content ref status to 'generado'
    for c in target_module.get("contents", []):
        if c.get("kind") == "quiz":
            c["status"] = "generado"
            
    updated = await route_service.update_route(route_id, {
        "modules": modules
    })
    return updated


from services.lesson.service import LessonService
from config.dependencies import get_lesson_service

@router.post("/{route_id}/modules/{module_id}/lesson/regenerate", response_model=Dict[str, Any])
async def regenerate_lesson(
    route_id: str,
    module_id: str,
    payload: Dict[str, Any] | None = None,
    route_service: RouteService = Depends(get_route_service),
    lesson_service: LessonService = Depends(get_lesson_service)
):
    """
    Generates or regenerates a lesson for a specific module of a learning path.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    modules = route.get("modules", [])
    target_module = None
    for m in modules:
        if m.get("id") == module_id:
            target_module = m
            break
            
    if not target_module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    user_prompt = payload.get("user_prompt") if payload else None
    
    # Extract customer company name: explicit field → domain from URL → industry → fallback
    cust_ctx = route.get("customerContext", {}) or {}
    company_name = cust_ctx.get("companyName") or cust_ctx.get("company")
    if not company_name:
        url = cust_ctx.get("url", "") or ""
        if url:
            from urllib.parse import urlparse
            domain = urlparse(url if url.startswith("http") else f"https://{url}").hostname or ""
            parts = domain.replace("www.", "").split(".")
            if parts:
                company_name = parts[0].capitalize()
    if not company_name:
        company_name = cust_ctx.get("industry") or "la empresa del cliente"

    # Resolve ID
    resolved_route_id = route_service._resolve_id(route_id)

    # Call lesson service
    res = await lesson_service.generate_lesson(
        route_id=resolved_route_id,
        module_id=module_id,
        module_name=target_module.get("name", "Módulo"),
        module_description=target_module.get("description", "Descripción") or target_module.get("descripcion", ""),
        company_name=company_name,
        user_prompt=user_prompt
    )
    
    # Update module's lesson pack content
    target_module["lesson"] = {
        "pdfUrl": res.get("pdfUrl"),
        "txtUrl": res.get("txtUrl"),
        "sections": res.get("sections", []),
        "terms": res.get("terms", [])
    }
    
    # Also update module's lesson content ref status to 'generado'
    for c in target_module.get("contents", []):
        if c.get("kind") == "lesson":
            c["status"] = "generado"
            
    updated = await route_service.update_route(route_id, {
        "modules": modules
    })
    return updated


@router.post("/{route_id}/modules/{module_id}/lab/regenerate", response_model=Dict[str, Any])
async def regenerate_lab(
    route_id: str,
    module_id: str,
    payload: Dict[str, Any] | None = None,
    route_service: RouteService = Depends(get_route_service),
    lab_service: LabService = Depends(get_lab_service),
    approved_sources_repo=Depends(get_approved_research_source_repository),
):
    """
    Genera o regenera un laboratorio practico para un modulo especifico.
    Usa contexto de ruta, modulo, customer context, fuentes aprobadas y RAG.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    modules = route.get("modules", [])
    target_module = next((module for module in modules if module.get("id") == module_id), None)
    if not target_module:
        raise HTTPException(status_code=404, detail="Module not found")

    resolved_route_id = route_service._resolve_id(route_id)
    user_prompt = payload.get("user_prompt") if payload else None
    company_name = _resolve_company_name(route)
    module_objective = _derive_module_objective(target_module, route)
    customer_context = route.get("customerContext", {}) or {}

    approved_repo_sources = await approved_sources_repo.list_by_route(resolved_route_id, module_id=module_id)
    route_level_approved = _approved_route_sources(route)

    approved_sources_by_key: dict[str, dict] = {}
    for source in route_level_approved:
        key = source.get("url") or source.get("title") or ""
        if key:
            approved_sources_by_key[key] = source

    for source in approved_repo_sources:
        key = source.url or source.title
        approved_sources_by_key[key] = {
            "id": str(source.id) if source.id else None,
            "title": source.title,
            "url": source.url,
            "kind": source.source_type,
            "verified": source.is_verified,
            "status": source.status,
            "toolName": source.tool_name,
            "metadata": source.metadata,
        }

    approved_sources = list(approved_sources_by_key.values())

    lab = await lab_service.generate_lab(
        route_id=resolved_route_id,
        module_id=module_id,
        route_name=route.get("name", "Ruta"),
        route_objective=route.get("objective", ""),
        module_name=target_module.get("name", "Modulo"),
        module_description=target_module.get("description", "Descripcion") or target_module.get("descripcion", ""),
        module_objective=module_objective,
        company_name=company_name,
        customer_context=customer_context,
        approved_sources=approved_sources,
        user_prompt=user_prompt,
    )

    target_module["lab"] = {
        key: value
        for key, value in lab.items()
        if key != "provenance"
    }

    for content in target_module.get("contents", []):
        if content.get("kind") == "lab":
            content["status"] = "generado"

    pack = route.get("pack", {}) or {}
    pack["lab"] = target_module["lab"]

    updated = await route_service.update_route(route_id, {
        "modules": modules,
        "pack": pack,
    })
    return updated


@router.post("/{route_id}/modules/{module_id}/infographic/regenerate", response_model=Dict[str, Any])
async def regenerate_module_infographic(
    route_id: str,
    module_id: str,
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service),
    infographic_service: InfographicService = Depends(get_infographic_service)
):
    """
    Generates or regenerates an infographic for a specific module of a learning path.
    """
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")
        
    modules = route.get("modules", [])
    target_module = None
    for m in modules:
        if m.get("id") == module_id:
            target_module = m
            break
            
    if not target_module:
        raise HTTPException(status_code=404, detail="Module not found")
        
    user_prompt = payload.get("user_prompt")
    aspect_ratio = payload.get("aspect_ratio", "auto")
    
    # Generate stable component_id specific to route + module + infografia
    h = hashlib.md5(f"{route_id}:{module_id}:infografia".encode('utf-8')).hexdigest()
    component_id = UUID(h)
    
    # Extract customer company name
    cust_ctx = route.get("customerContext", {}) or {}
    company_name = cust_ctx.get("companyName") or cust_ctx.get("company")
    if not company_name:
        url = cust_ctx.get("url", "") or ""
        if url:
            from urllib.parse import urlparse
            domain = urlparse(url if url.startswith("http") else f"https://{url}").hostname or ""
            parts = domain.replace("www.", "").split(".")
            if parts:
                company_name = parts[0].capitalize()
    if not company_name:
        company_name = cust_ctx.get("industry") or "la empresa del cliente"
        
    # Extract word budget or fallback
    word_budget = cust_ctx.get("wordBudget") or cust_ctx.get("word_budget") or 120
    
    # Call infographic service with the specific module info. If generation
    # fails, leave the existing module infographic untouched.
    try:
        res = await infographic_service.generate_infographic(
            component_id=component_id,
            sources=[target_module],
            company_name=company_name,
            word_budget=word_budget,
            user_prompt=user_prompt,
            aspect_ratio=aspect_ratio,
            route_name=target_module.get("name", "Módulo"),
            is_module=True
        )
    except InfographicGenerationError as exc:
        raise HTTPException(
            status_code=503 if exc.retryable else 502,
            detail={
                "message": str(exc),
                "code": "infographic_generation_failed",
                "retryable": exc.retryable,
                "previous_asset_preserved": True,
            },
        ) from exc
    
    # Update module's infographic content
    import time
    cache_buster = int(time.time())
    local_png_url = f"{res.get('local_png_url')}?cb={cache_buster}"
    local_pdf_url = f"{res.get('local_pdf_url')}?cb={cache_buster}"
    
    target_module["infografia"] = {
        "title": f"Infografía - {target_module.get('name', 'Módulo')}",
        "bullets": [
            "Conceptos del módulo ilustrados con gpt-image-2.",
            "Integración de branding corporativo.",
            f"Enfoque en {target_module.get('name')}."
        ],
        "footer": ["Descargar PNG", "Descargar PDF"],
        "imageUrl": local_png_url,
        "pdfUrl": local_pdf_url,
        "aspectRatio": aspect_ratio
    }
    
    # Update status of infographic component inside contents list to 'generado'
    for c in target_module.get("contents", []):
        if c.get("kind") == "infografia":
            c["status"] = "generado"
            
    updated = await route_service.update_route(route_id, {
        "modules": modules
    })
    return updated

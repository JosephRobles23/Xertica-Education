from services.jobs.service import JobsService
from services.research.service import ResearchService
from services.route.service import RouteService
from services.kb.interface import KnowledgeBaseInterface
from services.kb.service import KBService
from services.video.service import VideoService
from repositories.jobs.repository import SupabaseJobRepository
from repositories.learning_path.repository import SupabaseLearningPathRepository
from repositories.kb import get_kb_chunk_repository
from repositories.sourcing import get_sourcing_repository as _build_sourcing_repository
from repositories.documents import get_documents_repository as _build_documents_repository
from repositories.source_links import get_source_link_repository as _build_source_link_repository
from adapters.embeddings import get_embedder
from adapters.linker import get_linker as _build_linker
from adapters.storage import get_storage_adapter as _build_storage_adapter

# Instantiate repositories and services
_jobs_repository = SupabaseJobRepository()
_jobs_service = JobsService(_jobs_repository)

_route_repository = SupabaseLearningPathRepository()
_route_service = RouteService(_route_repository)
_research_service = ResearchService()
_video_service = VideoService()

# KB / RAG (ADR-0006): embedder y store se auto-seleccionan (mock ↔ real).
_knowledge_base = KBService(embedder=get_embedder(), repository=get_kb_chunk_repository())

# Sourcing (ADR-0007): repo route-céntrico de fuentes.
_sourcing_repository = _build_sourcing_repository()

# Documentos del usuario (Vía 2 · ADR-0008): storage + repo.
_documents_repository = _build_documents_repository()
_storage_adapter = _build_storage_adapter()

# Vinculación Source↔Módulo (ADR-0012): repo del mapping + linker (mock ↔ real).
_source_link_repository = _build_source_link_repository()
_linker = _build_linker()

def get_jobs_service() -> JobsService:
    return _jobs_service

def get_route_service() -> RouteService:
    return _route_service

def get_research_service() -> ResearchService:
    return _research_service

def get_knowledge_base() -> KnowledgeBaseInterface:
    return _knowledge_base

def get_sourcing_repository():
    return _sourcing_repository

def get_documents_repository():
    return _documents_repository

def get_storage_adapter():
    return _storage_adapter

def get_source_link_repository():
    return _source_link_repository

def get_linker():
    return _linker

def get_video_service() -> VideoService:
    return _video_service

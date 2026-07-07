from services.jobs.service import JobsService
from services.research.service import ResearchService
from services.route.service import RouteService
from services.kb.interface import KnowledgeBaseInterface
from services.kb.service import KBService
from repositories.jobs.repository import SupabaseJobRepository
from repositories.learning_path.repository import SupabaseLearningPathRepository
from repositories.kb import get_kb_chunk_repository
from adapters.embeddings import get_embedder

# Instantiate repositories and services
_jobs_repository = SupabaseJobRepository()
_jobs_service = JobsService(_jobs_repository)

_route_repository = SupabaseLearningPathRepository()
_route_service = RouteService(_route_repository)
_research_service = ResearchService()

# KB / RAG (ADR-0006): embedder y store se auto-seleccionan (mock ↔ real).
_knowledge_base = KBService(embedder=get_embedder(), repository=get_kb_chunk_repository())

def get_jobs_service() -> JobsService:
    return _jobs_service

def get_route_service() -> RouteService:
    return _route_service

def get_research_service() -> ResearchService:
    return _research_service

def get_knowledge_base() -> KnowledgeBaseInterface:
    return _knowledge_base

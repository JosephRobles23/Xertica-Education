from services.jobs.service import JobsService
from services.route.service import RouteService
from repositories.jobs.repository import SupabaseJobRepository
from repositories.learning_path.repository import SupabaseLearningPathRepository

# Instantiate repositories and services
_jobs_repository = SupabaseJobRepository()
_jobs_service = JobsService(_jobs_repository)

_route_repository = SupabaseLearningPathRepository()
_route_service = RouteService(_route_repository)

def get_jobs_service() -> JobsService:
    return _jobs_service

def get_route_service() -> RouteService:
    return _route_service

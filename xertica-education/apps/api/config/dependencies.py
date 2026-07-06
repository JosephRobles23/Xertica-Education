from services.jobs.service import JobsService
from services.route.service import RouteService

# Singleton instances for local memory mock store (to be replaced by DB repositories later)
_jobs_service = JobsService()
_route_service = RouteService()

def get_jobs_service() -> JobsService:
    return _jobs_service

def get_route_service() -> RouteService:
    return _route_service

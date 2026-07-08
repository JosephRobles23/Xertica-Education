from services.jobs.service import JobsService
from services.research.service import ResearchService
from services.route.service import RouteService
from services.video.service import VideoService
from repositories.jobs.repository import SupabaseJobRepository
from repositories.learning_path.repository import SupabaseLearningPathRepository

# Instantiate repositories and services
_jobs_repository = SupabaseJobRepository()
_jobs_service = JobsService(_jobs_repository)

_route_repository = SupabaseLearningPathRepository()
_route_service = RouteService(_route_repository)
_research_service = ResearchService()
_video_service = VideoService()

def get_jobs_service() -> JobsService:
    return _jobs_service

def get_route_service() -> RouteService:
    return _route_service

def get_research_service() -> ResearchService:
    return _research_service

def get_video_service() -> VideoService:
    return _video_service

# routers/jobs.py
#
# API router handling endpoints related to asynchronous background jobs.
# Allows clients to initiate jobs (like long-running AI content generation) and poll for status.
#
# Related files:
# - services/jobs/service.py: The core logic managing job creation, queuing, and updates.
# - config/dependencies.py: FastAPI dependency providers (including DB and service instances).

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from config.dependencies import get_jobs_service
from services.jobs.service import JobsService
from models.dto.requests import CreateJobRequest
from models.dto.responses import JobResponse
from typing import Dict

# Define the router namespace under `/jobs`. This prefixes all paths in this file.
router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("/", response_model=Dict[str, UUID])
async def create_job(
    request: CreateJobRequest,
    jobs_service: JobsService = Depends(get_jobs_service)
):
    """
    Spawns a new asynchronous background job of a specified type.

    Typically used for long-running processes (e.g., AI curriculum generation)
    to prevent blocking HTTP requests. Returns a unique job ID that the client
    can use to poll for status.
    """
    job_id = await jobs_service.create_job(request.type)
    return {"id": job_id}

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    jobs_service: JobsService = Depends(get_jobs_service)
):
    """
    Retrieves the status and progress details of a specific job by its ID.

    If the job does not exist in the database, returns a 404 Not Found error.
    """
    job = await jobs_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from config.dependencies import get_jobs_service
from services.jobs.service import JobsService
from models.dto.requests import CreateJobRequest
from models.dto.responses import JobResponse
from typing import Dict

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("/", response_model=Dict[str, UUID])
async def create_job(
    request: CreateJobRequest,
    jobs_service: JobsService = Depends(get_jobs_service)
):
    job_id = await jobs_service.create_job(request.type)
    return {"id": job_id}

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    jobs_service: JobsService = Depends(get_jobs_service)
):
    job = await jobs_service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

from typing import Dict, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from models.common import JobStatus
from repositories.jobs.interface import JobRepositoryInterface

class JobsService:
    def __init__(self, repository: JobRepositoryInterface):
        self.repository = repository

    async def create_job(self, task_name: str) -> UUID:
        """Creates a new job with status 'queued' and returns its ID."""
        job_id = uuid4()
        await self.repository.create(job_id, task_name)
        return job_id

    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves details of a job by ID, dynamically transitioning state over time."""
        job = await self.repository.get_by_id(job_id)
        if not job:
            return None

        # Dynamic transition based on elapsed seconds
        now = datetime.now(timezone.utc)
        elapsed = (now - job["created_at"]).total_seconds()

        if elapsed < 2:
            status = JobStatus.QUEUED
            progress = 10
        elif elapsed < 6:
            status = JobStatus.RUNNING
            progress = 50
        else:
            status = JobStatus.COMPLETED
            progress = 100

        updates = {
            "status": status,
            "progress": progress,
            "updated_at": now
        }

        if status == JobStatus.COMPLETED and not job.get("result"):
            updates["result"] = {"message": f"Task '{job['type']}' completed successfully."}

        # Persist the dynamic transition updates
        updated_job = await self.repository.update(job_id, updates)
        return updated_job

    async def update_job_status(self, job_id: UUID, status: JobStatus) -> bool:
        """Updates the status of a job directly."""
        updated = await self.repository.update(job_id, {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        })
        return updated is not None

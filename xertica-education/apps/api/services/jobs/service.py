from typing import Dict, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from models.common import JobStatus

class JobsService:
    def __init__(self):
        # In-memory store for mocks, database row logic will replace this
        self._jobs: Dict[UUID, Dict[str, Any]] = {}

    async def create_job(self, task_name: str) -> UUID:
        """Creates a new job with status 'queued' and returns its ID."""
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        self._jobs[job_id] = {
            "id": job_id,
            "type": task_name,
            "status": JobStatus.QUEUED,
            "progress": 0,
            "created_at": now,
            "updated_at": now,
            "result": None,
            "error": None,
        }
        return job_id

    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves details of a job by ID, dynamically transitioning state over time."""
        job = self._jobs.get(job_id)
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

        job["status"] = status
        job["progress"] = progress
        job["updated_at"] = now

        if status == JobStatus.COMPLETED and not job.get("result"):
            job["result"] = {"message": f"Task '{job['type']}' completed successfully."}

        return job

    async def update_job_status(self, job_id: UUID, status: JobStatus) -> bool:
        """Updates the status of a job directly."""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc)
            return True
        return False

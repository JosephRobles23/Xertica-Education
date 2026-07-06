from typing import Dict, Optional, Any
from uuid import UUID, uuid4
from models.common import JobStatus

class JobsService:
    def __init__(self):
        # In-memory store for mocks, database row logic will replace this
        self._jobs: Dict[UUID, Dict[str, Any]] = {}

    async def create_job(self, task_name: str) -> UUID:
        """Creates a new job with status 'queued' and returns its ID."""
        job_id = uuid4()
        self._jobs[job_id] = {
            "id": job_id,
            "task": task_name,
            "status": JobStatus.QUEUED,
        }
        return job_id

    async def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves details of a job by ID."""
        return self._jobs.get(job_id)

    async def update_job_status(self, job_id: UUID, status: JobStatus) -> bool:
        """Updates the status of a job."""
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            return True
        return False

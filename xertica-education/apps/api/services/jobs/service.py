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
        """Retrieves details of a job by ID.

        El estado lo escribe únicamente el background worker (queued -> running ->
        completed/failed). Aquí solo se lee: simular la transición por tiempo hacía
        que el frontend viera 'completed' antes de que el LLM terminara.
        """
        return await self.repository.get_by_id(job_id)

    async def update_job_status(
        self, job_id: UUID, status: JobStatus, error: Optional[str] = None,
        result: Optional[Any] = None,
    ) -> bool:
        """Updates the status of a job directly."""
        updates: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        if error is not None:
            updates["error"] = error
        if result is not None:
            updates["result"] = result
        updated = await self.repository.update(job_id, updates)
        return updated is not None

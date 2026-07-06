import os
from uuid import UUID
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from supabase import create_client
from config.settings import settings
from models.common import JobStatus
from repositories.jobs.interface import JobRepositoryInterface

class SupabaseJobRepository(JobRepositoryInterface):
    def __init__(self):
        self._fallback_store: Dict[UUID, Dict[str, Any]] = {}
        self._supabase = None
        
        url = settings.supabase_url
        key = settings.supabase_key
        if url and "placeholder" not in url and key and "placeholder" not in key:
            try:
                self._supabase = create_client(url, key)
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client: {e}")

    async def create(self, job_id: UUID, task_name: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        job_data = {
            "id": str(job_id),
            "type": task_name,
            "status": JobStatus.QUEUED.value,
            "progress": 0,
            "created_at": now,
            "updated_at": now,
            "result": None,
            "error": None
        }
        
        if self._supabase:
            try:
                res = self._supabase.table("jobs").insert(job_data).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"Supabase create job error, falling back to memory: {e}")
                
        self._fallback_store[job_id] = {
            "id": job_id,
            "type": task_name,
            "status": JobStatus.QUEUED,
            "progress": 0,
            "created_at": datetime.fromisoformat(now.replace("Z", "+00:00")),
            "updated_at": datetime.fromisoformat(now.replace("Z", "+00:00")),
            "result": None,
            "error": None
        }
        return self._fallback_store[job_id]

    async def get_by_id(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        if self._supabase:
            try:
                res = self._supabase.table("jobs").select("*").eq("id", str(job_id)).execute()
                if res.data:
                    job = res.data[0]
                    return {
                        "id": UUID(job["id"]),
                        "type": job["type"],
                        "status": JobStatus(job["status"]),
                        "progress": job["progress"],
                        "created_at": datetime.fromisoformat(job["created_at"].replace("Z", "+00:00")),
                        "updated_at": datetime.fromisoformat(job["updated_at"].replace("Z", "+00:00")),
                        "result": job["result"],
                        "error": job["error"]
                    }
            except Exception as e:
                print(f"Supabase get job error, falling back to memory: {e}")
                
        return self._fallback_store.get(job_id)

    async def update(self, job_id: UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = {}
        for k, v in data.items():
            if isinstance(v, datetime):
                payload[k] = v.isoformat()
            elif isinstance(v, JobStatus):
                payload[k] = v.value
            elif isinstance(v, UUID):
                payload[k] = str(v)
            else:
                payload[k] = v

        if self._supabase:
            try:
                res = self._supabase.table("jobs").update(payload).eq("id", str(job_id)).execute()
                if res.data:
                    job = res.data[0]
                    return {
                        "id": UUID(job["id"]),
                        "type": job["type"],
                        "status": JobStatus(job["status"]),
                        "progress": job["progress"],
                        "created_at": datetime.fromisoformat(job["created_at"].replace("Z", "+00:00")),
                        "updated_at": datetime.fromisoformat(job["updated_at"].replace("Z", "+00:00")),
                        "result": job["result"],
                        "error": job["error"]
                    }
            except Exception as e:
                print(f"Supabase update job error, falling back to memory: {e}")
                
        if job_id in self._fallback_store:
            for k, v in data.items():
                self._fallback_store[job_id][k] = v
            return self._fallback_store[job_id]
        return None

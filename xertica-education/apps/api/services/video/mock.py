from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, Dict, List
from services.video.interface import VideoServiceInterface
from models.dto.requests import StoryboardRequest
from models.dto.responses import VideoJobResponse, VideoJobResult
from models.common import JobStatus

class MockVideoService(VideoServiceInterface):
    def __init__(self):
        # Store mock jobs in memory: job_id -> {created_at, status, progress, result}
        self._jobs: Dict[UUID, dict] = {}

    async def generate_video(
        self,
        component_id: Optional[UUID] = None,
        custom_storyboard: Optional[StoryboardRequest] = None,
        use_mock: bool = False
    ) -> UUID:
        job_id = uuid4()
        self._jobs[job_id] = {
            "created_at": datetime.now(timezone.utc),
            "status": JobStatus.QUEUED,
            "progress": 0,
            "result": None
        }
        return job_id

    async def get_video_job_status(self, job_id: UUID) -> Optional[VideoJobResponse]:
        if job_id not in self._jobs:
            return None

        job = self._jobs[job_id]
        now = datetime.now(timezone.utc)
        elapsed = (now - job["created_at"]).total_seconds()

        # Dynamic transition simulation
        if elapsed < 2:
            status = JobStatus.QUEUED
            progress = 10
        elif elapsed < 6:
            status = JobStatus.RUNNING
            progress = 40
        elif elapsed < 12:
            status = JobStatus.RENDERING
            progress = 75
        else:
            status = JobStatus.COMPLETED
            progress = 100
            if not job["result"]:
                job["result"] = VideoJobResult(
                    video_url="https://zrbspzkavigldnmicmen.supabase.co/storage/v1/object/public/videos/mock-capsule.mp4",
                    duration_seconds=45.2,
                    cost_usd=1.25
                )

        return VideoJobResponse(
            job_id=job_id,
            status=status,
            progress=progress,
            result=job["result"],
            error=None
        )

    async def segment_video(self, video_url: str) -> List[dict]:
        return [
            {"id": "seg1", "title": "Introducción y Arquitectura del Corpus", "start": "00:00", "end": "05:15", "summary": "Explicación teórica de cómo se nutre el corpus de conocimiento."},
            {"id": "seg2", "title": "Demostración Práctica de Verificación", "start": "05:15", "end": "12:45", "summary": "Paso a paso de la verificación cruzada de fuentes contra políticas."},
            {"id": "seg3", "title": "Configuración del Pipeline de Renderizado", "start": "12:45", "end": "20:30", "summary": "Cómo se orquestan Playwright y FFmpeg en segundo plano."},
            {"id": "seg4", "title": "Conclusión y Cierre", "start": "20:30", "end": "25:00", "summary": "Resumen final y pasos sugeridos para integración."}
        ]


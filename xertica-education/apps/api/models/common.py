from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"

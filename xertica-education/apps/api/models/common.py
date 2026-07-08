from enum import Enum
from uuid import NAMESPACE_URL, UUID, uuid5

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


def as_uuid(value) -> UUID:
    """Normaliza un id (str|UUID) a UUID; deriva uno estable si no es un UUID válido."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return uuid5(NAMESPACE_URL, str(value))

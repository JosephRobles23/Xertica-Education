"""Modelos de dominio de la Knowledge Base / RAG (ADR-0006)."""
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class Chunk(BaseModel):
    """Fragmento de una fuente (Markdown) embebido e indexado en pgvector."""
    id: Optional[UUID] = None
    source_id: UUID
    learning_path_id: UUID
    content: str
    token_count: int = 0
    metadata: dict = Field(default_factory=dict)
    embedding: Optional[list[float]] = None


class Citation(BaseModel):
    """Fuente que respalda un fragmento recuperado."""
    source_id: UUID
    title: Optional[str] = None
    url: Optional[str] = None
    snippet: str
    score: float
    verificada_google: bool = False


class GroundedChunk(BaseModel):
    """Resultado de `query`: contenido + su cita."""
    content: str
    citation: Citation


class IngestReport(BaseModel):
    """Resumen de una corrida de ingesta."""
    learning_path_id: UUID
    sources_processed: int
    chunks_created: int
    tokens_embedded: int

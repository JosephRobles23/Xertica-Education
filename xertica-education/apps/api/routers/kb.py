# routers/kb.py
#
# Endpoint de consulta a la Knowledge Base (RAG). Expone el puerto `KnowledgeBase`
# para que los generadores de contenido (Lesson/Video/Infografía/Quiz/Lab) obtengan
# grounding con citas. Ver ADR-0006.

from fastapi import APIRouter, Depends
from typing import List

from config.dependencies import get_knowledge_base
from services.kb.interface import KnowledgeBaseInterface
from models.dto.requests import KbQueryRequest
from models.domain.kb import GroundedChunk

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.post("/query", response_model=List[GroundedChunk])
async def query_kb(
    req: KbQueryRequest,
    kb: KnowledgeBaseInterface = Depends(get_knowledge_base),
):
    """
    Búsqueda semántica grounded con citas, aislada por `learning_path_id`.

    Cada resultado trae el fragmento y su cita (fuente, título, url, score,
    verificada_google). Con `verified_only=true` solo devuelve fuentes verificadas.
    """
    return await kb.query(
        req.learning_path_id, req.query, k=req.k, verified_only=req.verified_only
    )

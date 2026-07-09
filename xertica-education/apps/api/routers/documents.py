# routers/documents.py
#
# Subida de documentos del usuario (Vía 2 · ADR-0008 + ADR-0013). El endpoint valida
# tipo/tamaño, almacena el binario en Storage, lo PARSEA a Markdown verbatim en el acto
# (parse-at-upload · ADR-0013 → documents.parsed_md) y registra la fila `documents` + el
# `Source` Vía 2. Todo upload entra a la KB por default (use_as_source deprecado).

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from typing import Dict, Any

from config.dependencies import (
    get_storage_adapter, get_documents_repository, get_sourcing_repository,
)
from config.settings import settings
from models.common import as_uuid
from models.domain.document import Document
from models.domain.source import Source
from adapters.parser.simple import SimpleParserAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning-paths", tags=["documents"])

_ALLOWED = {"pdf", "docx", "pptx", "xlsx", "txt", "md"}
_LEGACY = {"doc", "ppt", "xls"}
_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/{route_id}/documents", response_model=Dict[str, Any])
async def upload_document(
    route_id: str,
    file: UploadFile = File(...),
    use_as_source: bool = Form(True),
    storage=Depends(get_storage_adapter),
    documents_repo=Depends(get_documents_repository),
    sourcing_repo=Depends(get_sourcing_repository),
):
    """Sube un documento de la Vía 2. Lo almacena, lo parsea a Markdown en el acto
    (parse-at-upload · ADR-0013) y por default lo registra como fuente de la KB
    (`use_as_source` deprecado, siempre true). El `parsed_md` lo reutilizan tanto
    generate-structure (contexto) como la ingesta de Gate 1 (sin re-parsear)."""
    name = (file.filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext in _LEGACY:
        raise HTTPException(415, f"Formato legacy no soportado (.{ext}). Conviértelo a .docx/.pptx/.xlsx.")
    if ext not in _ALLOWED:
        raise HTTPException(415, f"Formato no soportado (.{ext}). Permitidos: {', '.join(sorted(_ALLOWED))}.")

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, "Archivo demasiado grande (máx 20 MB).")

    lp = as_uuid(route_id)
    storage_path = f"{lp}/{file.filename}"
    await storage.upload_file(settings.storage_bucket, storage_path, data)

    # Parse-at-upload (ADR-0013): verbatim → parsed_md. Best-effort: si falla, parsed_md
    # queda None y la ingesta de Gate 1 lo reintenta desde el binario (regla de oro 1).
    parsed_md = None
    parse_error = None
    try:
        parsed_md = await SimpleParserAdapter().parse_document(data, file.filename)
    except Exception as exc:
        logger.exception(
            "Document parsing failed for %s (route %s)", file.filename, route_id
        )
        parse_error = f"{type(exc).__name__}: {exc}"

    doc = await documents_repo.create(Document(
        learning_path_id=lp, storage_path=storage_path,
        filename=file.filename, mime=file.content_type,
        use_as_source=use_as_source, parsed_md=parsed_md,
    ))

    source_id = None
    if use_as_source:
        persisted = await sourcing_repo.upsert_sources([Source(
            learning_path_id=lp, origin="upload", document_id=doc.id,
            title=file.filename, estado="approved",
        )])
        source_id = str(persisted[0].id) if persisted else None

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "use_as_source": doc.use_as_source,
        "parsed": parsed_md is not None,
        "parse_error": parse_error,
        "source_id": source_id,
    }

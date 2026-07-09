from __future__ import annotations

import json
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException

from adapters.parser.simple import SimpleParserAdapter
from config.dependencies import (
    get_documents_repository,
    get_route_service,
    get_sourcing_repository,
    get_storage_adapter,
)
from config.settings import settings
from models.common import as_uuid
from models.domain.document import Document
from models.domain.source import Source
from services.route.service import RouteService

router = APIRouter(prefix="/learning-paths", tags=["google-drive"])

_DRIVE_API = "https://www.googleapis.com/drive/v3"
_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
_GOOGLE_EXPORT_MIME: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}


def _bearer_headers(access_token: str) -> dict[str, str]:
    token = access_token.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Google access token is required")
    return {"Authorization": f"Bearer {token}"}


def _sanitize_filename(name: str, fallback: str = "drive-file") -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in " ._-" else "_" for ch in name).strip()
    return cleaned or fallback


async def _download_drive_file(
    *,
    file_id: str,
    name: str,
    mime_type: str,
    access_token: str,
) -> tuple[bytes, str, str]:
    headers = _bearer_headers(access_token)
    async with httpx.AsyncClient(timeout=60) as client:
        if mime_type.startswith("application/vnd.google-apps."):
            export_mime, ext = _GOOGLE_EXPORT_MIME.get(mime_type, ("text/plain", ".txt"))
            resp = await client.get(
                f"{_DRIVE_API}/files/{file_id}/export",
                params={"mimeType": export_mime},
                headers=headers,
            )
            filename = _sanitize_filename(name)
            if "." not in filename:
                filename = f"{filename}{ext}"
            output_mime = export_mime
        else:
            resp = await client.get(
                f"{_DRIVE_API}/files/{file_id}",
                params={"alt": "media"},
                headers=headers,
            )
            filename = _sanitize_filename(name)
            output_mime = mime_type or "application/octet-stream"

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Google Drive download failed: {resp.text}",
        )
    return resp.content, filename, output_mime


async def _persist_route_document(
    *,
    route_id: str,
    filename: str,
    mime_type: str,
    data: bytes,
    use_as_source: bool,
    storage,
    documents_repo,
    sourcing_repo,
):
    lp = as_uuid(route_id)
    storage_path = f"{lp}/drive/{filename}"
    await storage.upload_file(settings.storage_bucket, storage_path, data)

    parsed_md = None
    try:
        parsed_md = await SimpleParserAdapter().parse_document(data, filename)
    except Exception:
        parsed_md = None

    doc = await documents_repo.create(
        Document(
            learning_path_id=lp,
            storage_path=storage_path,
            filename=filename,
            mime=mime_type,
            use_as_source=use_as_source,
            parsed_md=parsed_md,
        )
    )

    source_id = None
    if use_as_source:
        persisted = await sourcing_repo.upsert_sources(
            [
                Source(
                    learning_path_id=lp,
                    origin="upload",
                    document_id=doc.id,
                    title=filename,
                    tipo="google_drive",
                    estado="approved",
                )
            ]
        )
        source_id = str(persisted[0].id) if persisted else None

    return {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "use_as_source": doc.use_as_source,
        "parsed": parsed_md is not None,
        "source_id": source_id,
    }


def _route_export_markdown(route: Dict[str, Any]) -> bytes:
    lines = [
        f"# {route.get('name') or route.get('titulo') or 'Ruta de aprendizaje'}",
        "",
        f"**Tema:** {route.get('tema') or 'Sin tema definido'}",
        "",
        "## Objetivo",
        "",
        route.get("objective") or route.get("brief") or "Sin objetivo definido.",
        "",
        "## Modulos",
    ]
    for module in route.get("modules", []) or []:
        lines.extend(
            [
                "",
                f"### {module.get('title') or module.get('name') or module.get('id') or 'Modulo'}",
                "",
                module.get("objective") or module.get("summary") or "",
            ]
        )
        components = module.get("components") or module.get("contents") or []
        if components:
            lines.append("")
            for component in components:
                title = component.get("title") or component.get("kind") or component.get("type") or "Contenido"
                lines.append(f"- {title}")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


async def _upload_to_drive(
    *,
    access_token: str,
    filename: str,
    mime_type: str,
    data: bytes,
) -> Dict[str, Any]:
    boundary = "xertica_drive_boundary"
    metadata = {"name": filename, "mimeType": mime_type}
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    headers = {
        **_bearer_headers(access_token),
        "Content-Type": f"multipart/related; boundary={boundary}",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{_UPLOAD_API}/files",
            params={"uploadType": "multipart", "fields": "id,name,mimeType,webViewLink"},
            headers=headers,
            content=body,
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Google Drive upload failed: {resp.text}",
        )
    return resp.json()


@router.post("/{route_id}/drive-documents", response_model=Dict[str, Any])
async def upload_drive_document(
    route_id: str,
    payload: Dict[str, Any],
    storage=Depends(get_storage_adapter),
    documents_repo=Depends(get_documents_repository),
    sourcing_repo=Depends(get_sourcing_repository),
):
    file_id = payload.get("file_id")
    name = payload.get("name") or "drive-file"
    mime_type = payload.get("mime_type") or "application/octet-stream"
    if not file_id:
        raise HTTPException(status_code=422, detail="file_id is required")

    data, filename, downloaded_mime = await _download_drive_file(
        file_id=file_id,
        name=name,
        mime_type=mime_type,
        access_token=payload.get("access_token", ""),
    )
    persisted = await _persist_route_document(
        route_id=route_id,
        filename=filename,
        mime_type=downloaded_mime,
        data=data,
        use_as_source=bool(payload.get("use_as_source", True)),
        storage=storage,
        documents_repo=documents_repo,
        sourcing_repo=sourcing_repo,
    )
    return {
        **persisted,
        "drive_file": {
            "file_id": file_id,
            "name": name,
            "mime_type": mime_type,
            "web_view_link": payload.get("web_view_link"),
        },
    }


@router.post("/{route_id}/export/google-drive", response_model=Dict[str, Any])
async def export_route_to_google_drive(
    route_id: str,
    payload: Dict[str, Any],
    route_service: RouteService = Depends(get_route_service),
):
    route = await route_service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Learning path not found")

    filename = _sanitize_filename(payload.get("filename") or f"{route.get('name') or route_id} - asset final.md")
    if not filename.lower().endswith(".md"):
        filename = f"{filename}.md"

    uploaded = await _upload_to_drive(
        access_token=payload.get("access_token", ""),
        filename=filename,
        mime_type="text/markdown",
        data=_route_export_markdown(route),
    )
    return {
        "file_id": uploaded.get("id"),
        "name": uploaded.get("name"),
        "mime_type": uploaded.get("mimeType"),
        "web_view_link": uploaded.get("webViewLink"),
    }

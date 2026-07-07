"""Chunking estructural de Markdown para el RAG (ADR-0006 §2).

Corta por encabezados Markdown, subdivide secciones grandes por párrafos, empaca
piezas contiguas hasta ~target_tokens y añade un solape de contexto entre chunks.
El conteo de tokens es una heurística barata (~4 chars/token) — el tope es suave.
"""
from __future__ import annotations

TARGET_TOKENS = 500
OVERLAP_TOKENS = 64


def estimate_tokens(text: str) -> int:
    """Estimación barata de tokens (~4 caracteres por token en cl100k)."""
    return max(1, len(text) // 4)


def _split_sections(markdown: str) -> list[str]:
    """Divide en secciones por headings ('#..'), conservando cada heading con su cuerpo."""
    sections: list[str] = []
    current: list[str] = []
    for line in markdown.splitlines():
        if line.lstrip().startswith("#") and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]


def _split_oversized(section: str, target_tokens: int) -> list[str]:
    """Parte una sección que excede el target empacando por párrafos (línea en blanco)."""
    paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]
    out: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if buf and estimate_tokens(candidate) > target_tokens:
            out.append(buf)
            buf = para
        else:
            buf = candidate
    if buf:
        out.append(buf)
    return out


def _overlap_tail(text: str, overlap_tokens: int) -> str:
    """Últimas ~overlap_tokens palabras del texto, para dar contexto al siguiente chunk."""
    if overlap_tokens <= 0:
        return ""
    words = text.split()
    n = max(1, int(overlap_tokens * 0.75))  # ~0.75 palabras por token
    return " ".join(words[-n:]) if words else ""


def chunk_markdown(
    text: str,
    target_tokens: int = TARGET_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    # 1) secciones estructurales, subdividiendo las que exceden el target
    pieces: list[str] = []
    for section in _split_sections(text):
        if estimate_tokens(section) > target_tokens:
            pieces.extend(_split_oversized(section, target_tokens))
        else:
            pieces.append(section)

    # 2) empaca piezas contiguas hasta el target
    packed: list[str] = []
    buf = ""
    for piece in pieces:
        candidate = f"{buf}\n\n{piece}".strip() if buf else piece
        if buf and estimate_tokens(candidate) > target_tokens:
            packed.append(buf)
            buf = piece
        else:
            buf = candidate
    if buf:
        packed.append(buf)

    # 3) solape: prepende la cola del chunk previo
    if overlap_tokens <= 0 or len(packed) <= 1:
        return packed
    result = [packed[0]]
    for i in range(1, len(packed)):
        tail = _overlap_tail(packed[i - 1], overlap_tokens)
        result.append(f"{tail}\n\n{packed[i]}".strip() if tail else packed[i])
    return result

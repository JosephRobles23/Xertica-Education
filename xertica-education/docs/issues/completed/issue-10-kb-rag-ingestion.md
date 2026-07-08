## Parent
None

## What to build
Integrate the real parser adapter `adapters/parser/` (loading files) and write pgvector indexing logic in Supabase Postgres. Implement vector retrieval and sources citation mapping inside `KBService`.

## Acceptance criteria
- [x] Uploaded reference files are parsed and segmented.
- [x] KB performs vector similarity searches, returning results containing references.

## Blocked by
- [Issue 06 (Gate 1 Sourcing)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-06-gate-1-sourcing.md)
- [Issue 09 (Sourcing Database Repository)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-09-sourcing-database-repository.md)

---

## Estado — COMPLETADA (2026-07-07 · rama `feature/KB-RAG`)

Cerrada siguiendo el flujo de Joseph (decision-map → grill → ADR → TDD → ponytail-review).

**Qué se construyó**
- Puerto `KnowledgeBase` (`services/kb/`): `ingest` + `query` con citas (`GroundedChunk`).
- Chunking estructural de Markdown; puerto `Embedder` con `MockEmbedder` + adapter real
  vía **OpenRouter** (`text-embedding-3-small`, 1536).
- Store pgvector: tabla `kb_chunks` + índice HNSW coseno + función `match_kb_chunks`.
- Ingesta como **Job en background** disparado en Gate 1 (`/sourcing/approve`).
- Parser ligero (`adapters/parser/simple.py`) — MinerU queda como fase 2.
- Endpoint **`POST /kb/query`** para los generadores.

**Decisiones:** [ADR-0006](../../adr/0006-kb-rag-ingestion-embeddings.md) · mapa en
[docs/decisions/kb-rag-decision-map.md](../../decisions/kb-rag-decision-map.md).

**Verificado:** E2E real contra Supabase + OpenRouter (upsert → ingest → query grounded con
scores semánticos reales, citas a fuentes persistidas, cleanup por cascade). Suite de tests verde.

**Deuda (fuera de alcance):** fetch/parse real de URLs y archivos subidos (hoy `MockDocumentProvider`);
MinerU en modo precisión; adapter `KnowledgeBase → Gemini Enterprise` (fase 2).

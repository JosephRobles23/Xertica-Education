# ADR-0006: Ingesta RAG de la Knowledge Base — embeddings, chunking y contrato

- **Estado:** Aceptado
- **Ámbito:** `apps/api/services/kb/`, `apps/api/adapters/embeddings/` (nuevo), `apps/api/adapters/parser/`, `supabase/migrations/`
- **Issue:** [issue-10 · KB RAG ingestion](../issues/pending/joseph/issue-10-kb-rag-ingestion.md) · rama `feature/KB-RAG`
- **Relación:** **construye sobre [ADR-0001](0001-pgvector-supabase-knowledge-base.md)** (pgvector como store) y hereda RLS de [ADR-0004](0004-supabase-postgres-persistence.md); aplica [ADR-0002](0002-mocks-first-class-citizens.md) (mocks first-class).

## Contexto

`issue-10` pide ingesta real (parse → chunk → embed → pgvector) y `query` con citas dentro de `KBService`. ADR-0001 fijó **pgvector en Supabase** como store, pero quedaban abiertas seis decisiones que el schema y el código necesitan cerrar antes de codificar. El contenido del dominio es **español**, lo que pesa en la elección del modelo de embedding. El schema actual (`20260706120000_init_schema.sql`) **no tiene** tabla de chunks/vectores.

Resueltas en una sesión de grilling (`/grill-with-docs`) sobre el [mapa de decisiones](../decisions/kb-rag-decision-map.md).

## Decisión

1. **Embeddings:** OpenAI **`text-embedding-3-small`**, **dimensión nativa 1536**. Se accede vía un puerto nuevo `Embedder` con adapter **real** (`OpenAIEmbedder`) y **mock** determinista (`MockEmbedder`, vector estable derivado por hash) — así el pipeline corre sin claves (regla de oro). Requiere `OPENAI_API_KEY` **solo server-side**.
   > **Supersede** la línea `embeddings: text-embedding-google` de `architecture.md` (§models.yaml). Motivo: se optó por OpenAI multilingüe barato (~$0.02/1M tokens) en vez del gateway Google previsto. Se declara el conflicto explícitamente (CONTEXT.md §6). Fijar la **dimensión** (no el modelo) desacopla el schema: se puede cambiar de modelo mientras la dim siga en 1536, sin re-migrar.
2. **Chunking:** **estructural** — cortar por headings del Markdown que devuelve el parser y empacar a **~500 tokens con ~64 de solape**. Mejor grounding/citas que una ventana ciega.
3. **Disparo de la ingesta:** **Job asíncrono** (reutiliza `JobsService`, `queued→running→completed`), disparado tras Gate 1 (`/sourcing/approve`). No bloquea el request HTTP mientras corren las llamadas de embedding.
4. **Store:** nueva tabla **`kb_chunks`** (`id`, `source_id` FK, `learning_path_id` FK, `content`, `embedding vector(1536)`, `metadata jsonb`, `token_count`), índice **HNSW `vector_cosine_ops`** (embeddings normalizados → coseno), **RLS activo sin políticas** (hereda ADR-0004). FKs `on delete cascade` bajo la fuente/ruta.
5. **Parser MVP:** adapter **ligero** (`pypdf` / `python-docx` / `python-pptx`) → Markdown detrás de `BaseParserAdapter`. **MinerU** queda como swap de adapter en **fase 2** (evita dependencia GPU en el MVP). El puerto es de Joseph (cara KB); la subida Vía 2 de Arantza consume el mismo adapter.
6. **Puerto `KnowledgeBase`:**
   - `ingest(learning_path_id, sources) -> IngestReport` (chunks creados, tokens, fuentes procesadas).
   - `query(learning_path_id, text, k=8, verified_only=False) -> list[GroundedChunk]`.
   - `GroundedChunk = { content, citation }`, `citation = { source_id, title, url, snippet, score, verificada_google }`. La búsqueda **filtra por `learning_path_id`** (aislamiento por ruta).

## Consecuencias

- **+** El pipeline RAG funciona **sin claves** con `MockEmbedder`, cumpliendo "ninguna feature bloquea a otra"; lo real se activa con `OPENAI_API_KEY`.
- **+** Dimensión fija (1536) desacopla el modelo del schema.
- **+** El puerto `KnowledgeBase` estabiliza el contrato para Santiago/Sebas/Shared (consumidores de grounding) desde ya, con datos mock.
- **−** Se introduce **OpenAI** como proveedor fuera del gateway Google previsto → reflejarlo en `models.yaml`/config y en el modelo de costos.
- **−** Cambiar la dimensión obliga a **re-embeder + migración**.
- **Deuda registrada:** MinerU real (fase 2), adapter `KnowledgeBase → Gemini Enterprise` (fase 2, bloqueado por licencias), y el gateway unificado de modelos (`models.yaml`) que hoy no existe.

# Decision Map — KB / RAG (issue-10) · rama `feature/KB-RAG`

> Mapa de decisiones (skill `/decision-mapping`) para la ingesta RAG de Joseph.
> Se carga completo como contexto. Mantener compacto; enlazar assets, no duplicarlos.
> Alcance: `apps/api/services/kb/`, `apps/api/adapters/parser/`, `apps/api/adapters/embeddings/` (nuevo), `supabase/migrations/` (tabla de chunks).

## Ya decidido (resuelto inline — sin niebla)

- **Store vectorial:** pgvector en Supabase, reutilizando la BD principal ([[docs/adr/0001-pgvector-supabase-knowledge-base]]).
- **KB detrás de un puerto `KnowledgeBase`:** adapter intercambiable (Gemini Enterprise/NotebookLM en fase 2, bloqueado por licencias). `architecture.md` decisión #3.
- **Familia de embeddings:** Google `text-embedding-*` vía el gateway `models.yaml` (`architecture.md:441`). El modelo/dimensión exactos → ticket #1.
- **Dos vías de ingesta** convergen en Gate 1 y en la KB de Joseph (hub). `architecture.md` §5.
- **Regla de oro / mocks first-class** ([[docs/adr/0002-mocks-first-class-citizens]]): todo puerto nuevo trae su `mock` que cumple el contrato.

---

## Frontera (tickets abiertos)

## #1: ¿Modelo de embedding y dimensión del vector?

Type: Discuss → **ADR** (irreversible: la dimensión se hornea en el schema; re-embeder es costoso)

### Question
El contenido del dominio es **español**. ¿Qué modelo Google y qué `vector(N)` fijamos para `kb_chunks.embedding`? ¿Adapter real, mock, o ambos para el MVP?

### Answer
**RESUELTO** → OpenAI **`text-embedding-3-small`**, **1536 dim** (nativo). Puerto `Embedder` con adapter real + `MockEmbedder`. Supera la línea `text-embedding-google` de `architecture.md`. Ver [[docs/adr/0006-kb-rag-ingestion-embeddings]].

## #2: ¿Estrategia de chunking?

Blocked by: #1
Type: Discuss

### Question
El parser devuelve **Markdown**. ¿Chunking por estructura (headings) con límite de tokens y solape, o ventana fija de tokens? ¿Tamaño/solape?

### Answer
**RESUELTO** → **estructural** por headings, empacado a **~500 tokens / ~64 de solape**.

## #3: Contrato del puerto `KnowledgeBase`

Type: Discuss (`/domain-modeling`)

### Question
Firma de `query(...)` y forma de la **cita**: ¿qué campos retorna cada resultado grounded (source_id, título, url, snippet, score, verificada_google)? ¿Se filtra por `learning_path_id`?

### Answer
**RESUELTO** → `ingest(learning_path_id, sources) -> IngestReport` y `query(learning_path_id, text, k=8, verified_only=False) -> list[GroundedChunk]`. `GroundedChunk = {content, citation{source_id, title, url, snippet, score, verificada_google}}`. Filtra por `learning_path_id`. Ver ADR-0006 §6.

## #4: ¿Disparo de la ingesta — síncrono o Job?

Type: Discuss

### Question
La ingesta (parse + chunk + embed + upsert) es pesada. ¿Corre inline en `POST /sourcing/approve` (Gate 1) o como **Job** asíncrono con polling (patrón `JobsService`)?

### Answer
**RESUELTO** → **Job asíncrono** (reutiliza `JobsService`), disparado tras Gate 1.

## #5: Migración del schema `kb_chunks`

Blocked by: #1, #3
Type: Discuss · Prototype

### Question
Columnas (`id`, `source_id`, `learning_path_id`, `content`, `embedding vector(N)`, `metadata`, `token_count`), tipo de índice (`ivfflat` vs `hnsw`), y RLS (habilitado sin policy, como el resto).

### Answer
**RESUELTO** → `kb_chunks(id, source_id, learning_path_id, content, embedding vector(1536), metadata jsonb, token_count)`, índice **HNSW `vector_cosine_ops`**, RLS on sin policy, FKs `on delete cascade`.

## #6: Alcance del parser para el MVP

Type: Discuss

### Question
`architecture.md` pone MinerU (GPU, "en evaluación") como parser. ¿MVP con parser ligero (`pypdf`/`python-docx`) detrás de `BaseParserAdapter` y MinerU como fase 2? ¿Dónde queda el límite de propiedad con Arantza (Vía 2 / `adapters/parser`)?

### Answer
**RESUELTO** → parser **ligero** (`pypdf`/`python-docx`/`python-pptx`) → Markdown detrás de `BaseParserAdapter`; MinerU = swap fase 2. El puerto es de Joseph; la subida Vía 2 de Arantza consume el mismo adapter.

---

## Estado del mapa: **frontera resuelta.** Sin niebla → a implementación (`/to-prd` → `/to-issues` → `/tdd` + `/ponytail`).

---

### Ruta al finish line
#1 → (#2, #3) → #5 → implementación (`/tdd` + `/ponytail`). #4 y #6 son paralelos.
Decisiones irreversibles de #1 (y el contrato de #3) → **ADR-0006** vía `/grill-with-docs`.

# Architecture Decision Records (ADR)

Registro de decisiones de arquitectura del monorepo **Xertica Education**. Un ADR captura una decisión significativa, su contexto y sus consecuencias, para no re-litigar lo ya resuelto.

Convención (repo de contexto único; ver [`docs/agents/domain.md`](../agents/domain.md) y [`CONTEXT.md`](../../CONTEXT.md)):

- Un archivo por decisión, numerado secuencialmente: `NNNN-titulo-en-kebab-case.md`.
- No se editan ADRs aceptados; para revertir o cambiar una decisión se crea uno nuevo que **supersede** al anterior.
- Si tu trabajo contradice un ADR, decláralo explícitamente en tu output en vez de sobrescribirlo en silencio.

Usa la [plantilla](0000-template.md) para nuevos ADRs.

## Índice

| ADR | Título | Estado |
| :--- | :--- | :--- |
| [0001](0001-pgvector-supabase-knowledge-base.md) | pgvector en Supabase como Knowledge Base | Aceptado |
| [0002](0002-mocks-first-class-citizens.md) | Mocks como first-class citizens | Aceptado |
| [0003](0003-domain-naming-in-english.md) | Nomenclatura del dominio en inglés | Aceptado |
| [0004](0004-supabase-postgres-persistence.md) | Supabase Postgres como persistencia primaria | Aceptado |
| [0005](0005-full-spine-schema.md) | Schema del Spine completo desde el día 1 | Aceptado |
| [0006](0006-kb-rag-ingestion-embeddings.md) · KB | Ingesta KB/RAG + embeddings vía OpenRouter | Aceptado |
| [0006](0006-video-asset-source-of-truth.md) · Video ⚠️ | Video Asset como fuente de verdad | Aceptado |
| [0007](0007-source-route-centrica-sourcing.md) · KB | Sourcing route-céntrico (`sources.learning_path_id`) | Aceptado |
| [0007](0007-declarative-render-plan.md) · Video ⚠️ | Render Plan declarativo | Aceptado |
| [0008](0008-document-parsing-via2-ingestion.md) · KB | Parsing e ingesta de documentos (Vía 2) | Aceptado · rev. por 0011/0013 |
| [0008](0008-remotion-composition-engine.md) · Video ⚠️ | Remotion como motor de composición | Aceptado |
| [0009](0009-expanded-visual-types.md) · Video | Tipos visuales expandidos (14) | Aceptado |
| [0010](0010-openmontage-git-submodule.md) · Video | OpenMontage como git submodule | Aceptado |
| [0011](0011-kb-solo-via2-linking-por-modulo.md) · KB | KB solo-Vía-2; Vía 1 se vincula por módulo | Aceptado |
| [0011](0011-deep-research-without-pre-generation-gate.md) · Video ⚠️ | Deep Research sin gate previo a la generación | Aceptado |
| [0012](0012-vinculacion-source-modulo-hibrida.md) · KB | Vinculación source↔módulo híbrida (`source_module_links`) | Aceptado |
| [0012](0012-pacing-y-densidad-visual-de-guion.md) · Video ⚠️ | Pacing y densidad visual de guión | Aceptado |
| [0013](0013-parse-at-upload-parsed-md.md) · KB | Parse-at-upload (`documents.parsed_md`) | Aceptado |
| [0014](0014-structure-generation-llm.md) · KB | Estructura Propuesta vía LLM (Gate 0) | Aceptado |
| [0015](0015-route-details-persistence-and-llm-identity.md) · KB | Persistencia de detalles de ruta y título/tema/objetivo por LLM | Aceptado |
| [0016](0016-approved-research-sources.md) · Research | URLs aprobadas fuera de la KB | Aceptado |
| [0017](0017-deep-research-source-review-policy.md) · Research | Política de revisión de fuentes de Deep Research | Aceptado |

> ⚠️ **Colisión de numeración (deuda documental):** las ramas `main` (video) y `feature/KB-RAG` (KB) desarrollaron en paralelo y **reutilizaron 0006/0007/0008/0011/0012** para decisiones distintas. Ambos archivos coexisten con nombres distintos. Renumerar los duplicados es un cleanup pendiente.

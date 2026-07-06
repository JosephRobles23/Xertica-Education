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

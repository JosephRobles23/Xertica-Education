## Parent
None

## What to build
Build the sourcing database repository (`repositories/kb/` or similar tables) to persist candidate and approved sources (`Source` entities). Replace the sourcing mock layer with DB transactions.

## Acceptance criteria
- [x] Source entries and verification status are loaded and updated in the Supabase database.

## Blocked by
- [Issue 06 (Gate 1 Sourcing)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-06-gate-1-sourcing.md)
- [Issue 07 (Jobs Database Repository)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-07-jobs-database-repository.md)

---

## Estado — COMPLETADA (2026-07-07 · rama `feature/KB-RAG`)

Tomada por Joseph porque su KB la necesitaba (cierra el FK `kb_chunks.source_id`).
Cerrada con grilling → ADR → TDD.

**Qué se construyó**
- `SourcingRepository` (`repositories/sourcing/`): `interface` + `InMemory` + `Supabase` + factory
  + `mapping` (`route["sources"]` → `Source`).
- **UPSERT idempotente** por `unique(learning_path_id, url)` que **preserva** el estado humano.
- Persiste **todas las candidatas** con `estado` (approved/requires-review/rejected).
- Cableado en Gate 1 (`/sourcing/approve`): upsert → luego ingesta RAG de las verificadas.

**Cambio de schema (ADR-0007):** `sources` pasa a **route-céntrica** (`+learning_path_id`,
`+estado`, `−asset_id`); nueva tabla puente **`asset_sources`** (M:N). Corrige el modelo
asset-céntrico de ADR-0005.

**Decisiones:** [ADR-0007](../../adr/0007-source-route-centrica-sourcing.md) · mapa en
[docs/decisions/issue-09-source-persistence-decision-map.md](../../decisions/issue-09-source-persistence-decision-map.md).

**Verificado:** schema aplicado en Supabase Cloud + E2E real (persistencia + ingesta + query + cleanup).

**Deuda (fuera de alcance):** poblar `asset_sources` en la fase de citación (generación, Fase 5-6).

# ADR-0007: Source route-céntrica en sourcing; citación asset↔source vía tabla puente

- **Estado:** Aceptado
- **Ámbito:** `supabase/migrations/`, `apps/api/repositories/sourcing/`, `apps/api/models/domain/source.py`, `apps/api/routers/learning_paths.py` (Gate 1)
- **Issue:** [issue-09 · Sourcing database repository](../issues/pending/arantza/issue-09-sourcing-database-repository.md)
- **Relación:** **corrige el modelo asset-céntrico de `sources` de [ADR-0005](0005-full-spine-schema.md)** y **habilita la escritura real de [ADR-0006](0006-kb-rag-ingestion-embeddings.md)** (cierra el FK `kb_chunks.source_id`).

## Contexto

El **user-flow real** es route-céntrico: el deep-research escribe las fuentes en `route["sources"]` (JSON) y se aprueban como **corpus de la Ruta en Gate 1**, *antes* de que exista ningún Asset (los assets se generan en Fase 5-6). El frontend modela `sources: Source[]` a nivel **ruta** (`types.ts:159`), con un `suggestedUse` que es solo una *pista*.

El **Spine (ADR-0005)** las modeló asset-céntricas: `sources.asset_id NOT NULL` y `ASSET ||--o{ SOURCE`. Dos problemas:
1. En sourcing no hay `asset_id` al que apuntar (contradice el flujo).
2. La relación real es **muchos-a-muchos** (una fuente la citan varios assets), no 1:N.

La tabla `sources` está **vacía** (nadie persiste aún; el repo es un esqueleto). issue-09 pide persistir candidatas **y** aprobadas. Resuelto en sesión de grilling (`/grill-with-docs`).

## Decisión

1. **`sources` route-céntrica:** agregar `learning_path_id uuid not null references learning_paths(id) on delete cascade`. La fuente pertenece a la **Ruta** desde Gate 1.
2. **Quitar `sources.asset_id`** (y su índice `idx_sources_asset`). La citación asset↔source (Fase 5-6) se modela con una **tabla puente `asset_sources(asset_id, source_id)`** M:N (PK compuesta, FKs `on delete cascade`). Corrige el 1:N erróneo de ADR-0005.
3. **Persistir todas las candidatas con estado:** agregar `estado text check (estado in ('approved','requires-review','rejected'))` (vocabulario del frontend; inglés por ADR-0003). Se guardan candidatas **y** aprobadas; `verificada_google` ya existe.
4. **Idempotencia:** `unique(learning_path_id, url)`. El UPSERT (`ON CONFLICT`) refresca metadata (`title`, `tipo`, relevancia) pero **no pisa** `estado` ni `verificada_google` — preserva las decisiones humanas del Gate 1 al re-correr el deep-research.
5. **Punto de escritura único:** en `POST /learning-paths/{id}/sourcing/approve` se hace el upsert de `route["sources"]` → `sources` y **luego** corre la ingesta RAG (ADR-0006) de las verificadas. Entre deep-research y approve, las candidatas viven en el JSON de la ruta (`update_route`).
6. **Migración aditiva** en archivo nuevo: como `sources` está vacía, el `drop` de `asset_id` es seguro y no hay backfill. RLS activo sin políticas (hereda ADR-0004).

## Consecuencias

- **+** Cierra el FK `kb_chunks.source_id → sources.id`: la **escritura real** de la ingesta RAG funciona de punta a punta (ya no depende de que existan assets).
- **+** Schema alineado con el user-flow real; la relación asset↔source queda **correcta (M:N)**.
- **+** Auditable: las candidatas y las decisiones humanas del Gate 1 quedan en la DB y son re-revisables.
- **−** Toca el **Spine** (ADR-0005): `drop` de `sources.asset_id` + nueva tabla. El modelo de dominio `Source` y cualquier consumidor de `Source.asset_id` deben ajustarse (hoy nadie lo lee).
- **−** `asset_sources` se crea ahora pero **no se puebla** hasta la citación en generación (Fase 5-6) → tabla interina vacía.
- **Deuda registrada:** poblar `asset_sources` en la fase de citación queda para su propio slice; el `MockDocumentProvider` (ADR-0006) sigue hasta tener fetch/parse real.

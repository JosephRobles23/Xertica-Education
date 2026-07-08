# Decision Map — Persistencia de Sources (issue-09) · rama `feature/KB-RAG`

> Decisiones tomadas en la sesión de grilling (`/grill-with-docs`) para persistir las
> fuentes del sourcing. Todas resueltas → [[docs/adr/0007-source-route-centrica-sourcing]].
> Alcance: `supabase/migrations/`, `apps/api/repositories/sourcing/`, `models/domain/source.py`,
> `routers/learning_paths.py` (Gate 1).

## Contexto

El user-flow real es **route-céntrico** (fuentes en `route["sources"]`, aprobadas por Ruta en
Gate 1, antes de que existan assets), pero el Spine (ADR-0005) las modeló **asset-céntricas**
(`sources.asset_id NOT NULL`, relación 1:N). La tabla `sources` está vacía. Este mapa reconcilia
ambos y desbloquea la escritura real de la ingesta RAG (cierra el FK `kb_chunks.source_id`).

---

## #1: ¿Modelo de `sources` — route-céntrico o asset-céntrico?

Type: Discuss → **ADR** (corrige el Spine)

### Answer
**RESUELTO → Route-céntrico.** `sources` gana `learning_path_id` (FK a `learning_paths`); la
fuente pertenece a la Ruta desde Gate 1. El binding a un Asset se resuelve después (#2).

## #2: ¿Relación asset↔source — `asset_id` nullable o tabla puente M:N?

Blocked by: #1
Type: Discuss

### Answer
**RESUELTO → Tabla puente `asset_sources(asset_id, source_id)` M:N ahora**, y se **quita**
`sources.asset_id`. Corrige el 1:N erróneo de ADR-0005. Se puebla en la citación (Fase 5-6).

## #3: ¿Qué se persiste — todas las candidatas o solo aprobadas?

Type: Discuss

### Answer
**RESUELTO → Todas las candidatas con `estado`** (`approved` / `requires-review` / `rejected`,
vocab del frontend) + `verificada_google`. La KB ingesta filtra las verificadas. Auditable.

## #4: ¿Idempotencia ante re-runs del deep-research?

Type: Discuss

### Answer
**RESUELTO → `unique(learning_path_id, url)` + UPSERT** que refresca metadata pero **no pisa**
`estado` ni `verificada_google` (`ON CONFLICT` no toca esas columnas) — preserva las decisiones
humanas del Gate 1.

## #5: ¿En qué punto del flujo se escribe a la tabla?

Type: Discuss

### Answer
**RESUELTO → Un único punto en `POST /sourcing/approve`**: upsert de `route["sources"]` → `sources`
y luego dispara la ingesta RAG de las verificadas. Entre deep-research y approve, las candidatas
viven en el JSON de la ruta (`update_route`).

---

## Estado del mapa: **frontera resuelta.** → migración aditiva + `SupabaseSourcingRepository`
(`/tdd` + `/ponytail`). Ver ADR-0007 para el schema y las consecuencias.

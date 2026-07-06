# ADR-0004: Supabase Postgres como persistencia primaria (primera implementación)

- **Estado:** Aceptado
- **Ámbito:** `supabase/`, `apps/api/repositories/`, `apps/api/config/`
- **Relacionado:** [ADR-0001](0001-pgvector-supabase-knowledge-base.md) (pgvector/KB), [ADR-0002](0002-mocks-first-class-citizens.md) (mocks first-class)

## Contexto

Los repositorios `SupabaseJobRepository` y `SupabaseLearningPathRepository` ya están implementados y hacen CRUD contra Supabase, pero **nadie crea las tablas** (`jobs`, `learning_paths`) ni existe config real: hoy siempre caen al fallback in-memory. Esta ADR define la primera implementación que da persistencia real, respetando la regla de oro #1 del MVP (ninguna feature bloquea a otra).

Alcance deliberadamente mínimo: solo las dos tablas que los repos ya consultan. **Fuera de alcance:** KB/pgvector (ver ADR-0001, es un slice posterior), autenticación, y cualquier acceso a Supabase desde el frontend.

## Decisión

1. **Postgres de Supabase como datastore primario** para `jobs` y `learning_paths`, accedido **solo server-side** desde FastAPI.
2. **Schema versionado con el Supabase CLI** en `supabase/` en la **raíz del monorepo** (`config.toml`, `migrations/`, `seed.sql`). Coincide con el doc de arquitectura y con la matriz de ownership de `AGENTS.md` (`supabase/` es de sebas). Se aplica a cloud con `supabase db push`.
3. **Seguridad API-gateway:** el backend usa la key **`service_role`** (bypassa RLS). Se **activa RLS** en ambas tablas **sin políticas públicas** → anon/frontend no accede directamente. La key vive solo en el servidor.
4. **Vocabulario de estados como `TEXT` + `CHECK`**, alineado con la fuente de verdad (el tipo `ContentStatus` del frontend):
   - `learning_paths.estado ∈ {borrador, generado, en-revision, aprobado}`
   - `jobs.status ∈ {queued, running, rendering, completed, failed}`
   Se descartan los ENUM de Postgres (alterarlos es doloroso) y el TEXT libre (sin integridad).
5. **Patrón repositorio-con-fallback:** cada repositorio intenta Supabase y, si la URL/key son placeholders o fallan, cae a un store in-memory conforme al contrato (materializa ADR-0002 en la capa de persistencia).
6. **Config con `pydantic-settings`** (`BaseSettings` + `env_file=".env"`), como pide issue-01. Secretos en `apps/api/.env` (gitignored) con `apps/api/.env.example` commiteado.
7. **Semilla:** las 2 rutas demo viven en `supabase/seed.sql` (paridad con el fallback actual).

## Consecuencias

- El Dashboard y el CRUD de rutas persisten en Postgres real; el fallback in-memory queda como red de seguridad para desarrollo sin credenciales.
- **RLS locked + service_role** implica que introducir acceso directo del frontend (auth/realtime) en el futuro **requerirá una nueva ADR** con políticas RLS explícitas — no es una extensión trivial.
- `seed.sql` **no** se aplica con `supabase db push`; sembrar el proyecto cloud es un paso manual (SQL Editor) hasta que se automatice.
- Corrige inconsistencias de dominio detectadas: el comentario obsoleto de `estado` en `LearningPath` y el `DRAFT → PATH_READY` erróneo en `CONTEXT.md` (nunca existió en el código).
- Deja una deuda de seguridad a saldar: `apps/web/.env.local` estaba trackeado en git con la password de la DB; se desdrackea y **la password debe rotarse**.

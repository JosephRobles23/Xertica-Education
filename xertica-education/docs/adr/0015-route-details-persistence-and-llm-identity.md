# ADR-0015: Persistencia de detalles de ruta y título/tema/objetivo derivados por LLM

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Deciden:** Joseph Robles · sesión de Claude
- **Ámbito:** `supabase/migrations/20260708140000_learning_path_details.sql`, `supabase/seed.sql`, `models/domain/learning_path.py`, `repositories/learning_path/repository.py`, `services/route/service.py`, `services/route_structurer/` (`interface.py`, `service.py`, `mock.py`), `routers/learning_paths.py`, `tests/test_route_structurer.py`, frontend `modules/new-route/NuevaRuta.tsx`, `modules/routes/Dashboard.tsx`, `modules/routes/RouteDetail.tsx`
- **Relación:** **continúa** [ADR-0004](0004-supabase-postgres-persistence.md) (persistencia en Postgres) y [ADR-0014](0014-structure-generation-llm.md) (Estructura Propuesta con LLM).

## Contexto

Tras ADR-0014 la Estructura Propuesta la genera el LLM, pero la identidad de la ruta tenía tres defectos que rompían la trazabilidad y la experiencia:

1. **Detalles solo en memoria.** `RouteService` guardaba `objective`, `customerContext`, `sources`, `pack` y `modules` en un dict de proceso (`self._details`). Solo `titulo`/`tema`/`estado` se persistían. Los módulos generados por el LLM se perdían en cada restart del API, con `--reload` en dev y entre workers de uvicorn (cada uno con su propio dict).
2. **Título, tema y objetivo no reflejaban el contenido.** El frontend enviaba `titulo`/`tema` **hardcodeados** (`"Ruta de Inteligencia Avanzada"` / `"Razonamiento"`) para toda ruta, y el `objective` se guardaba como el brief literal del usuario. El `route_structurer` producía módulos pero ni nombre, tema u objetivo de la ruta.
3. **El "número" de la ruta era el UUID.** La tarjeta del dashboard y el detalle mostraban el identificador (`478508b8-…`) como número de ruta, ilegible para el usuario.

## Decisión

1. **Detalles a Postgres (JSONB · continúa ADR-0004).** Se añade la columna `details jsonb` a `learning_paths` (migración `20260708140000`, con backfill idempotente de las rutas demo 01/02). El modelo `LearningPath` gana el campo `details`; `SupabaseLearningPathRepository` lo lee/escribe en create/get/list/update; `RouteService` deja de usar `self._details` y viaja los detalles dentro de `LearningPath.details`. El JSONB es **interino**: se normalizará al spine (módulos/componentes/assets) en un slice posterior (ADR-0005).

2. **Título, tema y objetivo los sintetiza el LLM (extiende ADR-0014).** `RouteStructurerInterface.generate()` pasa a devolver `{"title", "tema", "objective", "modules"}` en vez de solo la lista de módulos. El prompt instruye al modelo a **sintetizar** (no copiar el brief literal) un nombre atractivo, una materia central y un objetivo de aprendizaje redactado — y a **respetar un título u objetivo explícitos** si el brief los indica. El Job de Gate 0 (`_run_structure_job`) persiste `title`→`learning_paths.titulo`, `tema`→`learning_paths.tema` y `objective`→`details.objective`. Hay fallbacks deterministas por si el LLM omite algún campo. El frontend envía un título provisional derivado de la primera línea del brief que el Job reemplaza al completar.

3. **Número de orden en la UI (presentación).** La tarjeta y el detalle muestran un número de orden por **posición en la lista** (`01`, `02`, …), no el `id`. El `id` (UUID) se conserva para navegación y llamadas al API. Para que el número sea estable entre recargas, `repository.list_all()` ordena por `created_at`, dejando la última ruta creada al final.

## Consecuencias

- **+** Los detalles generados por el LLM (módulos, fuentes, objetivo) sobreviven a restarts, `--reload` y múltiples workers: persistencia real de la Estructura Propuesta.
- **+** La ruta tiene identidad legible y contextual: título, tema y objetivo derivados del contenido en lugar de placeholders, y un número de orden en vez del UUID.
- **+** El brief del usuario se respeta cuando especifica un título u objetivo concretos.
- **−** Cada regeneración de estructura **sobrescribe** título/tema/objetivo con lo que produce el LLM; un rename manual del usuario no sobrevive a una regeneración (mitigable con una bandera en un slice futuro).
- **−** La numeración por posición cuenta también las 7 rutas demo (mock `01`–`07`) que el frontend fusiona, por lo que las rutas reales empiezan en `08`. Queda condicionado a la limpieza/retiro de esos mocks.
- **−** `details` como JSONB único es deuda deliberada: el shape lo define el route service y no está normalizado al spine relacional (ADR-0005).

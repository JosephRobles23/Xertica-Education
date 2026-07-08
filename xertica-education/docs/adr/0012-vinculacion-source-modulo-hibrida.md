# ADR-0012: Vinculación Source↔Módulo híbrida (heurística + LLM on-demand) con `source_module_links`

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Deciden:** Galo (contacto@soygalo.com) · sesión `/grill-with-docs`
- **Ámbito:** `routers/learning_paths.py` (endpoint `link-sources`), `repositories/sourcing/`, `adapters/llm/`, `supabase/migrations/`, frontend `routes/RouteDetail.tsx`
- **Relación:** habilita [ADR-0011](0011-kb-solo-via2-linking-por-modulo.md) (las fuentes de Vía 1 se aprovechan por vinculación, no por ingesta).

## Contexto

Si las fuentes de Vía 1 (videos de YouTube) no entran al KB ([ADR-0011](0011-kb-solo-via2-linking-por-modulo.md)), su valor es quedar **asignadas al módulo que les corresponde**. `main` ya trae una **heurística en frontend** (`findRecommendedYoutubeSource` en `RouteDetail.tsx`): puntúa cada fuente de YouTube verificado contra el texto del módulo (`name + type + summary`) y elige la mejor. Funciona, cuesta cero y ya está desplegada, pero es un match textual superficial que puede errar.

La alternativa planteada fue "un LLM en segundo plano que vincule dicho source con el módulo". Un LLM asigna con mejor criterio semántico, pero tiene costo, latencia y requiere persistencia y contrato nuevos. La pregunta es cuándo pagarlo.

## Decisión

1. **Modelo híbrido.** La **heurística** de `RouteDetail` es el **baseline** (default, client-side, cero costo). El **LLM linker** corre **on-demand**: cuando el usuario lo pide explícitamente ("Re-vincular con IA") o cuando la confianza de la heurística es baja.

2. **El LLM re-rankea el pool existente, no re-busca.** Endpoint nuevo:

   ```
   POST /learning-paths/{route_id}/link-sources   body: { module_id }
   → LLM(route.modules, route.sources) → [{ source_id, module_id, score, why }]
   ```

   Recibe los `modules` + las `sources` **ya recolectadas** y devuelve la mejor asignación. **No** dispara deep research: es barato, determinista en su entrada y siempre devuelve algo. "Buscar otro" (que sí re-busca vía `/deep-research` acotado al módulo) se mantiene como acción **separada**, tal como está hoy en `main`.

3. **El mapping se persiste** en una tabla route-céntrica:

   ```sql
   create table source_module_links (
     id uuid primary key default gen_random_uuid(),
     learning_path_id uuid not null references learning_paths(id) on delete cascade,
     source_id uuid not null references sources(id) on delete cascade,
     module_id text not null,            -- id de módulo dentro de la ruta
     score real,
     origin text not null check (origin in ('heuristic','llm')),
     created_at timestamptz default now(),
     unique (source_id, module_id)
   );
   ```

4. **Solo el linker LLM escribe filas** (`origin='llm'`). La heurística de `RouteDetail` **no** persiste: sigue siendo el fallback client-side. `RouteDetail` lee: *si existe fila persistida para (módulo), úsala; si no, computa la heurística en cliente*. El campo `origin` deja la puerta abierta a persistir también la heurística en el futuro sin cambiar el esquema.

## Consecuencias

- **+** Calidad cuando importa (LLM on-demand) sin pagar costo/latencia en cada vista ni bloquear Gate 1.
- **+** El mapping persistido evita re-correr el LLM por render y da un punto único que otros generadores (video, provenance) pueden leer server-side.
- **+** Semántica exacta de "vincular": el LLM asigna sobre lo que ya hay; la búsqueda de material nuevo queda como acción distinta y explícita.
- **−** Cambio de contrato: tabla + endpoint nuevos (CONTEXT §5 regla 2 — acordado en este ADR). Requiere adapter LLM de chat; con key placeholder cae a `MockLinker` (regla de oro 1).
- **−** Estado a mantener sincronizado: si el pool de `sources` cambia (re-run de deep research), las filas de `source_module_links` de fuentes eliminadas se limpian por el `on delete cascade`, pero un re-ranking viejo puede quedar obsoleto hasta que el usuario re-vincule.
- **−** La cita final asset↔source sigue viviendo en `asset_sources` (Fase 2); `source_module_links` es *recomendación de asignación*, no *cita*. Son tablas con propósitos distintos y no deben fusionarse.
- **Deuda / fuera de alcance:** umbral concreto de "confianza baja" que auto-dispara el LLM (se calibra en implementación); persistir también la heurística; batch-linking de todos los módulos en un solo Job.

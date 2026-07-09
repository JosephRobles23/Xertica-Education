# ADR-0015: Storyboard KB-grounded independiente del render

- **Estado:** Propuesto
- **Fecha:** 2026-07-08
- **Deciden:** sebas (Video), joseph (KB)

## Contexto

La generación de video (`POST /videos/generate`) hoy recibe un `custom_storyboard`
pre-armado en el frontend (`Storyboard.tsx:161` usa `defaultScriptBlocks`), por lo que
el scriptwriter LLM del servidor (`services/video/service.py:375
_get_or_create_storyboard`) nunca se invoca en el flujo real. Ese método además
nordea la KB: construye contexto por lecturas directas a Supabase y consulta
`sources` por `asset_id`, una columna que ADR-0007 eliminó (sources son
route-céntricas; citación vía `asset_sources` M:N).

Necesitamos que el guion/storyboard del video de cada módulo se genere **a partir
de la Knowledge Base construida por Joseph (Vía 2)**, con el humano revisando antes
del render. Esto encaja con el patrón de Gates del dominio (CONTEXT.md §3): hoy
existen Gate 0 (estructura) y Gate 1 (sourcing); el guion es el siguiente punto de
control humano antes de gastar Veo/Imagen/TTS.

Eliminar la revisión humana del guion y mandar directo a render rompería el patrón
HITL y dejaría al usuario sin poder corregir el script antes de un proceso caro.

## Decisión

1. **Nuevo endpoint `POST /videos/storyboard`** que produce un `StoryboardRequest`
   KB-grounded para el Render Target dado. Es **puro**: consulta la KB, llama al
   scriptwriter LLM, devuelve JSON. **No persiste Asset ni crea Job.**
2. **Render Target como input**: `{route_id, module_id, component_kind="video",
   component_id?}` — los tresprimeros identifican el módulo a guionizar; `component_id`
   es opt-in para cuando ya existe el Componente.
3. **Module-grounded query**: la consulta a la KB se arma con `module.titulo` y
   `module.descripcion` (+ `component.titulo` si hay) y se envía a la consulta
   route-scoped existente `KnowledgeBase.query(learning_path_id, text)`. Sin nuevo
   método en el puerto KB; sin contrato nuevo para Joseph. Se confía en el linker
   (ADR-0012) + el título descriptivo del módulo para llevar la relevancia.
4. **Output reutiliza `StoryboardRequest`** (`models/dto/requests.py:64`) para que el
   frontend (editado o no) se inyecte tal cual en `POST /videos/generate`
   (`custom_storyboard`). Cero reshaping en el cliente.
5. **Persistencia queda en `/videos/generate`**: el upsert del `assets` con el
   `provenance.storyboard` y `estado="generado"` se mantiene en el flujo de render,
   no en el de storyboard. El storyboard endpoint no muta estado.
6. **`/videos/generate` no cambia contrato** en esta decisión; ya acepta
   `custom_storyboard`. La lógica de `_get_or_create_storyboard` (auto-generación
   server-side con lecturas directas a Supabase) queda como fallback legacy y se
   marca para limpieza posterior — no se elimina en este cambio para no romper el
   path sin `custom_storyboard`.

## Consecuencias

- **Se gana:** un único consumidor limpio de la KB para video; HITL de guion previo
  a render; contrato de `/videos/generate` inalterado; Joseph no tiene que tocar su
  puerto KB.
- **Se sacrifica:** un endpoint más (DTO de request nuevo + router). El
  `_get_or_create_storyboard` queda duplicado conceptualmente con el nuevo endpoint
  hasta que se limpie.
- **Condiciona:** el frontend (`Storyboard.tsx`) debe dejar de usar
  `defaultScriptBlocks` y empezar a llamar a `/videos/storyboard` para poblar la
  UI editable. La calidad del grounding depende de que el linker (ADR-0012) haya
  persistido `source_module_links` y de que los módulos tengan `descripcion` rica.
- **ADR相关性:** refine (no contradice) ADR-0006 (KB como puerto), ADR-0007
  (sources route-céntricas → aquí consumimos los chunks ya ingestados de Vía 2) y
  ADR-0012 (linker Source↔Módulo → el guion se beneficia de su salida sin
  acoplarse). Marca como **deuda conocida** la query `sources.eq("asset_id", …)`
  en `_get_or_create_storyboard` (`service.py:468`), que es stale desde ADR-0007.
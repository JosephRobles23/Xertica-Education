# ADR-0020 — Materialización perezosa del Spine

- **Estado:** Aceptado (grill de persistencia, 2026-07-10)
- **Relacionados:** [[0005-full-spine-schema]], [[0015-route-details-persistence-and-llm-identity]], [[0006-video-asset-source-of-truth]]

## Contexto

El Spine (`Ruta → Módulo → Componente → Asset`, ADR-0005) está migrado en Supabase pero
nunca se pobló: los módulos/componentes viven en el JSON `learning_paths.details`
(interino según ADR-0015). Consecuencia observada en producción: los INSERT de `assets`
que VideoService e InfographicService ya intentan **fallan por la cadena de FKs**
(`assets → components → modules`, todas vacías) y caen en silencio al fallback
in-memory (ADR-0004). Además, los ids de módulo del JSON (`"r1m1"`) no son UUID, así
que `_resolve_video_component_id` nunca puede insertar el componente.

## Decisión

**Materialización perezosa**: nadie puebla `modules`/`components` masivamente. Cuando
un servicio necesita persistir un `Asset`, un materializador compartido
(`repositories/spine/`) crea on-demand las filas de `module` y `component` que falten,
con **UUIDs deterministas** (uuid5 sobre `route_id + module_json_id [+ kind]`) para que
regeneraciones y re-runs converjan en las mismas filas (upsert por id).

- El JSON `details` sigue siendo la fuente de verdad de la **estructura** (módulos,
  orden, contenidos propuestos).
- La tabla `assets` se vuelve la fuente de verdad de los **artefactos** (estado de
  aprobación, `storage_path`, `provenance`) — coherente con ADR-0006 (video).
- La normalización completa de `modules`/`components` (escritura en Gate 0 + migración)
  queda como slice futuro solo si aparece una necesidad de consulta SQL real.

## Consecuencias

- Los INSERT de `assets` dejan de violar FKs; el Spine se llena solo con lo que
  realmente se materializa.
- Las filas de `modules`/`components` materializadas llevan la metadata disponible al
  momento (titulo/tipo/orden del JSON); no son la fuente de verdad de la estructura.
- `asset_versions` sigue sin uso (versionado = slice futuro; la regeneración upsertea
  el mismo asset determinista).

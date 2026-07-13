# Análisis de persistencia — Xertica Education

> Auditoría del 2026-07-10. Insumo para sesión de grill sobre el gap de persistencia.
> Contexto: en el Supabase de producción, `asset_sources`, `asset_versions`, `assets`,
> `components`, `kb_chunks` y `modules` están vacías; `learning_paths`, `documents`,
> `jobs`, `sources`, `approved_research_sources` y `source_module_links` sí tienen datos.

## 1. Veredicto por tabla vacía

| Tabla | Veredicto | Causa raíz |
|---|---|---|
| `modules` | Huérfana: **cero escrituras** en el código (solo un SELECT en VideoService) | ADR-0005 (full-spine schema) se aceptó como diseño pero nunca se implementó. Los módulos viven como JSON en `learning_paths.details.modules[]` |
| `components` | Huérfana: existe un INSERT (`VideoService._resolve_video_component_id`, service.py:~1583) pero en la práctica no se ejecuta / falla en cadena | Su FK `modulo_id → modules(id)` no puede satisfacerse porque `modules` está vacía. Los componentes viven en `details.modules[].contents[]` |
| `assets` | Código de escritura real existe (VideoService ~1628, InfographicService ~405) pero los inserts **fallan silenciosamente y caen a fallback in-memory** | FK `componente_id → components(id)` rota en cadena (components vacía) + patrón try/except-fallback de ADR-0004 que traga el error. Nota: prod tiene credenciales reales (otras tablas sí escriben), así que el placeholder NO es la causa aquí |
| `asset_versions` | Nunca usada: **ninguna referencia** en el código | Tabla de versionado definida en el schema para un futuro que no llegó |
| `asset_sources` | Sin ninguna escritura en el código; las migraciones del repo solo definen `sources` (con FK `asset_id`) | Probablemente creada a mano en Supabase o en migración fuera del repo; el código usa `sources` |
| `kb_chunks` | Código de escritura real existe (`SupabaseKbChunkRepository.upsert_chunks`) y el trigger existe (`_run_kb_ingestion_job` tras Gate 1 / sourcing approve) | **Requiere diagnóstico**: la ingesta es best-effort (si falla solo marca el job `failed` sin propagar). Revisar en la tabla `jobs` los registros `type=kb_ingestion` con status failed. Sospechosos: (a) RLS activo sin políticas + uso de anon key en vez de service key, (b) fetch del contenido de la fuente falla, (c) embedder/dimensión. Con OPENROUTER_KEY placeholder el MockEmbedder genera vectores deterministas igualmente — no explica el vacío por sí solo |

### La cadena rota

```
learning_paths (✅ datos, JSON gigante en details)
   └─ modules (❌ vacía — nadie inserta)
        └─ components (❌ vacía — FK imposible + insert casi nunca invocado)
             └─ assets (❌ vacía — FK imposible; el insert existe y falla en silencio)
                  └─ asset_versions (❌ vacía — sin código)
```

El patrón repositorio-con-fallback (ADR-0004: try Supabase → except → in-memory/local,
con `print` en vez de raise) hace que **todos estos fallos sean invisibles**: la app
funciona, pero la persistencia normalizada nunca ocurre.

## 2. Dónde vive realmente la información

### a) `learning_paths.details` (JSONB) — el "monolito JSON"

Todo el spine vive aquí, actualizado vía `RouteService.update_route()`:

```json
{
  "objective": "...",
  "customerContext": {...},
  "sources": [ {título, url, verified, status, relevanceScore, videoPreview...} ],
  "modules": [
    { "id": "r1m1", "name": "...", "type": "intro", "status": "aprobado",
      "contents": [ { "kind": "lesson", "lesson": {sections, terms, pdfUrl, txtUrl}, ... } ],
      "lab": {...}, "quiz": {...} }
  ],
  "pack": { "lesson": {...}, "video": {...}, "infografia": {...}, "quiz": {...}, "lab": {...} }
}
```

Consecuencias: sin integridad referencial, sin queries por módulo/componente, updates
de ruta completa (race conditions si dos flujos actualizan `details` a la vez), y las
URLs de artefactos embebidas apuntan a `http://localhost:8000/static/...`.

### b) Filesystem del servidor (`apps/api/static/`) — artefactos generados

| Artefacto | Archivo en disco | ¿Supabase Storage? | Metadata | Riesgo |
|---|---|---|---|---|
| Lesson | `static/lessons/{route}_{mod}_lesson.{txt,pdf}` | ❌ nunca lo intenta | URLs locales en `details.modules[].lesson` | Pérdida total en deploy efímero/multi-instancia; URLs rotas fuera de localhost |
| Quiz | `static/quizzes/...{txt,pdf}` | ❌ | ídem | ídem |
| Lab | `static/labs/...{txt,pdf,json}` | ❌ | JSON completo + provenance sí queda en `details` | Archivos se pierden; el JSON en BD permite reconstruir |
| Infografía | `static/infographics/...{png,pdf}` | ✅ lo intenta (bucket `xertica-education-assets`) + insert en `assets` | En `details.pack.infografia` + `assets` (si no falla FK) | El insert a `assets` falla por FK → solo queda lo local |
| Video MP4 | `/tmp/render_{job}/` (se limpia) | ✅ `videos/{job_id}/capsule.mp4` | `jobs.result` (video_url, cost, provenance) + intento en `assets` | El mejor flujo; metadata no llega a la ruta |
| Audio TTS | `/tmp/` por escena | ❌ | solo duración en provenance | **Irrecuperable** tras el render |
| Música (Pixabay) | `/tmp/` | ❌ | referencia parcial | Irrecuperable; el render no es reproducible |
| Storyboard | — (solo respuesta HTTP) | ❌ | solo si el render completa (`assets.provenance.storyboard`) | Si el usuario edita y no renderiza, se pierde |

### c) Navegador (localStorage + React state) — estado de workflow

**Nada del workflow de revisión/aprobación se persiste en el backend:**

| Estado | Dónde vive | ¿Endpoint para persistir? |
|---|---|---|
| Aprobaciones de contenido (`aprobado/en-revision/borrador` por route:module:kind) | React state (`statusOverride`) | ❌ no existe |
| Status de módulo / progreso de ruta | Derivado del anterior | ❌ |
| Fuentes descartadas (`discardedSources`) | React state | ❌ (reaparecen al refrescar) |
| Aprobación de storyboard / lab guide / flag `isGenerated` | React state | ❌ |
| Flag corpus aprobado | React state; el POST `/sourcing/approve` sí llega al backend pero el flag **no se rehidrata** al recargar | ⚠️ parcial |
| URL del video renderizado / job ids | localStorage | ⚠️ el backend lo tiene (jobs/assets) pero no se rehidrata |
| briefText / customerContext / archivo subido en Nueva Ruta | React state; se envía al crear pero no se rehidrata | ⚠️ parcial |

Impacto: un refresh, otro navegador u otro miembro del equipo ⇒ se pierden todas las
decisiones de revisión. El campo `status` dentro de `details.modules[]` existe en BD
pero el frontend no lo escribe de vuelta — la fuente de verdad del workflow es el navegador.

## 3. Qué falta definir (agenda para el grill)

### Decisión 1 — Destino del spine normalizado (ADR-0005)
Opciones: (a) implementar la normalización `modules`/`components`/`assets` con doble
escritura y migración, (b) declarar oficialmente el JSON `details` como modelo canónico
y **eliminar del schema** las tablas muertas (y las FKs que hacen fallar los inserts de
`assets`), o (c) híbrido: normalizar solo `assets` (que ya tiene escritores) colgándolo
de `learning_path_id`+`module_id` textual en vez de la cadena de FKs rota.
*Pregunta clave: ¿alguien necesita consultar módulos/componentes por SQL, o el JSON basta para el MVP?*

### Decisión 2 — Storage de artefactos
Unificar: todo artefacto generado (lesson/quiz/lab/infografía) pasa por
`SupabaseStorageAdapter` hacia el bucket, y las URLs guardadas en `details` son de
bucket, no `localhost:8000/static`. Definir: naming (`{route}/{module}/{kind}/v{n}`),
URLs públicas vs firmadas, y si `static/` queda solo como caché local. Incluye limpiar
los artefactos ya commiteados/sueltos en `apps/api/static/` y agregarlos a `.gitignore`.

### Decisión 3 — Persistencia del workflow de revisión
Diseñar dónde viven las aprobaciones: (a) campos dentro de `details` (mínimo cambio:
el frontend ya lee `modules[].status`, solo falta un PATCH granular y rehidratación), o
(b) tabla `approvals`/columnas dedicadas si se necesita auditoría (quién aprobó, cuándo).
Endpoints faltantes: aprobar/refinar contenido, descartar fuente, aprobar storyboard/lab,
marcar ruta generada — todos con rehidratación en `fetchRoutes()`.

### Decisión 4 — Diagnóstico kb_chunks (RAG)
Antes de decidir nada: consultar `jobs` por `type=kb_ingestion` fallidos y validar qué
key usa el backend (service_role vs anon — RLS está activo sin políticas en `kb_chunks`).
Definir además si la ingesta debe ser reintentable/visible en la UI en vez de best-effort silencioso.

### Decisión 5 — Storyboard y assets de video
Persistir el storyboard al generarse/editarse (no solo al renderizar), y decidir si el
`video_url` final debe escribirse también en `details` para que la ruta sea autosuficiente.

### Decisión 6 — Observabilidad de los fallbacks
El patrón ADR-0004 (fallback silencioso) fue correcto para el MVP offline, pero hoy
oculta fallos de persistencia en producción. Definir: logging estructurado + métrica o
al menos un flag `persisted: false` en las respuestas cuando se cayó al fallback.

## 4. Referencias de código

- Schema: `supabase/migrations/20260706120000_init_schema.sql`, `20260707120000_kb_chunks.sql`, `20260708140000_learning_path_details.sql`
- JSON de ruta: `apps/api/repositories/learning_path/repository.py`, `services/route/service.py`
- Inserts a `assets`: `apps/api/services/video/service.py` (~1628), `services/infographic/service.py` (~405)
- Ingesta KB: `apps/api/routers/learning_paths.py` (`_run_kb_ingestion_job`), `services/kb/ingestion.py`, `repositories/kb/__init__.py`
- Storage adapter: `apps/api/adapters/storage/supabase.py` (bucket `xertica-education-assets`)
- Estado frontend: `apps/web/src/shared/store/index.tsx` (localStorage keys ~218-223, statusOverride ~264, corpusApproved ~265, discarded ~266)
- Serving local: `apps/api/main.py` (`app.mount("/static", ...)`)

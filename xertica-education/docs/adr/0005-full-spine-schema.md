# ADR-0005: Schema del Spine completo desde el día 1

- **Estado:** Aceptado
- **Ámbito:** `supabase/migrations/`, `apps/api/models/domain/`
- **Relación:** **amplía y corrige el punto 4 de [ADR-0004](0004-supabase-postgres-persistence.md)** (que solo creaba `learning_paths` + `jobs`).
- **Fuente:** `Documents/Architecture/xertica-education-arquitectura.md` §3 (el *Spine*).

## Contexto

ADR-0004 acotó la primera migración a las dos tablas que los repos ya consultan (`learning_paths`, `jobs`). Al contrastar con el documento de arquitectura objetivo surgió que:

1. El doc pide el **Spine completo desde el día 1** (§3, ADR-9, §12): es barato y **desbloquea a los 4 devs en paralelo**. Faltaban `modules`, `components`, `assets`, `sources`, `asset_versions`.
2. Los **modelos de dominio del código ya reflejan el Spine** (`Asset`, `Component`, `Source` en `models/domain/`), pero sin tablas.
3. Existía un **conflicto de `estado`** en tres vocabularios: `RUTA` en el doc es ciclo de vida (`borrador/en_produccion/publicada`); `ASSET` es aprobación (`draft/generado/en_revision/aprobado`); el código real usa el vocab de aprobación **sobre la Ruta** (`route.status = ContentStatus`, con `en-revision` guion medio).

## Decisión

1. **Implementar las 6 tablas del Spine** en la migración inicial: `learning_paths` (Ruta), `modules`, `components`, `assets`, `sources`, `asset_versions`, más `jobs` (infra, fuera del Spine). Todas con **RLS activo sin políticas** (hereda ADR-0004).
2. **Enums como `TEXT` + `CHECK`** con el vocabulario del doc:
   - `modules.tipo ∈ {intro, capsula, lab, evaluacion, cierre}`
   - `components.tipo` / `assets.tipo ∈ {lesson, video, lab, infografia, quiz}`
   - `assets.estado ∈ {draft, generado, en_revision, aprobado}` (aprobación · guion **bajo**, como el modelo `Asset`)
   - `sources.tipo ∈ {youtube, google_docs, blog_oficial, soporte_google}`
3. **`learning_paths.estado` se mantiene INTERINO** con el vocab que el código usa hoy (`borrador, generado, en-revision, aprobado`). **No** se cambia a ciclo de vida todavía porque el `route service` lo escribe y el frontend lo lee como `ContentStatus`: hacerlo ahora rompería la app (contrato de API + UI). Queda como deuda explícita.
4. **FKs con `on delete cascade`** siguiendo la jerarquía del árbol (Ruta → Modulo → Componente → Asset → {Source, AssetVersion}).

## Consecuencias

- Los 4 devs pueden construir contra el Spine en paralelo desde el día 1, como pide el doc.
- El schema queda **por delante** del código que corre (routers/repos/frontend solo tocan `learning_paths` + `jobs`); las tablas nuevas son aditivas y nadie las escribe aún → cero riesgo para la app actual.
- **Deuda registrada:** `learning_paths.estado` seguirá siendo aprobación-sobre-la-Ruta hasta un slice que **desacople el ciclo de vida de la Ruta del `ContentStatus`** (separar `RouteStatus` en el frontend, actualizar `route service` + boot test). Ese cambio toca el contrato de API → requiere su propio ADR.
- Los modelos de dominio se alinean al schema (`Module`, `AssetVersion` nuevos; `LearningPath.storytelling`, `Component.tema`, `Source.asset_id/verificada_google`).

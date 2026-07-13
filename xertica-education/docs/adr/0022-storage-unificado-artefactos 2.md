# ADR-0022 — Storage unificado de artefactos generados

- **Estado:** Aceptado (grill de persistencia, 2026-07-10)
- **Relacionados:** [[0020-materializacion-perezosa-spine]], [[0016-video-render-artifact-retention]]

## Contexto

Cada tipo de contenido persistía distinto: video subía al bucket ✅, infografía lo
intentaba con fallback ⚠️, y lesson/quiz/lab escribían **solo** a `apps/api/static/`
con URLs `http://localhost:8000/static/...` guardadas en el JSON de la ruta — muertas
en cualquier deploy efímero o multi-instancia. Además había artefactos generados
commiteados en el repo.

## Decisión

1. **Todo artefacto generado pasa por `SupabaseStorageAdapter`** hacia el bucket
   `xertica-education-assets`; el filesystem local queda solo como fallback de
   desarrollo (patrón ADR-0004).
2. Convención de path alineada al Spine: `{route_id}/{module_id}/{kind}/{filename}`.
3. El `Asset.storage_path` guarda el **path del bucket** (no la URL completa); la URL
   se construye al servir.
4. **URLs públicas** del bucket para el MVP (no firmadas): la app aún no tiene auth de
   usuarios, así que firmar no protegería nada adicional. Cuando llegue identidad, el
   cambio a URLs firmadas se hace en un solo lugar (el adapter).
5. Higiene: `apps/api/static/{lessons,quizzes,labs,infographics,videos}/` entra al
   `.gitignore` y los artefactos ya commiteados salen del repo.

## Consecuencias

- Los artefactos sobreviven reinicios/deploys; las URLs del JSON dejan de apuntar a
  localhost cuando hay credenciales reales.
- Los buckets acumulan versiones bajo el mismo path (upsert); el versionado real
  (`asset_versions`) sigue siendo slice futuro.
- La infografía conserva su convención de path previa (`infographics/{component_id}_…`)
  para no romper URLs existentes; los tipos nuevos usan la convención del punto 2.

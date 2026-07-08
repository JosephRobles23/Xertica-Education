# ADR-0006: Video renderizado como Asset persistido

- **Estado:** Aceptado
- **Fecha:** 2026-07-07
- **Deciden:** Producto + Video Production

## Contexto

El flujo de video puede iniciar un render desde `/ruta/:id/video-storyboard`, abandonar la pantalla, volver luego y esperar ver el MP4 final. Durante el MVP aparecieron tres lugares capaces de recordar parte de ese flujo:

1. `jobs` registra progreso y resultado de trabajos asíncronos.
2. `assets` representa el artefacto materializado de un componente del Spine.
3. El navegador puede cachear `job_id` y `video_url` en estado local para mejorar la experiencia al navegar.

Usar el navegador como fuente de verdad hace que un video terminado pueda "desaparecer" después de refrescar, cambiar de navegador o reiniciar el backend. Usar solo `jobs` tampoco expresa el dominio: un job es el proceso; el video final es un Asset.

## Decisión

El video final de un componente `video` se considera un **Video Asset Renderizado**. Su fuente de verdad es el registro `assets` persistido en Supabase, con `tipo = video`, `storage_path` apuntando al MP4 final, `estado` de aprobación y `provenance` del storyboard/render.

Cuando el frontend dispare un render desde el storyboard, debe enviar un **Render Target** (`route_id`, `module_id`, `component_kind`) además del storyboard. El backend usa ese target para resolver o crear el Componente/Asset persistido. `component_id` sigue siendo válido cuando el caller ya conoce el ID persistido.

El navegador puede guardar `job_id` y `video_url` solo como caché temporal para reanudar polling y mostrar progreso. Esa caché no decide si el video existe.

## Consecuencias

- Al completar `/videos/jobs/{job_id}`, el backend debe escribir o actualizar el Asset de video asociado al componente/ruta.
- La pantalla de ruta y la pantalla de revisión final deben leer el video desde el Asset persistido, no desde placeholders ni solamente desde `localStorage`.
- El contrato de `/videos/generate` admite dos identidades: `component_id` para renders ya ligados al Spine, o `route_id` + `module_id` + `component_kind` para que el backend resuelva el Spine.
- `jobs` conserva el estado operativo del render, pero deja de ser el lugar canónico para descubrir el video terminado.
- El sistema gana durabilidad entre reinicios del backend y sesiones de navegador.
- El MVP puede seguir usando caché local para una experiencia más fluida mientras el contrato de lectura/escritura de Asset se completa.
- Queda como deuda integrar explícitamente `component_id`/ruta/módulo en la llamada de render cuando el frontend aún dispara videos con `component_id = null`.

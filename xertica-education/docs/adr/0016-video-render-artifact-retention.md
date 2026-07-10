# ADR-0016: Retencion de artefactos de render de video

- **Estado:** Aceptado
- **Fecha:** 2026-07-09
- **Deciden:** Producto + Video Production

## Contexto

El pipeline de Video de Explicacion Conceptual produce varios artefactos intermedios: audios TTS por escena, capturas Playwright, imagenes generadas, clips Veo, `edit_decisions.json`, copias en el directorio publico de Remotion y el MP4 final.

El despliegue objetivo es Cloud Run con Supabase Storage. Guardar todos los artefactos intermedios por default aumenta almacenamiento, transferencia y superficie operacional. A la vez, esos archivos son utiles para depurar renders fallidos y reproducir problemas visuales.

## Decision

Persistir por default solo:

- MP4 final del Video Asset Renderizado.
- Storyboard usado para renderizar.
- Configuracion/provenance ligera del render.
- Citas o identificadores de Grounding.
- Thumbnail/poster si el producto lo necesita.

No persistir por default:

- Audios TTS por escena.
- Capturas Playwright temporales.
- PNGs temporales de Imagen.
- Clips temporales de Veo.
- Copias internas de props/assets para Remotion.

Los intermedios pueden conservarse en modo debug o diagnostico de jobs fallidos, con retencion corta y explicita.

Los renders generados usan por default **720p H.264 MP4** durante el MVP. La configuracion de render se guarda en la provenance ligera. Renders 1080p o de mayor calidad se reservan para un modo explicito de publicacion o alta calidad, una vez que el perfil de costo, latencia y transferencia este medido.

## Consecuencias

**Positivo:**

- Menor costo y complejidad en Supabase Storage.
- Menos transferencia desde/hacia Cloud Run.
- Fuente de verdad clara: el Asset final y su provenance ligera.
- Iteracion mas rapida durante revision de Storyboard y video.

**Negativo:**

- Debugging menos inmediato para renders exitosos.
- Reproducir exactamente una falla puede requerir re-render o activar modo debug.
- Si un proveedor externo no es determinista, algunos intermedios no se podran reconstruir identicamente.
- 720p puede no ser suficiente para piezas finales de publicacion o pantallas grandes; esos casos requieren un render explicito de mayor calidad.

## Referencias

- `CONTEXT.md` — Video Asset Renderizado, Storyboard, Render Plan.
- ADR-0006 Video — Video renderizado como Asset persistido.
- ADR-0007 Video — Render Plan declarativo.
- ADR-0008 Video — Remotion como Composition Engine.

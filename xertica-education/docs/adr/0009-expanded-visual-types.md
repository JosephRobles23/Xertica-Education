# ADR-0009: Vocabulario expandido de Tipos Visuales

- **Estado:** Aceptado
- **Fecha:** 2026-07-07
- **Deciden:** Video Production (sebas)

## Contexto

El pipeline de video actual define 5 tipos visuales (`slide`, `animated_slide`, `walkthrough`, `ai_video`, `ai_illustration`). Este vocabulario fue diseñado para el motor de composición anterior (Playwright + FFmpeg + Imagen + Veo) y fuerza a cada video educativo a seguir la misma plantilla de 5 bloques. El resultado es que los videos se sienten genéricos y poco impresionantes.

Al migrar a Remotion como motor de composición (ADR-0008), el nuevo motor expone 16 tipos de escena nativos (text_card, stat_card, bar_chart, comparison, etc.) que pueden producir videos visualmente variados y de alta calidad.

## Decisión

Expandir el vocabulario de `visual_type` de 5 a 14 tipos, alineados con los tipos de escena de Remotion:

**Tipos nativos de Remotion (12):**
- `text_card` — texto grande con animación spring (reemplaza `slide` + `animated_slide`)
- `hero_title` — título con animación por caracter para intros
- `stat_card` — número grande con subtítulo (ej. "8.1B personas")
- `callout` — mensaje encuadrado (info/warning/tip/quote)
- `comparison` — comparación lado a lado ("antes vs después")
- `bar_chart` — gráfico de barras animado
- `line_chart` — gráfico de líneas animado (tendencias)
- `pie_chart` — gráfico de torta/donut (proporciones)
- `kpi_grid` — cuadrícula de 2-4 KPIs (dashboard)
- `progress_bar` — barra de progreso animada (flujos de proceso)
- `terminal_scene` — terminal falsa con animación de tipeo (reemplaza `walkthrough` para CLI)
- `screenshot_scene` — UI sintética con cursor/clic/tipeo (reemplaza `walkthrough` para web)

**Tipos basados en assets (2):**
- `ai_video` — clip de Veo 3.1 reproducido directamente (se mantiene)
- `ai_illustration` — ilustración de Imagen 3 con Ken Burns/parallax (se mantiene)

**Tipos retirados:**
- `slide` → reemplazado por `text_card`
- `animated_slide` → reemplazado por `text_card` (las animaciones spring son nativas de Remotion)
- `walkthrough` → reemplazado por `screenshot_scene` (web) o `terminal_scene` (CLI)

El campo `visual_type` pasa de `str` sin validación a un `Literal` con los 14 valores (o enum). El `visual_config` se tipa por tipo visual con modelos Pydantic específicos, no un `dict` genérico.

## Consecuencias

**Positivo:**
- Videos educativos visualmente variados (stats get stat cards, comparisons get comparison cards, etc.).
- El LLM scriptwriter puede elegir el tipo visual más apropiado para cada escena, no forzar una plantilla de 5 bloques.
- Videos más cercanos al estilo Johnny Harris / 3Blue1Brown.

**Negativo:**
- Cambio en el contrato de API: `VideoScene.visual_type` agora acepta 14 valores en vez de 5.
- El frontend `Storyboard.tsx` debe actualizar su tipo `ScriptBlock.visualType` para incluir los 14 valores.
- El LLM scriptwriter necesita un prompt actualizado que enseñe los 14 tipos (trabajo de ingeniería de prompts).
- El `visual_config` actual es un `dict` genérico — hay que migrar a modelos tipados por tipo visual.

**Condicionado a:**
- ADR-0008 (Remotion Composition Engine) — los tipos se mapean a los escenarios de Remotion.
- ADR-0007 (Declarative Render Plan) — la transformación de storyboard a `edit_decisions` usa los tipos expandidos.
- La migración del frontend a tipo-ware (selector de tipo visual) queda como fase futura; el MVP usa transformación backend-only (el LLM elige, el usuario solo edita texto).

## Referencias

- OpenMontage `remotion-composer/SCENE_TYPES.md` — documentación de los 16 tipos de escena
- OpenMontage `remotion-composer/src/Explainer.tsx` — SceneRenderer que despacha por tipo
- `apps/api/models/dto/requests.py` — modelo actual de `VideoScene.visual_type`

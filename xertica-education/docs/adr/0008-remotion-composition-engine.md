# ADR-0008: Remotion como Composition Engine

- **Estado:** Aceptado
- **Fecha:** 2026-07-07
- **Deciden:** Video Production (sebas)

## Contexto

El pipeline actual compone videos con FFmpeg: Ken Burns sobre imágenes estáticas, crossfades entre escenas, mezcla de audio con `amix` y volumen fijo a 8%. Este enfoque produce resultados débiles (bugs en el cálculo de offset de crossfade, animaciones genéricas, sin subtítulos). El equipo evaluó tres alternativas:

1. **FFmpeg puro** — mantener y arreglar el código actual. Sigue sin dar animaciones de calidad profesional.
2. **HyperFrames** — motor de composición HTML/CSS/GSAP vía `npx hyperframes`. Bueno para motion graphics, pero no tiene subtítulos word-level ni componentes de chart/datos preconstruidos.
3. **Remotion** — motor de composición React vía `npx remotion render`. 16 tipos de escena preconstruidos, animaciones spring, subtítulos word-level, audio nativo con curvas de fade, sistema de temas.

El pipeline educativo de Xertica necesita charts, stats, comparaciones, subtítulos y animaciones suaves — el caso de uso primario de Remotion.

## Decisión

Usar **Remotion** como motor de composición de video, específicamente la composición `Explainer` del proyecto `remotion-composer/` de OpenMontage. El pipeline invoca Remotion como subproceso:

```
npx remotion render src/index.tsx Explainer output.mp4 --props edit_decisions.json --codec h264
```

No hay fallback a FFmpeg para composición. Si Remotion falla, el Job falla con un error estructurado. El `render_runtime` queda fijado en `"remotion"` a nivel de `edit_decisions` y no se cambia en tiempo de ejecución.

**Justificación contra HyperFrames:**
- HyperFrames no tiene subtítulos word-level (Remotion sí con `CaptionOverlay`).
- HyperFrames no tiene componentes de chart/stat/comparison preconstruidos (Remotion tiene 16).
- El contenido educativo es data-driven (charts, stats, texto estructurado) — el caso fuerte de Remotion.
- HyperFrames es mejor para kinetic typography y product promos, que no son nuestro dominio.

## Consecuencias

**Positivo:**
- Videos con animaciones spring profesionales (no CSS hacks ni FFmpeg Ken Burns).
- Subtítulos word-level con highlighting (TikTok-style) sin procesamiento extra.
- Audio nativo con curvas de fade (narración + música) sin FFmpeg `amix`.
- 16 tipos de escena listos para usar (text_card, stat_card, bar_chart, etc.).
- Sistema de temas (colores, fuentes, físicas de spring) consistente entre videos.

**Negativo:**
- Dependencia de Node.js 18+ en el servidor de producción.
- Tiempo de render ~2-5x comparado con FFmpeg puro (Remotion renderiza frame a frame con headless Chrome).
- Los assets deben copiarse al directorio `public/` de Remotion antes del render.

**Condicionado a:**
- ADR-0009 (Expanded Visual Types) — los 14 tipos visuales se mapean a los escenarios de Remotion.
- ADR-0007 (Declarative Render Plan) — la etapa de composición es una etapa del plan, no el plan completo.

## Referencias

- [Remotion Docs](https://www.remotion.dev/)
- OpenMontage `remotion-composer/` — composición Explainer, SceneRenderer, CaptionOverlay
- OpenMontage `skills/core/hyperframes.md` — matriz de decisión Remotion vs HyperFrames
- Johnny Harris / 3Blue1Brown — estilo visual aspiracional para contenido educativo

# ADR-0017: Estrategia de calidad para Videos de Explicacion Conceptual

- **Estado:** Aceptado
- **Fecha:** 2026-07-09
- **Deciden:** Producto + Video Production

## Contexto

El pipeline de video mejoro tecnicamente con Remotion, tipos visuales expandidos, TTS y render asincrono, pero el producto final seguia fallando como experiencia educativa. Los videos tendian a abrir con una metafora generica de Veo, usar imagenes estaticas o graficos sin funcion didactica, y mostrar capturas web poco especificas. El resultado era visualmente variado pero no necesariamente instructivo.

El objetivo del componente `video` no es producir una secuencia decorativa, sino un Video de Explicacion Conceptual que ensene un concepto del Modulo usando el Objetivo Pedagogico del Modulo y Grounding de la KB cuando exista.

## Decision

Adoptar una estrategia de calidad basada en ensenanza explicita antes que variedad visual:

1. Un Video de Explicacion Conceptual dura por default ~90-120 segundos y contiene 5-7 escenas fuertes, no una cuota fija de 8-12 cambios visuales.
2. El Objetivo Pedagogico del Modulo es la columna vertebral del Storyboard; la KB aporta evidencia, ejemplos y vocabulario permitido.
3. Cada escena debe tener una Intencion Pedagogica de Escena: que ensena, por que ese Tipo Visual sirve y que detalle del Modulo o Grounding la respalda.
4. El generador debe pensar primero en Patrones Didacticos y luego mapearlos a Tipos Visuales de Remotion.
5. La Paleta Visual MVP prioriza `comparison`, `progress_bar`, `callout`, `text_card`, `terminal_scene` y `screenshot_scene`.
6. `ai_video`/Veo deja de ser obligatorio; se permite como maximo una vez y solo cuando una metafora visual ayude a entender el concepto.
7. `ai_illustration` se reserva para modelos mentales o arquitectura concreta, no como imagen estatica generica.
8. Los graficos cuantitativos (`stat_card`, `bar_chart`, `line_chart`, `pie_chart`, `kpi_grid`) requieren valores evidenciados o marcados explicitamente como ilustrativos.
9. `screenshot_scene` requiere un Walkthrough Didactico: URL especifica, proposito, pasos ordenados de UI y resultado de aprendizaje.
10. Si la KB no devuelve Grounding util, el sistema puede generar un Storyboard Module-grounded, pero debe distinguirlo de un Storyboard KB-grounded y no fingir citas.
11. La Revisión de Storyboard debe exponer suficiente informacion para corregir malas decisiones antes del render: teaching point, Tipo Visual, narracion y razon visual.
12. El render debe ser predecible: una vez aprobado el Storyboard, el Render Executor materializa lo aprobado con la menor invencion posible.

## Consecuencias

**Positivo:**

- Los videos se evaluan por aprendizaje, no por cantidad de widgets.
- El gasto de Veo/Imagen/TTS ocurre despues de una revision humana mas informada.
- Remotion se usa como una caja de herramientas pedagogica, no como variedad decorativa.
- El sistema puede funcionar honestamente tanto con KB fuerte como con fallback Module-grounded.

**Negativo:**

- El contrato interno del Storyboard probablemente necesita campos nuevos como `teaching_pattern`, `pedagogical_intent`, `visual_rationale` y `grounding_status`.
- La UI de Revisión de Storyboard debe volverse mas rica que un editor de narracion.
- Los prompts del scriptwriter requieren reglas mas estrictas y validacion para evitar recaer en visuales genericos.
- Algunos videos tendran menos escenas que antes, lo que exige que cada escena tenga mejor composicion y proposito.

## Referencias

- `CONTEXT.md` — Video de Explicacion Conceptual, Escena Explicativa, Patron Didactico, Revisión de Storyboard, Render Predecible.
- ADR-0008 Video — Remotion como Composition Engine.
- ADR-0009 Video — Vocabulario expandido de Tipos Visuales.
- ADR-0012 Video — Pacing y densidad visual de guion; esta ADR refina la regla de 8-12 escenas hacia 5-7 escenas fuertes.
- ADR-0015 Video — Storyboard KB-grounded independiente del render.
- ADR-0016 Video — Retencion de artefactos y calidad default de render.

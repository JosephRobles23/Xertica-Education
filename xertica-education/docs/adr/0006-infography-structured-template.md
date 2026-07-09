# ADR-0006: Infografía por Plantilla + Datos Estructurados (Obsoleto)

- **Estado:** Supersedido por [ADR-0007](0007-infographics-ai-generation-pivot.md)
- **Fecha:** 2026-07-03
- **Deciden:** Santiago, Equipo de Desarrollo

## Contexto

El diseño inicial de infografías planteaba recibir datos estructurados desde el LLM en formato JSON y renderizarlos usando plantillas HTML + CSS estáticas, para luego compilarlas a PDF mediante un motor de renderizado (weasyprint o headless Chromium/playwright).

## Decisión

Se decidió utilizar Jinja2 para las plantillas e inyectar los datos estructurados en un diseño fijo, con validación de conteo de palabras para el `word_budget`.

## Consecuencias

- **Ventajas:** Control absoluto del layout, tipografías nítidas y logotipos fieles.
- **Desventajas:** Alta complejidad en dependencias del sistema (Pango, Cairo o Chromium) para convertir HTML a PDF en entornos Windows/Linux de forma consistente.

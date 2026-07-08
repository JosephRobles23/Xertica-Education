# ADR-0007: Infografías Generadas Directamente por IA (gpt-image-2)

- **Estado:** Aceptado
- **Fecha:** 2026-07-07
- **Deciden:** Santiago, Equipo de Desarrollo, Cliente

## Contexto

El enfoque anterior de plantillas fijas en HTML/CSS requería dependencias nativas complejas en el sistema servidor (como Pango/Cairo para WeasyPrint o Chromium para Playwright) para la compilación a PDF. Además, limitaba la variabilidad de diseño del MVP de Xertica Education.

Se busca simplificar drásticamente el pipeline y aprovechar el potencial del modelo `gpt-image-2` de OpenAI para la generación creativa y la adopción de branding por inferencia en base al prompt.

## Decisión

Se decide pivotar la arquitectura de generación de infografías:
1. El contenido del curso ya generado (sources) se sintetiza bajo un límite de palabras (`word_budget`).
2. Se construye un prompt rico en estilo, colores de marca, indicación de logotipo y contenido.
3. Se invoca directamente a la API de OpenAI Images con el modelo `gpt-image-2` para obtener la infografía en formato **PNG**.
4. La imagen PNG se envuelve en un archivo **PDF** de una página usando la librería `Pillow` (PIL), sin pasar por ningún renderizador HTML/CSS.
5. Se almacena tanto el PNG como el PDF en el storage y se registra el asset con su respectiva metadata y procedencia (provenance).

## Consecuencias

- **Ventajas:**
  - Reducción masiva en la complejidad de dependencias locales (no se requiere weasyprint ni playwright).
  - Mayor dinamismo y creatividad visual en el resultado final, adaptándose automáticamente a marcas reconocidas por nombre (Google, Meta, etc.).
- **Desventajas/Riesgos:**
  - Pérdida de control determinístico exacto sobre el layout de la infografía.
  - La API de imágenes de OpenAI puede rechazar prompts debido a políticas sobre marcas y logotipos de terceros (se implementará un mecanismo de fallback automático que intente sin logotipos explícitos).
  - Incertidumbre sobre la fidelidad exacta del texto renderizado dentro de la imagen.

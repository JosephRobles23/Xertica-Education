# ADR-0012: Pacing de Guion e Incremento de Escenas para Ritmo Dinámico

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Deciden:** Video Production (sebas, assistant)

## Contexto

En la versión inicial del pipeline de video, el guion generado por la IA estaba restringido a 4-6 escenas para una duración total de ~2 minutos (~300 palabras). Esto causaba que cada escena durara entre 16 y 25 segundos en pantalla con un solo visual estático (una ilustración, un título o una tarjeta de texto), provocando monotonía y pérdida de atención.

Para que los videos del MVP se sientan dinámicos e instructivos, el pacing visual debe acoplarse con la complejidad de lo que se expone, evitando que una imagen estática o título se muestre durante todo un bloque largo de narración.

## Decisión

Modificar las directrices del guionista de IA (`SCRIPTWRITER_SYSTEM_PROMPT`) para aplicar un pacing dinámico basado en el tipo visual:

1. **Incrementar la granularidad:** Forzar un límite de **8 a 12 escenas** por video (en vez de 4 a 6). Esto obliga a que haya un corte o cambio visual en promedio cada 8–12 segundos.
2. **Pacing adaptativo por tipo visual:**
   - **Visuales simples (`hero_title`, `text_card` de título):** Límite estricto de narración a 1 frase corta (menos de 8 palabras, ~3 segundos).
   - **Visuales intermedios (`stat_card`, `callout`, `comparison`):** Límite de 1-2 oraciones cortas (12 a 20 palabras, ~5-8 segundos).
   - **Visuales detallados/datos (`bar_chart`, `progress_bar`, `terminal_scene`, `screenshot_scene`):** Permitir narraciones de 2-3 oraciones (20 a 35 palabras, ~8-15 segundos) para dar tiempo a asimilar la información y ver las animaciones en acción.
3. **Deconstrucción de diagramas:** Evitar ilustraciones generales estáticas de larga duración. Requerir que los diagramas conceptuales se expliquen de forma progresiva a través de múltiples escenas consecutivas.

## Consecuencias

**Positivo:**
- Incremento drástico en el ritmo y dinamismo del video (cambios visuales continuos).
- Reducción del tiempo en pantalla para títulos de sección (2-3s en lugar de 16s).
- Sincronización natural entre el tiempo de visualización requerido y la extensión del discurso.

**Negativo:**
- Mayor consumo de tokens y llamadas API debido a la cantidad de escenas (8-12 en lugar de 4-6).
- El TTS generará más archivos de audio individuales por escena (aunque se combinan automáticamente en el backend).

## Referencias

- `apps/api/services/video/service.py` — Prompt del scriptwriter modificado con reglas de pacing.

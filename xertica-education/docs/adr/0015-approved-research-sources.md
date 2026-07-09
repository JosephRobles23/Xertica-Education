# ADR-0015: URLs aprobadas de Deep Research fuera de la KB

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Ámbito:** Deep Research, generación de contenido y revisión de módulos
- **Revisa:** ADR-0011 de Deep Research y aclara ADR-0011 de KB solo-Vía-2

## Contexto

Deep Research produce documentación web y videos. Las URLs documentales seleccionadas
no necesitan recuperación semántica para volver a encontrarse: el agente de generación
puede consumirlas directamente. Los uploads del cliente sí se benefician de RAG.

## Decisión

1. Gemini 2.5 Flash en Vertex AI usa Google Search Grounding para buscar documentación
   por tecnología detectada.
2. Un allowlist extensible clasifica documentación verificada y no verificada.
3. La documentación verificada se guarda automáticamente en
   `approved_research_sources`.
4. La documentación no verificada se muestra como Suggested Source y solo entra a esa
   tabla tras aprobación humana.
5. El agente de generación lee esta tabla por Ruta y Módulo, descarga cada URL y construye
   contexto directo. No usa búsqueda vectorial para localizar estas fuentes.
6. YouTube nunca entra a `approved_research_sources` ni a la KB; permanece como
   recomendación del Video Asset.
7. La KB continúa reservada para documentos subidos (Vía 2) y material que requiere RAG.

## Consecuencias

- Existe una fuente de verdad determinista para toda URL autorizada para generación.
- La aprobación automática y manual convergen en el mismo contrato.
- Las URLs no duplican contenido en `kb_chunks`.
- Las sugerencias de Google Search Grounding se conservan en `metadata` para cumplir
  requisitos de atribución y visualización.

# ADR-0017: Politica de revision de fuentes de Deep Research

- **Estado:** Aceptado
- **Fecha:** 2026-07-09
- **Ambito:** Deep Research, aprobacion de fuentes y generacion de contenido
- **Revisa:** ADR-0016 de URLs aprobadas de Deep Research

## Contexto

Deep Research puede producir muchas fuentes documentales para una ruta. Si todas las
fuentes no verificadas quedan visibles para revision humana, la UI se vuelve una lista
larga y repetitiva. Ademas, aprobar una fuente no debe hacer que aparezca otra candidata
en su lugar, porque eso convierte la revision en una cola aparentemente infinita.

La aprobacion de fuentes documentales alimenta `approved_research_sources`, que es leida
por el agente de generacion. Esa aprobacion debe ser de la ruta completa, no de un modulo
especifico.

## Decision

1. Las fuentes documentales verificadas se aprueban automaticamente y entran a
   `approved_research_sources` sin limite de cantidad.
2. Las fuentes documentales no verificadas con `relevanceScore > 90` tambien se
   auto-aprueban y se guardan en `approved_research_sources`.
3. Las fuentes documentales no verificadas con `relevanceScore < 70` se descartan para
   revision.
4. Las fuentes documentales no verificadas con `70 <= relevanceScore <= 90` forman la
   cola de revision humana.
5. La UI muestra una tanda fija de maximo 5 fuentes de revision humana por ruta. Aprobar
   o rechazar una fuente no agrega otra candidata a la tanda visible.
6. La aprobacion manual se guarda con `module_id = null`, porque la fuente aprobada queda
   autorizada para toda la ruta.
7. YouTube permanece fuera de esta politica documental y se gestiona en el flujo de Video
   Asset.

## Consecuencias

- La revision humana queda acotada y terminable.
- Las fuentes de alta confianza llegan al agente de generacion sin friccion manual.
- Las fuentes aprobadas tienen semantica route-level, evitando duplicacion por modulo.
- Rutas generadas antes de esta decision pueden tener mas fuentes pendientes en
  `route.sources`, pero el frontend debe presentar solo una tanda fija de revision.
- Cambiar los umbrales o el tamano de tanda requiere actualizar esta decision o crear un
  ADR supersesor.

# ADR-0023 — Gate 1 advierte sin bloquear; grounding visible por contenido

- **Estado:** Aceptado (grill de persistencia, 2026-07-10)
- **Relacionados:** [[0011-kb-solo-via2-linking-por-modulo]], [[0015-storyboard-kb-grounded-endpoint]]

## Contexto

Por ADR-0011 solo los documentos Vía 2 alimentan la KB. Una ruta sin uploads siempre
tendrá RAG vacío y hoy eso es invisible: el Gate 1 aprueba, la ingesta termina
"completed" con 0 chunks (job.result NULL), y lecciones/quizzes/labs se generan sin
grounding sin que el diseñador instruccional lo sepa.

## Decisión

1. **El Gate 1 nunca bloquea** (regla de oro #1: una ruta solo-Vía-1 es legítima).
2. El backend ya persiste el `IngestReport` en `job.result` y marca `failed` una
   ingesta de 0 chunks con causa diagnóstica (fix previo). El frontend **hace polling
   del `ingestionJobId`** que devuelve `sourcing/approve` y muestra el resultado:
   éxito → "KB lista: N chunks de M documentos"; corpus vacío → warning honesto.
3. **Grounding visible donde se consume**: los servicios de lesson/quiz/lab exponen
   `groundingStatus: "kb-grounded" | "module-grounded"` en el contenido generado (y en
   el `provenance` del Asset). La UI muestra un badge cuando el contenido es
   module-grounded — misma filosofía de fallback honesto que ADR-0015 definió para el
   storyboard.

## Consecuencias

- El diseñador sabe si el contenido está anclado a documentos del cliente antes de
  aprobarlo, sin mirar Supabase.
- `module-grounded` es un estado válido, no un error: el warning informa, no bloquea.

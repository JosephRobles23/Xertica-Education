# ADR-0007: Declarative Render Plan

- **Estado:** Aceptado
- **Fecha:** 2026-07-07
- **Deciden:** Video Production (sebas)

## Contexto

El pipeline de video actual (`VideoService._run_render_job`) ejecuta etapas de forma inline e imperativa: llama a adapters, invoca FFmpeg, escribe archivos temporales, todo mezclado en un solo método de ~400 líneas. Migrar esto a un orquestador diferente (LangGraph, ADK, Antigravity) requeriría desentrañar la lógica de negocio de las llamadas a herramientas.

Al mismo tiempo, el equipo tiene 4 desarrolladores en paralelo y el pipeline de video es responsabilidad de uno solo (sebas). Un plan declarativo permite testear y modificar etapas sin tocar la orquestación.

## Decisión

Dividir el pipeline en dos conceptos separados:

1. **Render Plan** — modelo Pydantic declarativo que describe las operaciones, sus entradas y sus salidas esperadas. No contiene lógica de ejecución.
2. **Render Executor** — componente que itera sobre las etapas del Render Plan y las ejecuta en secuencia. Es reemplazable (hoy determinista, mañana LangGraph/ADK) sin cambiar el contrato del plan.

El `RenderPlan` se persiste como parte del registro del Job (columna `result.provenance.render_plan`), permitiendo auditoría, reanudación y depuración.

## Consecuencias

**Positivo:**
- Migrar a LangGraph/ADK en el futuro requiere solo reescribir el Executor; el Plan y sus etapas no cambian.
- Cada etapa es testeable de forma aislada (unit test por etapa, no un monólogo de 400 líneas).
- El plan es serializable a JSON → se puede inspeccionar, reanudar, y auditar.

**Negativo:**
- Más código upfront (modelo Pydantic + executor + transformer) en vez del actual método inline.
- El executor secuencial introduce overhead mínimo de serialización/deserialización entre etapas.

**Condicionado a:**
- ADR-0006 (Video Asset Renderizado) — el plan produce un Asset, no es el Asset mismo.
- ADR-0008 (Remotion Composition Engine) — el plan describe etapas que el executor resuelve con Remotion, no con FFmpeg.

# Decision Map — Nueva Ruta vendor-neutral + brief unificado · rama main

> **Propósito:** rediseñar la página "Nueva ruta de aprendizaje" (Gate 0) para contenido de
> cualquier ámbito (no sesgado al stack Google), con UI/UX moderna y menos campos, y arreglar
> la brecha raíz: la estructura pegada por el usuario se descartaba antes de llegar a la IA.
>
> **Origen:** sesión de grilling de 11 preguntas (2026-08-17). Todas las ramas quedaron
> resueltas — no hay frontera abierta.
>
> **Carpetas afectadas:** `apps/web/src/modules/new-route/` · `apps/web/src/shared/{lib,store}/` ·
> `apps/api/services/{route_structurer,research}/` · `apps/api/prompts/` · `apps/api/adapters/llm/` ·
> `apps/api/config/settings.py` · `docs/adr/`
>
> **Plan técnico ejecutable:** `docs/dev/plan-nueva-ruta-vendor-neutral.md`

---

## Brechas que motivaron el rediseño (evidencia)

- `UploadStructureDialog.tsx:74-77` — al pegar la estructura como texto, `submitText()` crea
  `{ name: 'Estructura pegada', kind: 'texto' }` **sin el texto**; `NuevaRuta.tsx` no tiene rama
  de subida para `kind === 'texto'`. La estructura del usuario nunca llegaba al backend.
- `services/research/service.py:11-92` — `TOOL_REGISTRY` con aliases genéricos ("imagen",
  "datos", "prompt", "razonamiento", "diseño") que matchean casi cualquier brief en español y
  fuerzan herramientas Google.
- `services/research/service.py:545-547` — si no se detecta nada, fallback duro a Gemini
  (`tools = [TOOL_REGISTRY[2]]`).
- `config/settings.py:75` — el structurer usaba `gpt-4o-mini` pese a que los docstrings y
  [[docs/adr/0014-structure-generation-llm]] dicen Haiku 4.5.
- `adapters/llm/openrouter.py:60` — fallback silencioso a mock ante cualquier fallo HTTP:
  el Job muere `failed` sin motivo y la UI se queda con la propuesta enlatada.

---

## Ya decidido (grilling 2026-08-17 — sin niebla)

1. **Vendor-neutral total en UI.** Muere el campo `usesGoogleWorkspace` (solo lo consumía el
   mock del structurer; el prompt real nunca lo leyó), placeholders y copy sin nombres de
   producto. La detección de stack queda en manos del LLM leyendo brief/material.

2. **Un solo textarea inteligente (objetivo + estructura).** Todo el texto viaja como `brief`
   (campo existente — cero contrato nuevo). El prompt del structurer clasifica: si el texto
   contiene una estructura reconocible, la respeta; si no, propone. Badge informativo en UI por
   **heurística local sin LLM** (regex de módulos/lecciones/numeración) — sin endpoint nuevo,
   sin latencia, sin costo.

3. **Una sola zona "Material de apoyo" multi-archivo.** Las tres puertas actuales (dialog de
   estructura, "Propuesta de la compañía", "Material de referencia") van al mismo destino del
   backend (`documents` → `parsed_docs`); la separación era ficción de UI. Se fusionan.

4. **Contexto de la compañía: 4 campos planos, sin wizard.** Industria · Área · Audiencia ·
   Empresa. Mueren: URL (prometía inferencia que no existía), tabs (`CUSTOMER_STEPS`), botón
   "Inferir contexto" (regex local, teatro de IA). Empresa se añade al prompt del structurer
   para personalizar ejemplos/labs (customerContext ya es dict libre — sin cambio de contrato).

5. **Área: chips sugeridos + texto libre.** `CustomerArea` pasa de union literal a `string`;
   las 6 áreas actuales quedan como atajos clicables. Patrón tags (Linear/Notion).

6. **Modelo `gemini-3.6-flash` + fallo honesto.** OpenRouter `google/gemini-3.6-flash`
   ($0.75/M input, 1M contexto — briefs con estructuras largas caben sin truncar). Timeout 90s.
   Para el rol `route_structurer` el adapter **lanza el error real** en vez del mock silencioso;
   el motivo llega a `job.error` y la UI ya tiene el estado `failed` + "Regenerar". Sin retry
   multi-modelo (OpenRouter ya hace failover de providers; resiliencia extra = YAGNI hoy).

7. **Fidelidad a nivel módulo/tema, no a nivel lección.** Restricción de dominio vigente:
   máx 8 módulos y tipos de componente únicos por módulo (`normalize.py`). Las lecciones de un
   módulo fuente se fusionan en el `summary` del componente lesson; un módulo denso puede
   dividirse en dos. Permitir N lessons por módulo sería un cambio de dominio profundo →
   **fuera de alcance**, ADR futuro si el negocio lo pide (multiplicaría costos de generación
   por componente).

8. **Jerarquía de esqueleto: textarea > docs > proponer.** Enmienda parcial del material-first
   de [[docs/adr/0014-structure-generation-llm]] — se registra como **ADR-0024** (no se edita
   el 0014, se supersede parcialmente). `_MAX_DOC_CHARS` 12k → 40k. El ejemplo
   "Nano Banana para Marketing" sale del prompt (ejemplo neutral).

9. **Layout hero-first.** Textarea protagonista arriba (patrón v0/NotebookLM: la entrada
   principal enorme e invitante, lo opcional después); material → contexto colapsado →
   research → CTA. Sistema visual existente (Tailwind 4 + shadcn) — "moderna y amigable" por
   jerarquía, espaciado y microcopy, no por cambiar de librería.

10. *(Subsumida en 11 — el usuario amplió el alcance al sourcing.)*

11. **Research: detección abierta con LLM + registro como capa de verificación.** El LLM
    (rol `researcher`, hoy huérfano en `settings.model_names`) detecta las herramientas
    *realmente mencionadas* (set abierto: Excel, Figma, SAP…). Las registradas en
    `TOOL_REGISTRY` salen verificadas con sus fuentes oficiales; las no registradas pasan por
    búsqueda y degradan a `requires-review` (estado ya soportado por
    [[docs/adr/0017-deep-research-source-review-policy]]). Se podan los aliases genéricos del
    registro (fix del 80% del sesgo) y se elimina el fallback forzado a Gemini. La verificación
    por allowlist de [[docs/adr/0016-approved-research-sources]] se **mantiene** — cambia solo
    la detección. Compatible con [[docs/adr/0011-deep-research-without-pre-generation-gate]].

---

## Fuera de alcance (declarado)

- Cambio de dominio para permitir N componentes del mismo tipo por módulo (fidelidad 1:1 a
  nivel lección) → ADR propio con análisis de costos de generación.
- Limpieza de los datos demo sesgados de `apps/web/src/shared/data/routes.ts` (rutas de
  demostración, no afectan la generación real).

## Deuda detectada de paso (no bloqueante)

- Archivos duplicados de sync (`* 2.py`, `* 3.py`, `* 4.py`) en `apps/api/prompts/`,
  `apps/api/tests/` y `apps/api/adapters/research/`.
- `docs/adr/README.md` desactualizado (no lista 0019, 0021-0023) y colisiones de numeración
  en 0006-0008, 0011-0012, 0015-0017, 0020.
- Rol `researcher` declarado en `settings.model_names` sin ningún llamador (se adopta en la
  decisión 11).

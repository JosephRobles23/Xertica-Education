# Skills Agénticas para Xertica Education

> Sistema de 12 skills para desarrollo agéntico, adaptadas de [Matt Pocock](https://github.com/mattpocock/skills) + [Ponytail](https://github.com/DietrichGebert/ponytail). Configuradas para 3 providers: **Claude Code**, **Cursor** y **Antigravity**.
>
> **Fecha:** junio 2026 · **Stack:** Python · FastAPI · LangGraph · Next.js · Supabase

---

## Tabla de contenidos

1. [Las 12 skills — glosario en español](#1-las-12-skills--glosario-en-español)
2. [Invocación: model-invoked vs user-invoked](#2-invocación-model-invoked-vs-user-invoked)
3. [Estructura de archivos por provider](#3-estructura-de-archivos-por-provider)
4. [Ponytail: qué es y cómo funciona](#4-ponytail-qué-es-y-cómo-funciona)
5. [El pipeline agéntico completo](#5-el-pipeline-agéntico-completo)
6. [Ejemplo práctico: Verificación de Fuentes (Gate 1)](#6-ejemplo-práctico-verificación-de-fuentes-gate-1)
7. [Artefactos que genera el sistema](#7-artefactos-que-genera-el-sistema)
8. [Referencia rápida de comandos](#8-referencia-rápida-de-comandos)
9. [Configuración por provider](#9-configuración-por-provider)

---

## 1. Las 12 skills — glosario en español

### Diseño y planificación (6 skills)

| # | Skill | Nombre en español | Qué hace | Cuándo usarla |
|---|-------|-------------------|----------|---------------|
| 1 | `/grilling` | **Interrogatorio** | Entrevista implacable sobre un plan o diseño. Pregunta una a una, propone su respuesta recomendada, explora el código cuando puede responder sola. | Antes de implementar cualquier módulo. Cuando tienes un plan y quieres encontrar los huecos. |
| 2 | `/domain-modeling` | **Modelado de dominio** | Mantiene el vocabulario canónico del proyecto en `CONTEXT.md` (glosario puro, sin implementación) y ADRs en `docs/adr/`. Desafía términos vagos, propone términos precisos, cruza lo que dices contra el código. | Siempre activa durante sesiones de diseño. Se invoca automáticamente desde `/grill-with-docs`. |
| 3 | `/grill-with-docs` | **Interrogatorio con documentación** | Combina `/grilling` + `/domain-modeling`. Mientras te interroga, actualiza el glosario (`CONTEXT.md`) y crea ADRs cuando hay decisiones irreversibles. | Cuando quieres que las decisiones se documenten automáticamente mientras las tomas. **Autodocumentación dinámica.** |
| 4 | `/decision-mapping` | **Mapa de decisiones** | Convierte una idea suelta en un mapa de tickets de investigación secuenciados. Usa "niebla de guerra" — solo mapea lo visible, descubre el resto ticket por ticket. Tres tipos: Research, Prototype, Discuss. | Cuando el problema tiene demasiadas incógnitas. Proyectos multi-sesión donde cada decisión abre nuevas preguntas. |
| 5 | `/prototype` | **Prototipo** | Código desechable que responde una pregunta. Dos ramas: **Logic** (app de terminal para probar state machines) y **UI** (variaciones radicales en una ruta, switchable por URL). Sin tests, sin polish — se borra cuando responde la pregunta. | Cuando "¿funciona esta lógica?" o "¿cómo debería verse?" no se puede responder sin código. |
| 6 | `/teach` | **Enseñar** | Crea un workspace de enseñanza con lecciones HTML interactivas, glosarios, reference docs y learning records. Usa principios de ciencia cognitiva (retrieval practice, spacing, interleaving). | Para onboardear gente al dominio (gates HITL, spine Ruta/Módulo/Componente, grounding y provenance) o aprender un tema nuevo. |

### Producción y entrega (3 skills)

| # | Skill | Nombre en español | Qué hace | Cuándo usarla |
|---|-------|-------------------|----------|---------------|
| 7 | `/to-prd` | **Generar PRD** | Sintetiza la conversación actual en un PRD formal con Problem Statement, User Stories extensas, Implementation Decisions, Testing Decisions y Out of Scope. No interroga — solo sintetiza. Publica en **Linear**. | Después de sesiones de grilling, cuando el diseño está claro. |
| 8 | `/to-issues` | **Generar tickets** | Rompe un PRD en vertical slices (tracer bullets). Cada issue corta a través de TODAS las capas end-to-end (schema → API → UI → tests). Publica en **Linear** con labels de triage. | Después de tener un PRD aprobado. Convierte el plan en trabajo ejecutable. |
| 9 | `/tdd` | **Desarrollo guiado por tests** | Ciclos RED → GREEN estrictos y verticales (un test → una implementación → siguiente). Tests prueban comportamiento a través de interfaces públicas. Incluye vocabulario de diseño (Module, Depth, Seam). | Durante la implementación de lógica de negocio. |

### Minimalismo — Ponytail (2 skills)

| # | Skill | Nombre en español | Qué hace | Cuándo usarla |
|---|-------|-------------------|----------|---------------|
| 10 | `/ponytail` | **Modo minimalista** | Fuerza la solución más simple: escalera de decisión (¿necesita existir? → stdlib → nativo → dep existente → una línea → mínimo código). Tres intensidades: lite, full, ultra. | **Siempre activo** durante implementación. |
| 11 | `/ponytail-review` | **Revisión minimalista** | Revisa diffs buscando exclusivamente over-engineering. Una línea por hallazgo con tags: `delete:`, `stdlib:`, `native:`, `yagni:`, `shrink:`. | Antes de cada PR. Solo caza complejidad, no bugs. |

### Arquitectura (1 skill)

| # | Skill | Nombre en español | Qué hace | Cuándo usarla |
|---|-------|-------------------|----------|---------------|
| 12 | `/improve-architecture` | **Mejorar arquitectura** | Escanea el codebase buscando módulos shallow, genera reporte HTML visual (Tailwind + Mermaid) con diagramas before/after, y grilla sobre el candidato que elijas. | Post-MVP, cuando el código ya existe y quieres profundizar módulos. |

---

## 2. Invocación: model-invoked vs user-invoked

Las skills se dividen en dos tipos según cómo se activan:

| Tipo | Qué significa | Costo |
|------|---------------|-------|
| **Model-invoked** | El agente la detecta y activa automáticamente | Gasta tokens (descripción cargada cada turno) |
| **User-invoked** | Solo se activa cuando tú escribes el comando | Cero costo de contexto |

### Distribución de las 12 skills

| Model-invoked (4) | User-invoked (8) |
|---|---|
| `/grilling` — se activa al detectar planes por validar | `/grill-with-docs` — tú decides cuándo documentar |
| `/domain-modeling` — se activa cuando otra skill lo necesita | `/decision-mapping` — proceso pesado, tú lo inicias |
| `/tdd` — se activa al implementar lógica de negocio | `/prototype` — crea archivos, mejor controlado |
| `/ponytail` — siempre activo por diseño | `/to-prd` — publica en Linear, requiere intención |
| | `/to-issues` — publica en Linear, requiere intención |
| | `/ponytail-review` — tú decides cuándo revisar |
| | `/teach` — proceso multi-sesión |
| | `/improve-architecture` — genera reporte HTML |

### Equivalencia entre providers

| Concepto | Claude Code | Cursor | Antigravity |
|----------|-------------|--------|-------------|
| Model-invoked | Sin `disable-model-invocation` en YAML | `alwaysApply: false` + descripción rica | Trigger en header del .md |
| User-invoked | `disable-model-invocation: true` | `alwaysApply: false` (manual con @nombre) | Invocación explícita |
| Siempre activo (Ponytail) | Model-invoked con "ACTIVE EVERY RESPONSE" | `alwaysApply: true` | "Always active" en header |

---

## 3. Estructura de archivos por provider

```
xertica-education/
├── .claude/skills/                        ← Claude Code
│   ├── grilling/SKILL.md                    model-invoked
│   ├── domain-modeling/SKILL.md             model-invoked
│   ├── grill-with-docs/SKILL.md             user-invoked
│   ├── decision-mapping/SKILL.md            user-invoked
│   ├── prototype/SKILL.md                   user-invoked
│   ├── to-prd/SKILL.md                     user-invoked (Linear)
│   ├── to-issues/SKILL.md                  user-invoked (Linear)
│   ├── tdd/SKILL.md                        model-invoked
│   ├── ponytail/SKILL.md                   model-invoked (always)
│   ├── ponytail-review/SKILL.md            user-invoked
│   ├── teach/SKILL.md                      user-invoked
│   └── improve-architecture/SKILL.md       user-invoked
│
├── .cursor/rules/                         ← Cursor
│   ├── grilling.mdc                         agent-requested
│   ├── domain-modeling.mdc                  agent-requested
│   ├── grill-with-docs.mdc                  manual (@grill-with-docs)
│   ├── decision-mapping.mdc                 manual (@decision-mapping)
│   ├── prototype.mdc                        manual (@prototype)
│   ├── to-prd.mdc                          manual (@to-prd)
│   ├── to-issues.mdc                       manual (@to-issues)
│   ├── tdd.mdc                             agent-requested
│   ├── ponytail.mdc                        alwaysApply: true
│   ├── ponytail-review.mdc                 manual (@ponytail-review)
│   ├── teach.mdc                           manual (@teach)
│   └── improve-architecture.mdc            manual (@improve-architecture)
│
├── .agents/rules/                         ← Antigravity
│   ├── grilling.md                          trigger-based
│   ├── domain-modeling.md                   trigger-based
│   ├── grill-with-docs.md                   explicit invocation
│   ├── decision-mapping.md                  explicit invocation
│   ├── prototype.md                         explicit invocation
│   ├── to-prd.md                           explicit invocation
│   ├── to-issues.md                        explicit invocation
│   ├── tdd.md                              trigger-based
│   ├── ponytail.md                         always active
│   ├── ponytail-review.md                  explicit invocation
│   ├── teach.md                            explicit invocation
│   └── improve-architecture.md             explicit invocation
```

---

## 4. Ponytail: qué es y cómo funciona

Ponytail fuerza **la solución más simple que funcione**. Encarna a un senior developer perezoso (eficiente, no descuidado) que ha visto cada codebase over-engineered.

**Filosofía:** "El mejor código es el código que nunca escribiste."

### La escalera de decisión

El agente se detiene en el primer peldaño que aguante:

```
1. ¿Necesita existir?           → Si es especulativo, no lo hagas (YAGNI)
2. ¿La stdlib lo resuelve?      → Úsala
3. ¿Hay un feature nativo?      → <input type="date"> en vez de un date picker
4. ¿Ya está instalado como dep? → Úsalo, no agregues otra dependencia
5. ¿Puede ser una línea?        → Una línea
6. Solo entonces:               → El mínimo código que funcione
```

### Impacto medido (benchmarks)

| Métrica | Sin Ponytail | Con Ponytail | Reducción |
|---------|-------------|-------------|-----------|
| Líneas de código | 100% | 6–46% | **54–94% menos** |
| Tokens consumidos | 100% | 78% | **22% menos** |
| Costo | 100% | 80% | **20% menos** |
| Velocidad | baseline | 1.27x | **27% más rápido** |

### Tres intensidades

| Nivel | Comportamiento |
|-------|----------------|
| **lite** | Construye lo pedido, pero nombra la alternativa perezosa en una línea. |
| **full** | La escalera se aplica. Stdlib y nativo primero. Diff más corto, explicación más corta. **Default.** |
| **ultra** | Extremista YAGNI. Borrar antes que agregar. Envía el one-liner y cuestiona el requerimiento. |

### Qué NO simplifica

Nunca toca: validación en boundaries de confianza, manejo de errores que previene pérdida de datos, seguridad, accesibilidad, ni nada explícitamente solicitado.

### Marcadores `ponytail:`

Cuando toma un atajo deliberado, lo marca con su techo y ruta de upgrade:

```python
# ponytail: global lock, per-account locks si el throughput importa
lock = threading.Lock()
```

---

## 5. El pipeline agéntico completo

Las 12 skills forman un pipeline de 8 fases. Cada fase produce artefactos que alimentan la siguiente.

```
                    ┌─────────────────────────────────────────┐
                    │  PIPELINE AGÉNTICO DE XERTICA EDUCATION │
                    └─────────────────────────────────────────┘

  FASE 1                FASE 2                FASE 3              FASE 4
  ┌──────────┐          ┌──────────┐          ┌──────────┐        ┌──────────┐
  │ /decision│          │/grill-   │          │/prototype│        │ /to-prd  │
  │ -mapping │───────►  │ with-docs│───────►  │          │──────► │          │
  │          │          │          │          │          │        │          │
  │ Mapa de  │          │Interroga │          │ Prueba   │        │Sintetiza │
  │decisiones│          │+ documenta│         │hipótesis │        │en PRD    │
  └──────────┘          └──────────┘          └──────────┘        └──────────┘
       │                     │                     │                   │
       ▼                     ▼                     ▼                   ▼
  decision-map.md       CONTEXT.md            prototype/          PRD en Linear
                        docs/adr/             (se borra)

  FASE 5                FASE 6                FASE 7              FASE 8
  ┌──────────┐          ┌──────────┐          ┌──────────┐        ┌──────────┐
  │/to-issues│          │  /tdd    │          │/ponytail │        │/improve- │
  │          │───────►  │    +     │───────►  │ -review  │──────► │architectu│
  │          │          │/ponytail │          │          │        │re        │
  │ Vertical │          │          │          │Caza over-│        │Profundiza│
  │ slices   │          │RED→GREEN │          │engineering│       │ módulos  │
  └──────────┘          └──────────┘          └──────────┘        └──────────┘
       │                     │                     │                   │
       ▼                     ▼                     ▼                   ▼
  Issues en Linear      Código + tests        Diff limpio         Reporte HTML
  (ready-for-agent)     en rama feature       listo para PR       + mejoras
```

### Skills que se activan solas durante el pipeline

- `/grilling` — se activa dentro de `/decision-mapping` y `/improve-architecture`
- `/domain-modeling` — se activa dentro de `/grill-with-docs` y `/improve-architecture`
- `/ponytail` — siempre activo durante Fase 6
- `/tdd` — se activa al implementar lógica de negocio en Fase 6

### Fase 1: Mapeo de decisiones (`/decision-mapping`)

**Input:** La idea o módulo a construir.
**Output:** Un `decision-map.md` con tickets numerados.

```markdown
## #1: ¿Qué dominios cuentan como "verificable Google" para el Gate 1?
Type: Research
### Question
Necesitamos la lista de dominios que Arantza puede marcar como verificados
(youtube.com, docs.google.com, support.google.com…) o si Xertica Education
debe consultar una API de reputación en vez de un allowlist estático.
### Answer
(se llena al resolver el ticket)
```

**Fog of war:** Solo se mapean las decisiones visibles. Al resolver #1, pueden aparecer #4, #5 que antes estaban en la niebla.

### Fase 2: Interrogatorio con documentación (`/grill-with-docs`)

**Input:** Un ticket del decision-map (o un diseño directo).
**Output:** `CONTEXT.md` actualizado + ADRs cuando aplique.

El agente pregunta una a una:

> "Tu arquitectura dice que el `route_structurer` respeta la estructura cuando el input ya viene definido. ¿Qué pasa si el autor trae solo 2 módulos pero pide una duración objetivo de 40 minutos? **Mi recomendación:** el LLM propone dividir en más módulos solo si excede ~10 min por módulo, y lo deja como sugerencia editable en el árbol — nunca lo fuerza sin que el humano lo apruebe en el Gate 0."

Mientras tanto, actualiza `CONTEXT.md`:

```markdown
## Gate (HITL)
Punto de interrupción durable en el grafo LangGraph donde la ejecución se
detiene y espera aprobación humana antes de continuar. Xertica Education
tiene cuatro: Gate 0 (estructura), Gate 1 (fuentes), Gate 2 (guion), Gate 3 (asset final).

## Provenance
Registro obligatorio en cada `ASSET`: qué modelo/pipeline lo generó, su costo
y su tiempo. Alimenta la trazabilidad de gasto y la confianza del contenido.
```

### Fase 3: Prototipo (`/prototype`)

**Input:** Una pregunta que no se responde sin código.
**Output:** Código desechable que responde la pregunta.

- **Logic branch:** "¿La state machine del asset maneja borrador → generado → en_revisión → aprobado al rechazar en Gate 3?" → app de terminal
- **UI branch:** "¿Cómo se ve el editor de árbol del Gate 0?" → 3 variaciones en `?variant=1|2|3`

Se borra el prototipo cuando responde la pregunta. Se guarda la decisión en un ADR.

### Fase 4: Generar PRD (`/to-prd`)

**Input:** Todo lo discutido.
**Output:** PRD publicado en **Linear** con label `ready-for-agent`.

Incluye: Problem Statement, User Stories extensas, Implementation Decisions (sin file paths), Testing Decisions con seams, Out of Scope.

### Fase 5: Generar tickets (`/to-issues`)

**Input:** PRD aprobado.
**Output:** Vertical slices publicados en **Linear**.

```
XED-12: Adapter MinerU para parsing de PDF/DOCX/PPTX a Markdown
XED-13: route_structurer — propuesta de estructura desde texto libre
XED-14: Editor de árbol con refinamiento granular por nodo  → Blocked by: #13
XED-15: Gate 1 — pantalla de revisión y scoring de fuentes  → Blocked by: #12
```

**Labels de Linear:** `ready-for-agent`, `ready-for-human`, `needs-info`, `bug`, `enhancement`.

### Fase 6: Implementar con TDD + Ponytail (`/tdd` + `/ponytail`)

**Input:** Un issue `ready-for-agent`.
**Output:** Código + tests en rama feature.

```
RED:   test_dominio_verificado_score_alto() → FALLA
GREEN: allowlist + comparación de dominio, una línea (Ponytail: stdlib)

RED:   test_word_budget_no_excede_limite() → FALLA
GREEN: len(texto.split()) <= budget (Ponytail: no tokenizer custom)

RED:   test_provenance_registra_modelo_y_costo() → FALLA
GREEN: dict literal en el asset (Ponytail: no clase ProvenanceBuilder)
```

```python
# ponytail: allowlist simple, upgrade a API de reputación si la lista crece
dominio = urlparse(fuente.url).netloc.removeprefix("www.")
if dominio in DOMINIOS_VERIFICADOS:
    fuente.verificada_google = True
```

### Fase 7: Revisión minimalista (`/ponytail-review`)

**Input:** El diff antes de hacer PR.
**Output:** Lista de simplificaciones.

```
L12-38: yagni: ReconciliationStrategy ABC con una sola implementación. Inlinear.
L45: stdlib: json.dumps manual. return JSONResponse.
L89: native: moment.js para una fecha. date.isoformat(), 0 deps.
net: -31 lines possible.
```

### Fase 8: Mejorar arquitectura (`/improve-architecture`)

**Input:** Codebase existente post-MVP.
**Output:** Reporte HTML con candidatos de profundización + sesión de grilling.

Se genera un HTML con Tailwind + Mermaid mostrando módulos shallow con diagramas before/after. Después el usuario elige un candidato y se inicia un `/grilling` para diseñar la mejora.

---

## 6. Ejemplo práctico: Verificación de Fuentes (Gate 1)

Walkthrough del pipeline completo aplicado a una de las piezas más sensibles del MVP: decidir qué fuentes entran a la Base de Conocimiento antes del Gate 1.

### Paso 1 — Decision Mapping

```
> /decision-mapping "Verificación de fuentes para el Gate 1 de Xertica Education"
```

Produce:

```markdown
# Decision Map: Verificación de Fuentes (Gate 1)

## #1: ¿Qué dominios cuentan como "verificable Google"?
Type: Research · Blocked by: —

## #2: ¿El score de confianza se calcula al vuelo o se precalcula?
Type: Discuss · Blocked by: —

## #3: ¿Cómo se ve la pantalla de revisión de fuentes (Gate 1)?
Type: Prototype · Blocked by: #1

## #4 – #N: (fog of war)
```

### Paso 2 — Resolver tickets con grilling + docs

```
> /decision-mapping resume decision-map-gate1-fuentes.md #2
```

Sesión de `/grill-with-docs`:

> **Agente:** "Si precalculas el score en un job batch, ¿qué pasa cuando Arantza agrega una fuente nueva a mitad de sesión?"
> **Tú:** "Buen punto, necesita ser on-demand."
> **Agente:** "Actualizo CONTEXT.md y propongo ADR-0002: Scoring de fuentes on-demand."

### Paso 3 — Prototype de la pantalla de revisión

```
> /prototype "¿Cómo se ve la pantalla de revisión de fuentes (Gate 1)?"
```

3 variaciones UI. Se elige la de tarjetas con badge de verificación + quote. Se borra el prototipo.

### Paso 4 — PRD y tickets

```
> /to-prd           → PRD publicado en Linear con ~18 user stories
> /to-issues        → 6 vertical slices en Linear
```

### Paso 5 — Implementar con TDD + Ponytail

```python
# test_source_verification.py
def test_dominio_youtube_oficial_score_alto():
    fuente = make_fuente(url="https://youtube.com/watch?v=abc123")
    result = verificar_fuente(fuente)
    assert result.score >= 0.85
    assert result.verificada_google is True

def test_dominio_no_google_score_bajo():
    fuente = make_fuente(url="https://blog-externo.com/post-2026")
    result = verificar_fuente(fuente)
    assert result.score < 0.5
    assert result.verificada_google is False
```

```python
# sourcing/verification.py
from urllib.parse import urlparse

DOMINIOS_VERIFICADOS = {
    "youtube.com", "docs.google.com", "support.google.com", "developers.google.com",
}

def verificar_fuente(fuente):
    dominio = urlparse(fuente.url).netloc.removeprefix("www.")
    # ponytail: allowlist simple, upgrade a API de reputación si la lista crece
    score = 0.95 if dominio in DOMINIOS_VERIFICADOS else 0.3
    fuente.verificada_google = score >= 0.8
    return ScoreResult(score=score, verificada=fuente.verificada_google)
```

### Paso 6 — Review

```
> /ponytail-review
Lean already. Ship.
```

---

## 7. Artefactos que genera el sistema

Después de adoptar las 12 skills, el repositorio acumula estos artefactos:

```
xertica-education/
├── CONTEXT.md                              ← Glosario de dominio (/domain-modeling)
├── docs/
│   ├── adr/                                ← Decisiones arquitectónicas
│   │   ├── 0001-mineru-parsing-scaffold.md
│   │   ├── 0002-scoring-fuentes-on-demand.md
│   │   └── 0003-gate0-route-builder-hitl.md
│   ├── decisions/                          ← Mapas de decisiones (/decision-mapping)
│   │   ├── decision-map-gate1-fuentes.md
│   │   └── decision-map-route-builder.md
│   ├── architecture/
│   │   └── xertica-education-arquitectura.md
│   └── Skills_Desarrollo_Agentico.md       ← Este documento
│
├── .claude/skills/    (12 SKILL.md)        ← Claude Code
├── .cursor/rules/     (12 .mdc)            ← Cursor
├── .agents/rules/     (12 .md)             ← Antigravity
│
└── apps/
    └── ...
```

---

## 8. Referencia rápida de comandos

### Planificación

| Comando | Cuándo | Ejemplo |
|---------|--------|---------|
| `/decision-mapping "idea"` | Idea con muchas incógnitas | `/decision-mapping "Integración con Veo 3.1 REST API"` |
| `/decision-mapping resume mapa.md #N` | Retomar un ticket | `/decision-mapping resume decision-map-gate1-fuentes.md #3` |
| `/grill-with-docs` | Stress-test + autodocumentación | `/grill-with-docs` (sobre el plan actual) |
| `/grilling` | Stress-test puro | `/grilling` (interrogatorio sin documentar) |
| `/prototype` | Responder pregunta con código | `/prototype "¿funciona la state machine del asset?"` |
| `/teach "tema"` | Aprender un concepto | `/teach "gates HITL y provenance"` |

### Producción

| Comando | Cuándo | Ejemplo |
|---------|--------|---------|
| `/to-prd` | Diseño claro, necesitas PRD | `/to-prd` → publica en Linear |
| `/to-issues` | PRD listo, necesitas tickets | `/to-issues` → vertical slices en Linear |
| `/tdd` | Implementar con tests primero | `/tdd` (ciclos RED→GREEN) |
| `/ponytail [lite\|full\|ultra]` | Cambiar intensidad | `/ponytail ultra` |

### Revisión y mejora

| Comando | Cuándo | Ejemplo |
|---------|--------|---------|
| `/ponytail-review` | Antes de PR | `/ponytail-review` (revisa el diff) |
| `/improve-architecture` | Post-MVP | `/improve-architecture` (reporte HTML) |

### Equivalencia entre providers

| Claude Code | Cursor | Antigravity |
|-------------|--------|-------------|
| `/grilling` | `@grilling` | `grilling` |
| `/domain-modeling` | `@domain-modeling` | `domain-modeling` |
| `/grill-with-docs` | `@grill-with-docs` | `grill-with-docs` |
| `/decision-mapping` | `@decision-mapping` | `decision-mapping` |
| `/prototype` | `@prototype` | `prototype` |
| `/to-prd` | `@to-prd` | `to-prd` |
| `/to-issues` | `@to-issues` | `to-issues` |
| `/tdd` | `@tdd` | `tdd` |
| `/ponytail` | (always active) | (always active) |
| `/ponytail-review` | `@ponytail-review` | `ponytail-review` |
| `/teach` | `@teach` | `teach` |
| `/improve-architecture` | `@improve-architecture` | `improve-architecture` |

---

## 9. Configuración por provider

### Claude Code

Las skills ya están en `.claude/skills/`. Se detectan automáticamente. Las model-invoked aparecen en el menú de skills disponibles. Las user-invoked se activan escribiendo `/nombre`.

### Cursor

Las reglas están en `.cursor/rules/`. Cursor las detecta automáticamente:
- `ponytail.mdc` con `alwaysApply: true` se carga siempre
- Las demás se invocan con `@nombre` en el chat o el agente las activa según la descripción

### Antigravity

Las reglas están en `.agents/rules/`. Se cargan según las convenciones de Antigravity CLI (`agy`). Las que tienen "Always active" en el header se aplican automáticamente.

### Linear (issue tracker)

Las skills `/to-prd` y `/to-issues` publican directamente en Linear via MCP. Labels configurados:

| Label | Uso |
|-------|-----|
| `bug` | Algo está roto |
| `enhancement` | Feature nueva o mejora |
| `needs-info` | Esperando más información |
| `ready-for-agent` | Listo para que un agente IA lo implemente |
| `ready-for-human` | Necesita implementación humana |

---

*12 skills adaptadas de [mattpocock/skills](https://github.com/mattpocock/skills) y [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) para el proyecto Xertica Education. Configuradas para Claude Code, Cursor y Antigravity.*

# Kickoff — Arantza · Sourcing / Deep Research

> Cómo llevar tus **primeras tareas** de principio a fin con las 12 skills agénticas.
> Lee primero: [`Skills_Desarrollo_Agentico.md`](../../../Documents/Skills/Skills_Desarrollo_Agentico.md) (pipeline completo) · [`CONTEXT.md`](../../CONTEXT.md) (dominio) · [`docs/adr/`](../adr/) · [`architecture.md`](../arquitectura/architecture.md) §14.

## Tus primeras tareas
1. **Spike — límites de Deep Research** ([issue #21](../issues/pending/shared/issue-21-research-spike-quotas.md)) — *research primero: define el terreno antes de construir*.
2. **Contexto del Cliente — formulario previo a la ruta** ([issue #16](../issues/pending/arantza/issue-16-customer-context-route.md)) — captura `URL`, `industria`, `área`, `Google Workspace` e inyéctalos en el prompt del `route_structurer`.

El orden es a propósito: el **spike** acota qué es posible con Deep Research; con eso claro, construyes el **formulario** sabiendo qué contexto vale la pena capturar.

---

## Cómo se mapea tu flujo a las skills

Piensa en las skills como un **pipeline de 8 fases**. No todas aplican a cada tarea: un *spike* vive en las fases de exploración; una *feature* recorre el pipeline completo.

```
Spike (#21)      → /decision-mapping → /prototype → /grill-with-docs → ADR
Feature (#16)    → /decision-mapping → /grill-with-docs → /prototype → /to-prd → /to-issues → /tdd+/ponytail → /ponytail-review
```

---

## Tarea 1 · Spike — límites de Deep Research

### Paso 1 — Mapear lo desconocido: `/decision-mapping`
**Concepto.** Convierte una pregunta borrosa en un mapa de tickets secuenciados. Usa "niebla de guerra": solo mapea lo visible; al resolver un ticket aparecen los siguientes.
**Por qué importa para ti.** Un spike sin mapa se vuelve un agujero de horas. El mapa te da un criterio de "terminado" y hace visible qué bloquea a qué.

```
> /decision-mapping "Límites técnicos y de cuotas de Deep Research para el MVP"
```
```markdown
# Decision Map: Límites de Deep Research
## #1: ¿Cuál es el rate limit / cuota diaria por proyecto?      Type: Research
## #2: ¿Costo por búsqueda y latencia p50/p95?                  Type: Research
## #3: ¿Cuántas fuentes útiles devuelve por consulta típica?     Type: Prototype · Blocked by #1
## #4–#N: (fog of war)
```

### Paso 2 — Responder con código desechable: `/prototype`
**Concepto.** Código que responde **una** pregunta y se borra. Rama *Logic* (probar comportamiento) o *UI* (probar apariencia). Sin tests, sin polish.
**Por qué importa para ti.** "¿Cuántas fuentes verificables devuelve una consulta real?" no se responde en abstracto. Un script de 30 líneas que dispara N consultas y cuenta resultados/latencia lo responde en minutos.

### Paso 3 — Documentar la decisión: `/grill-with-docs`
**Concepto.** `/grilling` (interrogatorio implacable, una pregunta a la vez con recomendación) + `/domain-modeling` (mantiene el glosario `CONTEXT.md` y crea **ADRs** en decisiones irreversibles).
**Por qué importa para ti.** El resultado del spike es una **decisión** ("Deep Research soporta X consultas/día → el MVP hace batching nocturno"). Si no queda en un ADR, se pierde y alguien la vuelve a investigar.

> **Agente:** "Encontraste un límite de N/día. ¿Eso obliga a cachear resultados por `tema` de Ruta o basta con reintentos? **Recomendación:** cachear por `(tema, industria)` porque dos clientes de la misma industria comparten fuentes." → propone **ADR-0006: Cuotas y caché de Deep Research**.

---

## Tarea 2 · Contexto del Cliente (formulario previo a la ruta)

### Paso 1 — `/decision-mapping`
```
> /decision-mapping "Formulario de Contexto del Cliente previo a la Ruta"
```
```markdown
## #1: ¿Qué campos cambian REALMENTE el prompt del route_structurer?   Type: Discuss
## #2: ¿El contexto se persiste (tabla) o solo vive en la request?      Type: Discuss
## #3: ¿Cómo se ve el formulario antes de /nueva-ruta?                  Type: Prototype · Blocked by #1
```

### Paso 2 — `/grill-with-docs` (interrogatorio + glosario)
**Por qué importa.** Aquí se decide el **contrato**: qué campos entran, cómo se llaman, dónde viven. Documentarlo en `CONTEXT.md` evita que "área" signifique cosas distintas en frontend y prompt.

> **Agente:** "Capturas *usan Google Workspace* como booleano. ¿Cambia las **fuentes** que prioriza Deep Research (favorecer `docs.google.com` / `support.google.com`) o solo el tono del contenido? **Recomendación:** si es `true`, el `researcher` sube esos dominios en el allowlist de verificación — así el contexto no es decorativo, mueve el grounding."

Actualiza `CONTEXT.md`:
```markdown
## Contexto del Cliente
Metadatos capturados antes de crear la Ruta (URL, industria, área, uso de
Google Workspace) que se inyectan en el prompt del `route_structurer` para
personalizar la estructura. La `industria` se persiste en `RUTA.industria`.
```

> **Nota de dominio:** `industria` ya existe en el Spine (`learning_paths.industria`, [ADR-0005](../adr/0005-full-spine-schema.md)). Reutilízala; no inventes un campo nuevo (respeta el glosario).

### Paso 3 — `/prototype` (rama UI)
3 variaciones del formulario en `?variant=1|2|3` sobre `/nueva-ruta`. Se elige una, se borra el resto. Responde "¿cómo se ve?" sin comprometer diseño.

### Paso 4 y 5 — `/to-prd` → `/to-issues`
**Concepto.** `/to-prd` sintetiza la conversación en un PRD (Problem Statement, User Stories, Implementation/Testing Decisions, Out of Scope) y lo publica en **Linear**. `/to-issues` lo parte en **vertical slices** (cada uno corta schema→API→UI→tests).
**Por qué importa para ti.** Un slice vertical evita que entregues "el formulario sin backend". Cada ticket es demo-able solo.

### Paso 6 — Implementar: `/tdd` + `/ponytail`
**Concepto.** `/tdd`: ciclos RED→GREEN (un test que falla → mínima implementación → siguiente). `/ponytail`: siempre activo, fuerza la solución más simple (escalera: ¿existe? → stdlib → nativo → dep existente → una línea → mínimo código).
**Por qué importa para ti.** El riesgo aquí es sobre-diseñar el "motor de contexto". Ponytail lo previene.

```python
# RED
def test_contexto_se_inyecta_en_prompt():
    ctx = ContextoCliente(industria="banca", area="Finanzas", usa_workspace=True)
    prompt = construir_prompt_ruta(tema="IA generativa", contexto=ctx)
    assert "banca" in prompt and "Finanzas" in prompt

# GREEN — ponytail: f-string, no ContextBuilder ni templating engine
def construir_prompt_ruta(tema: str, contexto: ContextoCliente) -> str:
    return (
        f"Diseña una ruta sobre {tema} para el área de {contexto.area} "
        f"en la industria {contexto.industria}."
        + (" Prioriza fuentes de Google Workspace." if contexto.usa_workspace else "")
    )
```

### Paso 7 — `/ponytail-review`
**Concepto.** Revisa el diff **solo** buscando over-engineering (tags `delete:`, `stdlib:`, `native:`, `yagni:`, `shrink:`). No caza bugs (eso es `/code-review`).
**Por qué importa para ti.** Antes del PR, atrapa la clase `ContextValidator` con una sola implementación o el `enum` para 4 áreas que podría ser un `Literal`.

---

## Referencia rápida — qué skill en qué momento

| Momento | Skill | Model/User-invoked |
| :-- | :-- | :-- |
| Explorar incógnitas | `/decision-mapping` | user |
| Probar una hipótesis con código | `/prototype` | user |
| Diseñar + documentar (glosario/ADR) | `/grill-with-docs` | user |
| Formalizar el plan | `/to-prd` → `/to-issues` | user |
| Implementar | `/tdd` + `/ponytail` | model (auto) |
| Antes del PR | `/ponytail-review` | user |
| Onboarding a un concepto | `/teach "grounding y verificación de fuentes"` | user |

## Definición de listo (DoD)
- [ ] Spike: ADR con límites/cuotas y recomendación para el MVP.
- [ ] Formulario: persiste el contexto y precede a la creación de la Ruta; la estructura generada refleja industria/área.
- [ ] `CONTEXT.md` actualizado con el término *Contexto del Cliente*.
- [ ] `/ponytail-review` sin hallazgos abiertos.

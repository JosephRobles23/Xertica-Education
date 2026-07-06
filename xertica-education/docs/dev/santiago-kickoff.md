# Kickoff — Santiago · Infografía

> Cómo llevar tu **primera tarea** de principio a fin con las 12 skills agénticas.
> Lee primero: [`Skills_Desarrollo_Agentico.md`](../../../Documents/Skills/Skills_Desarrollo_Agentico.md) · [`CONTEXT.md`](../../CONTEXT.md) · [`docs/adr/`](../adr/) · [`architecture.md`](../arquitectura/architecture.md) §5 y §10.

## Tu primera tarea
- **Pipeline de generación de infografía** (backlog #13) — de contenido *grounded* de la KB a una **infografía en PDF**. Ruta: `HTML grounded → PDF`.

*(No tienes tareas nuevas en el batch de §14, así que tu kickoff arranca por tu feature de dueño: la infografía. También compartes UI común con el resto del equipo.)*

> **Recuerda el principio de arquitectura #1:** toda infografía se genera **grounded** desde la KB, con sus `sources[]`. Nada inventado. Tu Asset lleva `provenance` (modelo/costo/tiempo) y respeta el `word_budget` — la longitud es restricción de diseño, no recorte posterior.

---

## Cómo se mapea tu flujo a las skills

Tu tarea es una **feature de punta a punta** (KB → HTML → PDF → Gate 3), así que recorre el **pipeline completo**:

```
/decision-mapping → /grill-with-docs → /prototype (UI) → /to-prd → /to-issues → /tdd+/ponytail → /ponytail-review
```

### Paso 0 — (opcional) `/teach`
**Concepto.** Workspace de enseñanza con lecciones interactivas y glosario (retrieval practice, spacing).
**Por qué importa para ti.** Si no tienes claro qué significa "grounded", `provenance` o cómo un `Componente` de tipo `infografia` se materializa en un `Asset` PDF, un `/teach "spine: Componente infografia → Asset PDF, grounding y provenance"` te ahorra rework.

### Paso 1 — `/decision-mapping`
**Concepto.** Convierte la idea en tickets secuenciados; niebla de guerra (solo mapea lo visible).
**Por qué importa para ti.** El HTML→PDF tiene decisiones acopladas (motor de render, fuentes/estilos, cómo llegan las citas). Mapearlas evita rehacer el pipeline cuando descubras que el motor elegido no soporta algo.

```
> /decision-mapping "Pipeline de infografía: HTML grounded → PDF"
```
```markdown
## #1: ¿Qué motor HTML→PDF? (weasyprint vs headless Chromium)     Type: Research
## #2: ¿El LLM genera HTML completo o rellena una plantilla fija?  Type: Discuss
## #3: ¿Cómo se incrustan las citas/sources en la infografía?      Type: Discuss · Blocked by #2
## #4: ¿Cómo se ve la infografía? (layout)                         Type: Prototype · Blocked by #2
```

### Paso 2 — `/grill-with-docs` → glosario + ADR
**Concepto.** `/grilling` (interrogatorio, una pregunta a la vez con recomendación) + `/domain-modeling` (mantiene `CONTEXT.md` y crea ADRs en decisiones irreversibles).
**Por qué importa para ti.** "¿El LLM genera HTML libre o rellena una plantilla?" define reproducibilidad y costo. Es material de ADR.

> **Agente:** "Si el LLM genera HTML libre, cada infografía es impredecible y difícil de revisar en el Gate 3. **Recomendación:** el LLM produce **datos estructurados** (título, secciones, bullets, cita) y una **plantilla fija** los renderiza a HTML — controlas el diseño y el `word_budget` es verificable." → **ADR-0006: Infografía por plantilla + datos, no HTML libre**.

Actualiza `CONTEXT.md`:
```markdown
## Infografía
Componente de tipo `infografia` que se materializa en un ASSET PDF. Se genera
grounded desde la KB: el LLM produce datos estructurados (secciones + citas) y
una plantilla fija los renderiza a HTML → PDF. Respeta el word_budget.
```

### Paso 3 — `/prototype` (rama UI)
**Concepto.** Variaciones radicales de UI en una ruta, switchables por `?variant=1|2|3`. Sin tests, se borra.
**Por qué importa para ti.** El layout de una infografía es una decisión visual: 3 variantes (columnas, timeline, tarjetas) responden "¿cómo se ve?" en minutos. Eliges una, guardas la decisión en ADR, borras el resto.

### Paso 4–5 — `/to-prd` → `/to-issues`
**Concepto.** `/to-prd` sintetiza en un PRD (publica en Linear); `/to-issues` lo parte en **vertical slices** (schema→API→UI→tests, cada uno demo-able).
**Por qué importa para ti.** Slices como `Generar datos estructurados desde KB`, `Render plantilla→PDF`, `Preview + aprobación Gate 3` — cada uno entrega valor solo.

### Paso 6 — `/tdd` + `/ponytail`
**Concepto.** RED→GREEN estricto + Ponytail siempre activo (stdlib/nativo antes que dependencias).
**Por qué importa para ti.** El anti-patrón es un "motor de plantillas" propio o un tokenizer para el word budget. Ponytail lo frena.

```python
# RED
def test_word_budget_no_excede_limite():
    datos = generar_datos_infografia(kb_result, word_budget=120)
    assert contar_palabras(datos) <= 120

def test_infografia_incluye_sources_verificadas():
    datos = generar_datos_infografia(kb_result, word_budget=120)
    assert all(s.verificada_google for s in datos.sources)

# GREEN — ponytail: split() para contar palabras, no un tokenizer custom
def contar_palabras(datos) -> int:
    return len(datos.texto_plano().split())
```
```python
# ponytail: plantilla Jinja2 (o str.format) + weasyprint; NO un render engine propio
# ponytail: dict literal para provenance, no ProvenanceBuilder
```

### Paso 7 — `/ponytail-review`
**Concepto.** Revisa el diff solo por over-engineering (`delete:`, `stdlib:`, `native:`, `yagni:`, `shrink:`); no caza bugs.
**Por qué importa para ti.** Atrapa la clase `InfographicRenderer` con una sola implementación, o el CSS-in-Python que podría ser un `.css` estático.

---

## Referencia rápida — qué skill en qué momento

| Momento | Skill | Tipo |
| :-- | :-- | :-- |
| Explorar decisiones (motor, plantilla) | `/decision-mapping` | user |
| Fijar decisión irreversible | `/grill-with-docs` → ADR | user |
| Probar el layout visual | `/prototype` (UI) | user |
| Formalizar | `/to-prd` → `/to-issues` | user |
| Implementar | `/tdd` + `/ponytail` | model (auto) |
| Antes del PR | `/ponytail-review` | user |
| Onboarding a un concepto | `/teach "grounding y provenance"` | user |

## Definición de listo (DoD)
- [ ] La infografía se genera **grounded** desde la KB, con `sources[]` verificadas.
- [ ] El PDF respeta el `word_budget` y registra `provenance`.
- [ ] Preview + aprobación en el Gate 3 conectados.
- [ ] `CONTEXT.md` con el término *Infografía*.
- [ ] `/ponytail-review` sin hallazgos abiertos.

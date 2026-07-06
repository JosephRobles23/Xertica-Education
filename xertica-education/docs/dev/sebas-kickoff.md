# Kickoff — Sebas · Video

> Cómo llevar tus **primeras tareas** de principio a fin con las 12 skills agénticas.
> Lee primero: [`Skills_Desarrollo_Agentico.md`](../../../Documents/Skills/Skills_Desarrollo_Agentico.md) · [`CONTEXT.md`](../../CONTEXT.md) · [`docs/adr/`](../adr/) · [`architecture.md`](../arquitectura/architecture.md) §5 ("Render híbrido") y §14.

## Tus primeras tareas
1. **Spike — procesamiento de video de larga duración** ([issue #22](../issues/pending/sebas/issue-22-long-video-processing-spike.md)) — viabilidad y costos.
2. **Reutilización de videos existentes** ([issue #19](../issues/pending/sebas/issue-19-existing-video-reuse.md)) — indexar videos largos (~2 h) por **timestamps + transcripciones segmentadas**, sin edición física.

Orden: el **spike** decide si el enfoque de indexación es viable/costeable; recién entonces implementas la **reutilización**. Es tentador saltar al código, pero un spike barato te evita construir sobre una suposición falsa.

> **Idea clave (respétala en el diseño):** "reutilizar sin editar físicamente". El video fuente **no se corta**; un segmento del guion **referencia** un tramo `[t_inicio, t_fin]`. Todo el diseño gira en torno a esa referencia, no a un archivo nuevo.

---

## Tarea 1 · Spike — video de larga duración

### Paso 1 — `/decision-mapping`
**Concepto.** Mapa de tickets con niebla de guerra.
**Por qué importa para ti.** El procesamiento de video largo tiene costos y latencias muy variables (transcripción, storage, egress). Mapear las incógnitas evita un spike que "explora para siempre".

```
> /decision-mapping "Procesamiento de video de larga duración: viabilidad y costo"
```
```markdown
## #1: ¿Costo/latencia de transcribir 2 h? (Whisper local vs API)     Type: Research
## #2: ¿La transcripción trae timestamps por palabra/segmento?         Type: Research
## #3: ¿Cómo indexar tramos para que el guion los referencie?          Type: Prototype · Blocked by #2
## #4–#N: (fog of war)
```

### Paso 2 — `/prototype` (rama Logic)
**Concepto.** Código desechable que responde una pregunta de comportamiento.
**Por qué importa para ti.** "¿La transcripción segmentada me da timestamps usables?" se responde transcribiendo **un** video real de 10 min y mirando la salida. Un script, no un pipeline.

### Paso 3 — `/grill-with-docs` → ADR
**Por qué importa para ti.** El resultado del spike es una decisión de arquitectura (self-host Whisper vs API, formato del índice). Va a ADR para que no se re-discuta.

> **Agente:** "Transcribir en vivo 2 h por cada guion es caro y lento. **Recomendación:** transcribir **una vez** al ingerir el video y guardar el índice `(segmento, t_inicio, t_fin, texto)` como asset reutilizable; el guion consulta ese índice." → **ADR-0006: Índice de transcripción por segmentos como asset reutilizable**.

---

## Tarea 2 · Reutilización de videos existentes

### Paso 1 — `/decision-mapping`
```
> /decision-mapping "Reutilización de video: indexar por timestamps + transcripciones"
```
```markdown
## #1: ¿El índice es una tabla nueva o un jsonb en ASSET.provenance?   Type: Discuss
## #2: ¿Cómo referencia un segmento del guion a un tramo del fuente?    Type: Discuss
## #3: State machine: guion → segmentos → (render generativo | reuso)   Type: Prototype
```

### Paso 2 — `/grill-with-docs`
**Por qué importa.** Aquí se decide dónde vive el índice y cómo se modela la "referencia a tramo". Documentarlo en `CONTEXT.md` mantiene el vocabulario alineado con el Spine.

> **Agente:** "Un segmento reusado no genera un binario nuevo; apunta a un tramo del fuente. ¿Ese segmento es un `ASSET` con `storage_path` vacío + referencia, o un tipo aparte? **Recomendación:** un `ASSET` de tipo `video` con `provenance = {fuente_id, t_inicio, t_fin}` — reutiliza el Spine, no inventa entidad nueva."

Actualiza `CONTEXT.md`:
```markdown
## Segmento reutilizado
Tramo [t_inicio, t_fin] de un video fuente ya existente, referenciado por un
ASSET de tipo video sin render nuevo. Su provenance registra el fuente y el
rango. Convive con los segmentos generados (Veo) en el mismo guion.
```

### Paso 3 — `/prototype` (rama Logic)
Una app de terminal que simula la state machine del guion: para cada segmento decide `reuso` (hay tramo en el índice) o `generativo` (Veo). Prueba la lógica sin renderizar nada.

### Paso 4–5 — `/to-prd` → `/to-issues`
Vertical slices: `Índice de transcripción por segmentos`, `Referencia guion→tramo`, `Concatenación mixta (reuso + generativo) con ffmpeg`.

### Paso 6 — `/tdd` + `/ponytail`
**Por qué importa para ti.** El anti-patrón es "cortar" el video físicamente. Ponytail te empuja a **referenciar**, y a usar `ffmpeg` (ya en el stack de render) en vez de una lib nueva.

```python
# RED
def test_segmento_reusado_referencia_tramo_sin_render():
    seg = planificar_segmento(guion_item, indice)
    assert seg.modo == "reuso"
    assert seg.provenance == {"fuente_id": "v1", "t_inicio": 120.0, "t_fin": 138.5}

# GREEN — ponytail: dict de provenance, no clase ReuseStrategy
def planificar_segmento(item, indice):
    tramo = indice.buscar(item.texto)          # match por transcripción
    if tramo:
        return Segmento(modo="reuso", provenance={
            "fuente_id": tramo.fuente_id, "t_inicio": tramo.t0, "t_fin": tramo.t1})
    return Segmento(modo="generativo", provenance={"modelo": "veo-3.1"})
```
```python
# ponytail: ffmpeg -ss/-to para extraer al concatenar; NO editar/re-encodear el fuente entero
```

### Paso 7 — `/ponytail-review`
Caza el `VideoSegmentManager` con estado que podría ser una función pura, o el re-encode innecesario del video completo.

---

## Referencia rápida — qué skill en qué momento

| Momento | Skill |
| :-- | :-- |
| Acotar el spike | `/decision-mapping` |
| Medir costo/latencia real | `/prototype` (Logic) |
| Fijar decisión (índice, self-host vs API) | `/grill-with-docs` → ADR |
| Modelar la state machine | `/prototype` (Logic) |
| Formalizar | `/to-prd` → `/to-issues` |
| Implementar | `/tdd` + `/ponytail` |
| Antes del PR | `/ponytail-review` |

## Definición de listo (DoD)
- [ ] Spike: reporte con viabilidad, costos y enfoque recomendado.
- [ ] Un segmento del guion referencia un tramo (timestamp) de un video fuente **sin render nuevo**.
- [ ] `provenance` registra `fuente_id`, `t_inicio`, `t_fin`.
- [ ] `CONTEXT.md` con el término *Segmento reutilizado*.
- [ ] `/ponytail-review` sin hallazgos abiertos.

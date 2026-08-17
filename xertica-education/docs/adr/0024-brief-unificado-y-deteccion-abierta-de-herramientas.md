# ADR-0024: Brief unificado, jerarquía de esqueleto y detección abierta de herramientas

- **Estado:** Aceptado
- **Fecha:** 2026-08-17
- **Deciden:** Joseph Robles · sesión de grilling con Claude Code
- **Ámbito:** `services/route_structurer/`, `services/research/`, `prompts/{route_structurer,research}.py`, `adapters/llm/openrouter.py`, `config/settings.py`, frontend `modules/new-route/NuevaRuta.tsx`
- **Relación:** **enmienda parcialmente** [ADR-0014](0014-structure-generation-llm.md) (material-first) · **matiza** [ADR-0011](0011-deep-research-without-pre-generation-gate.md) y mantiene intactas las políticas de verificación de [ADR-0016](0016-approved-research-sources.md) y [ADR-0017](0017-deep-research-source-review-policy.md).
- **Mapa de decisiones:** `docs/decisions/nueva-ruta-vendor-neutral-decision-map.md`

## Contexto

El producto debe generar rutas de aprendizaje de **cualquier ámbito**, pero la Estructura
Propuesta salía sistemáticamente sesgada al stack de Google. La auditoría del código encontró
cuatro causas concretas, ninguna de ellas un system prompt explícito:

1. **La estructura pegada por el usuario nunca llegaba al LLM.** `UploadStructureDialog.tsx`
   construía `{ name, kind: 'texto' }` sin el texto, y `NuevaRuta.tsx` no tenía rama de subida
   para ese `kind`. El modelo generaba desde el brief con `parsed_docs` vacío.
2. **Aliases genéricos en `TOOL_REGISTRY`** (`services/research/service.py`): `"prompt"`,
   `"imagen"`, `"datos"`, `"razonamiento"`, `"diseño"` matchean casi cualquier brief en español
   por substring, activando Gemini / Nano Banana / BigQuery sin que el usuario los mencionara.
3. **Fallback duro a Gemini**: sin herramientas detectadas, `run()` asignaba
   `tools = [TOOL_REGISTRY[2]]` — era imposible que el research *no* propusiera Google.
4. **Fallo silencioso del LLM**: el adapter OpenRouter devolvía un mock ante cualquier error
   HTTP o timeout; el Job moría `failed` sin motivo y la UI mostraba la propuesta enlatada.

Además, el modelo configurado (`gpt-4o-mini`) no correspondía con el documentado en ADR-0014
(Haiku 4.5), y el truncado de material a 12.000 caracteres cortaba estructuras largas.

## Decisión

### 1. Brief unificado y jerarquía de esqueleto (enmienda a ADR-0014)

La página Gate 0 pasa a tener **un solo campo de texto** que acepta el objetivo, una estructura
completa, o ambos; todo viaja en el campo `brief` existente. En consecuencia, el
material-first de ADR-0014 se sustituye por esta jerarquía explícita, codificada en el system
prompt del `route_structurer`:

1. Si el **brief** contiene una estructura reconocible (módulos, lecciones, numeración,
   headers), esa estructura es el esqueleto y se respeta fielmente.
2. Si no, el esqueleto es la estructura presente en el **material** subido (`parsed_docs`).
3. Si no hay ninguna, se **propone** una desde el objetivo, usando el material como contexto.

Racional: escribir o pegar en el campo principal es el acto más deliberado del usuario;
subordinarlo a un documento adjunto producía exactamente el bug de UX que motivó este ADR.

La fidelidad se garantiza **a nivel de módulo y tema**, no de lección individual: el dominio
vigente admite un máximo de 8 módulos y no permite componentes repetidos del mismo tipo dentro
de un módulo (`normalize.py`). Las lecciones de un módulo fuente se resumen en el `summary` de
su componente `lesson`, y un módulo demasiado denso puede dividirse en dos. Permitir N
componentes del mismo tipo por módulo queda **fuera de alcance** — sería un cambio de dominio
con impacto en costos de generación y merece su propio ADR.

`_MAX_DOC_CHARS` sube de 12.000 a 40.000 caracteres por documento.

### 2. Modelo `gemini-3.6-flash` y fallo honesto

El rol `route_structurer` pasa a `google/gemini-3.6-flash` vía OpenRouter (1M de contexto, que
es lo que hace innecesario el truncado agresivo) con timeout de 90 s.

`OpenRouterLLMAdapter.chat_completion` acepta `strict=True`: en ese modo, un error HTTP, un
timeout o un `content` vacío **lanzan una excepción con el motivo real** en lugar de devolver
el mock. El `route_structurer` lo usa; el resto de roles (`lesson_generator`, `quiz_generator`,
`lab_generator`, `scriptwriter`) conservan el comportamiento tolerante actual. El motivo llega
a `job.error` y de ahí a la UI, que ya soporta el estado `failed` con "Regenerar".

### 3. Detección abierta de herramientas, verificación por allowlist

La detección de herramientas del deep research pasa a dos capas:

1. **Detección abierta con LLM** (rol `researcher`, hasta ahora declarado sin llamador): un
   prompt pide las herramientas *explícitamente mencionadas* en el brief y los módulos, como
   conjunto abierto (Excel, Figma, SAP, ChatGPT o lo que sea), prohibiendo inferir o sugerir
   herramientas no nombradas.
2. **Fallback determinista**: si no hay LLM disponible, falla, o devuelve JSON inválido, se usa
   el matching por aliases del `TOOL_REGISTRY` — ahora **podado** de términos genéricos, solo
   nombres reales de producto.

El `TOOL_REGISTRY` deja de ser la fuente de detección y pasa a ser **capa de verificación**:
una herramienta detectada que está registrada obtiene sus canales, dominios y fuentes oficiales
verificadas; una que no lo está busca fuentes por YouTube/Tavily y degrada a `requires-review`
—el estado que ADR-0017 ya define para revisión humana. Se elimina el fallback forzado a
Gemini: sin detección, `detected_tools` es una lista vacía.

El texto sobre el que se detecta se reduce a `route_name + brief + módulos` más `industry`,
`area` y `audienceLevel`; antes se concatenaban todos los valores del `customerContext`,
incluida la URL del cliente, generando falsos positivos.

**Las políticas de verificación de ADR-0016 y ADR-0017 no cambian**: allowlist de dominios y
canales, auto-aprobación por `relevanceScore`, y tope de fuentes en revisión manual siguen
exactamente igual. Lo que cambia es qué herramientas entran al pipeline.

## Consecuencias

- **+** La estructura que el usuario pega se respeta; desaparece la brecha que descartaba su
  trabajo en silencio.
- **+** El contenido deja de sesgarse a Google: sin aliases genéricos, sin fallback forzado y
  con detección basada en lo que el usuario realmente escribió.
- **+** Los fallos del LLM son visibles y accionables en vez de degradarse a contenido enlatado.
- **+** El contexto de 1M tokens permite briefs y materiales largos sin truncado destructivo.
- **−** Una llamada LLM adicional por deep research (coste marginal en Flash) y dependencia de
  que el modelo respete la instrucción de no inferir herramientas; el fallback determinista
  cubre el caso de fallo.
- **−** La fidelidad a nivel lección sigue sin ser posible; se documenta como limitación
  conocida hasta que exista el ADR de dominio correspondiente.
- **~** ADR-0014 sigue vigente en todo lo demás (Job en background, `normalize.py`, ciclo de
  vida de Gate 0); solo se enmienda su regla de precedencia material-first.

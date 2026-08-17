# Plan técnico — Nueva Ruta vendor-neutral + brief unificado

> **Para el implementador.** Este documento es autocontenido: no necesitas la conversación que
> lo originó. Las decisiones y su racional están en
> `docs/decisions/nueva-ruta-vendor-neutral-decision-map.md`.
>
> **Estado:** listo para ejecutar. Nada de esto está implementado.

---

## 0. Contexto operativo del repo

Monorepo `xertica-education/` — pnpm workspaces + Turborepo. Lee **`CONTEXT.md`** (lenguaje
ubicuo: Ruta, Gate, Job, KB, Componente, Asset) y **`AGENTS.md`** (protocolo obligatorio) antes
de tocar dominio.

```bash
# Frontend (apps/web · Next.js 14 App Router + Tailwind 4 + shadcn)
pnpm --filter xertica-education-web typecheck
pnpm --filter xertica-education-web dev

# Backend (apps/api · FastAPI con uv, NO venv+pip)
cd apps/api && uv run pytest -q
cd apps/api && uv run python verify_boot.py
cd apps/api && uv run uvicorn main:app --reload --port 8000
```

**Reglas no negociables:**

- **TDD red-green** en el backend. Los tests van primero.
- **No cambies contratos de API.** Este plan no requiere ninguno: `brief` y `customerContext`
  ya viajan como texto/dict libre, y el shape de `route.modules` y de `run()` del research no
  se tocan.
- **No toques `normalize.py`** ni los enums de dominio (`ModuleType`, `ComponentType`).
- **Higiene de secretos:** nunca commitear `.env` ni claves; `git add` con rutas explícitas;
  **no hacer push** salvo petición explícita del usuario.
- **Reporta con honestidad:** si un test falla o un paso se omite, dilo con la evidencia.

**Problema que resolvemos (evidencia en el código actual):**

| Síntoma | Causa |
| :-- | :-- |
| La estructura pegada se ignora | `UploadStructureDialog.tsx:74-77` crea el objeto sin el texto; `NuevaRuta.tsx` no tiene rama `kind === 'texto'` |
| Contenido sesgado a Google | `research/service.py:11-92` aliases genéricos ("prompt", "imagen", "datos") + `:545-547` fallback duro a Gemini |
| Estructura pobre | `settings.py:75` usa `gpt-4o-mini` |
| Fallos invisibles | `adapters/llm/openrouter.py:60` cae a mock en silencio → Job `failed` sin motivo |

---

## WP0 — ADR-0024

**Archivo:** `docs/adr/0024-brief-unificado-y-deteccion-abierta-de-herramientas.md`
(0024 es el siguiente número libre; formato del template `docs/adr/0000-template.md`).

Contenido: decisiones **6, 8 y 11** del decision map.

- Declara la **enmienda parcial a ADR-0014**: el material-first pasa a jerarquía
  `estructura en el brief > estructura en documentos > proponer desde el objetivo`. No edites
  el 0014 (los ADRs aceptados no se editan) — refiérelo y matízalo.
- Declara el cambio de política de **detección** de herramientas respecto a ADR-0011/0016/0017:
  la verificación por allowlist se mantiene intacta; solo cambia cómo se detectan las
  herramientas candidatas.
- Registra el cambio de modelo del structurer y la política de fallo honesto.

De paso: actualiza `docs/adr/README.md`, que no lista 0019 ni 0021-0023.

**Done:** el ADR existe, referencia 0014/0011/0016/0017 y el README está al día.

---

## WP1 — Backend: structurer

**Tests primero:** `apps/api/tests/test_route_structurer.py` (100 líneas). Patrón existente:
pytest plano (funciones `test_*`, sin clases), corrutinas con `asyncio.run(...)`,
`class _FakeLLM(BaseLLMAdapter)` (L63-69) que assertea `role == "route_structurer"` y devuelve
un string canned. Añade casos: brief con estructura → módulos fieles; fallo del LLM →
excepción con motivo (no mock).

### 1.1 `apps/api/config/settings.py` (L74-79)

```python
model_names: Dict[str, str] = {
    "route_structurer": "gemini-3.6-flash",
    "researcher": "gemini-3.6-flash",   # rol ya declarado, hasta ahora sin llamador
    ...
}
```

### 1.2 `apps/api/adapters/llm/openrouter.py`

- `_map_model_name` (L62-71): añade `"gemini-3.6-flash": "google/gemini-3.6-flash"`.
- `chat_completion` (L12): acepta `strict: bool = False` y `timeout: float = 30.0` como
  parámetros propios (extráelos de kwargs antes de pasar el resto al payload — hoy hace
  `**kwargs` directo al body de OpenRouter en L31).
- Con `strict=True`, ante error HTTP, timeout o `content` vacío: **lanza** `RuntimeError` con el
  motivo real (status + texto de respuesta, o el mensaje de la excepción) en lugar de
  `_get_mock_response` (L60). Con `strict=False` el comportamiento actual se conserva —
  `lesson_generator`, `quiz_generator`, `lab_generator` y `scriptwriter` no deben cambiar.

### 1.3 `apps/api/services/route_structurer/service.py`

- `_MAX_DOC_CHARS = 40_000` (L15; Gemini 3.6 Flash tiene 1M de contexto).
- La llamada (L26) pasa `strict=True, timeout=90.0`.
- `_build_prompt` (L37-52): añade `empresa` al bloque CONTEXTO leyendo
  `ctx.get("companyName")`. Mantén el resto del formato.

### 1.4 `apps/api/prompts/route_structurer.py` — reescritura del `SYSTEM_PROMPT`

Mantén **intacto** el JSON schema de salida (normalize.py depende de él). Cambia las reglas:

- **Jerarquía explícita:** si el BRIEF contiene una estructura reconocible (módulos, lecciones,
  numeración, headers), esa estructura es el esqueleto y se respeta fielmente; si no, usa la
  estructura del MATERIAL; si no hay ninguna, propón desde el objetivo.
- **Regla de fusión (límites del dominio):** máximo 8 módulos; dentro de un módulo no puede
  repetirse un tipo de componente. Si un módulo fuente tiene varias lecciones, resúmelas todas
  dentro del `summary` del componente `lesson`; si es demasiado denso, divídelo en dos módulos
  en vez de perder contenido.
- **Neutralidad:** quita el ejemplo `"Nano Banana para Marketing"` → uno neutral
  (p. ej. `"Ventas Consultivas B2B"`). No menciones productos ni vendors salvo que aparezcan
  en el brief o el material.

### 1.5 `apps/api/services/route_structurer/mock.py`

Elimina la inyección `" con Google Workspace"` (L18, usada en L29 y L41).

### 1.6 Motivo del fallo visible

En `apps/api/routers/learning_paths.py`, `_run_structure_job`: verifica que el `except` propague
`str(exc)` al campo de error del Job (ya marca `failed` por ADR-0014; solo asegura el mensaje).

**Done:** tests verdes; un fallo del LLM produce un Job `failed` con motivo legible; ningún otro
rol cambia de comportamiento.

---

## WP2 — Backend: research vendor-neutral

**Tests primero:** nuevo `apps/api/tests/test_research_tool_detection.py`. Patrón de
`test_approved_research_sources.py`: fakes duck-typed inyectados en el constructor
(`ResearchService(youtube_client=..., documentation_client=..., llm=...)`). Cubre: detección con
LLM fake; fallback determinista sin LLM; que "prompt"/"imagen"/"datos" **ya no** disparan
herramientas Google; que sin detección `detected_tools == []`.

### 2.1 `apps/api/services/research/service.py`

- **Poda de aliases** en `TOOL_REGISTRY` (L11-92): elimina los genéricos — `"imagen"`, `"foto"`,
  `"multimedia"`, `"video generation"`, `"teaser"`, `"identidad visual"`, `"datos"`, `"data"`,
  `"analytics"`, `"prompt"`, `"razonamiento"`, `"diseño"`, `"design"`. Deja solo nombres reales
  de producto y sus variantes (`"veo"`, `"veo 3"`, `"nano banana"`, `"gemini"`, `"ai studio"`,
  `"bigquery"`, `"canva"`).

- **`detect_tools`** (L213-219) pasa a dos capas:
  1. **Detección abierta con LLM** (si hay `llm` inyectado y la key no es placeholder): nuevo
     `detect_tools_prompt(text)` en `apps/api/prompts/research.py` que pide un JSON array
     `[{"tool": str, "vendor": str|null}]` con las herramientas *explícitamente mencionadas* en
     el brief y los módulos — prohibido inferir o sugerir herramientas no nombradas. Se invoca
     con `chat_completion(role="researcher", ...)`.
  2. **Fallback determinista**: el matching por aliases podados (comportamiento actual). Se usa
     si no hay LLM, si falla o si devuelve JSON inválido. Esto mantiene los tests sin red.

  Luego cruza el resultado con `TOOL_REGISTRY`: match → herramienta registrada (canales,
  dominios y fuentes oficiales); sin match → herramienta abierta (vendor del LLM, sin canales)
  cuyas fuentes se buscan por YouTube/Tavily y salen `requires-review`.

- **Inyección:** nuevo parámetro opcional `llm=None` en `ResearchService.__init__`;
  `apps/api/config/dependencies.py:67-68` lo construye con `OpenRouterLLMAdapter` cuando
  `settings.openrouter_key` es real.

- **Elimina el fallback forzado a Gemini** (L545-547: `tools = [TOOL_REGISTRY[2]]`). Sin
  herramientas detectadas, el research corre con las tecnologías/tema del brief y devuelve
  `detected_tools: []`.

- **Haystack de detección** (L541-542): hoy concatena `str(v) for v in customer_context.values()`
  — mete la URL del cliente y valores no textuales, generando falsos positivos. Redúcelo a
  `route_name + brief + modules` más `industry`, `area` y `audienceLevel`.

- **El shape de retorno de `run()` no cambia.** `detected_tools` ya admite `vendor: None` y el
  frontend solo lee `.tool` para un toast (`RouteDetail.tsx:769`,
  `EstructuraPropuesta.tsx:288`).

**Done:** tests verdes; un brief de "prompting para bodegas" no detecta Gemini; un brief que
menciona Excel y Figma los detecta con `requires-review`.

---

## WP3 — Frontend: rediseño de la página

Verifica al cerrar con `pnpm --filter xertica-education-web typecheck`.

### 3.1 `apps/web/src/shared/lib/types.ts` (L200-221)

- `CustomerArea` → `string` (las 6 áreas quedan como sugerencias en la página).
- Elimina `GoogleWorkspaceUsage` y, de `CustomerContext`, los campos `usesGoogleWorkspace`,
  `url`, `inferredFrom` y `companyProposalFile`.
- **Efecto colateral:** `modules/video/Storyboard.tsx:212` usa `route.customerContext?.url` como
  fallback → déjalo en `route.sources.find(s => s.url)?.url ?? ''`.

### 3.2 `apps/web/src/shared/store/index.tsx`

Elimina `UploadedStructure` (L64-69) y su estado (L150-151, L254, L625, L641). No se envía al
backend en ningún sitio, así que no hay más consumidores que la propia página.

### 3.3 Elimina `apps/web/src/modules/new-route/components/UploadStructureDialog.tsx`

### 3.4 `apps/web/src/modules/new-route/NuevaRuta.tsx` — reescritura de la vista

Conserva la lógica de submit (L305-462: crear ruta, subir documentos, disparar
`generate-structure`, `setStructureJobId`, redirección a `/estructura-propuesta`) salvo lo que
se indica. Orden visual **hero-first**:

1. **Hero — textarea único** "Describe tu ruta de aprendizaje" (8-10 filas). Placeholder que
   invita a pegar el objetivo, la estructura completa, o ambos. Sigue viajando como `brief`
   (L321) — sin cambio de contrato.
2. **Badge de detección** — función pura local, sin LLM:
   `detectStructureHint(text)` cuenta líneas que matchean
   `/^(#{1,4}\s|m[óo]dulo\s+\d|lecci[óo]n\s+\d|\d+[.)]\s)/i`; con ≥3 muestra
   "✓ Estructura detectada (~N módulos) · la respetaremos como esqueleto". Si no detecta nada,
   **no muestra nada** (no molestar con negativos).
3. **Material de apoyo (opcional)** — zona única multi-archivo Drive/local que reemplaza los
   tres flujos actuales (estructura L328-358, propuesta de compañía L362-394, material
   L396-428). Todo sube por `api.uploadDocument` / `api.uploadDriveDocument`; el backend ya los
   trata igual (`documents` → `parsed_docs`).
4. **Contexto de la compañía** — bloque colapsable **plano** de 4 campos: Industria (input),
   Área (chips sugeridos + input libre), Audiencia (input), Empresa (input). Mueren
   `CUSTOMER_STEPS` (tabs), `WORKSPACE_OPTIONS`, el campo URL, y toda la lógica de inferencia
   (`inferFromText` L64-84, `inferFromUrl` L86-102, `inferCustomerContext` L158-183 y su botón).
   `compactCustomerContext` (L104-120) se reduce a los campos vivos: `industry`, `area`,
   `audienceLevel`, `companyName`, `baseMaterialFile`.
5. **Toggle deep research** — mismo comportamiento; copy vendor-neutral: "Detecta las
   herramientas mencionadas en tu material y propone videos, documentación y fuentes
   verificadas". Sin nombrar productos.
6. **CTA** "Proponer estructura con IA".

Mantén el sistema visual existente (tokens Tailwind 4 + primitivas shadcn ya importadas). La
mejora de UX viene de jerarquía, espaciado y microcopy, no de librerías nuevas.

**Done:** `typecheck` limpio; la página cabe en una pantalla; pegar una estructura muestra el
badge; no queda ninguna mención a Google Workspace ni a productos concretos en el copy.

---

## WP4 — Verificación end-to-end

```bash
cd /home/user/Projects/Xertica-Education/xertica-education
pnpm --filter xertica-education-web typecheck
cd apps/api && uv run pytest tests/test_route_structurer.py tests/test_research_tool_detection.py tests/test_approved_research_sources.py -q
cd apps/api && uv run python verify_boot.py
```

**Smoke manual** (con la API y la web levantadas):

| Caso | Esperado |
| :-- | :-- |
| Pegar el curso "Tu primer aliado con IA" (intro + 3 módulos + diagnóstico/cierre) | La propuesta refleja esos módulos y temas; las lecciones 3.1-3.5 aparecen resumidas en el summary del componente lesson; sin herramientas Google no mencionadas |
| Brief corto sin estructura ("quiero enseñar atención al cliente en una veterinaria") | Propone una estructura coherente desde el objetivo |
| Brief que menciona "Excel y Figma" con deep research activo | `detected_tools` los incluye; no aparece Gemini forzado; las fuentes no registradas quedan `requires-review` |
| Cortar la red / key inválida durante la generación | Job `failed` con el motivo real visible, no propuesta enlatada |

---

## Resumen de archivos

**Nuevos:** `docs/adr/0024-*.md` · `apps/api/tests/test_research_tool_detection.py`

**Modificados (backend):** `config/settings.py` · `adapters/llm/openrouter.py` ·
`services/route_structurer/{service,mock}.py` · `prompts/route_structurer.py` ·
`prompts/research.py` · `services/research/service.py` · `config/dependencies.py` ·
`routers/learning_paths.py` (solo el mensaje de error del job) · `tests/test_route_structurer.py`

**Modificados (frontend):** `shared/lib/types.ts` · `shared/store/index.tsx` ·
`modules/new-route/NuevaRuta.tsx` · `modules/video/Storyboard.tsx` (una línea)

**Eliminados:** `modules/new-route/components/UploadStructureDialog.tsx`

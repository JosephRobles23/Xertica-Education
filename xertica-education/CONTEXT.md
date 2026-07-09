# CONTEXT — Xertica Education

> Documento de dominio único del repositorio (single-context). Los skills de ingeniería y los agentes deben leer este archivo **antes de explorar o modificar código** (ver `docs/agents/domain.md`). Usa el vocabulario definido aquí en issues, PRs, tests y nombres de símbolos; no derives a sinónimos.

---

## 1. Qué es el producto

Xertica Education es una plataforma que **orquesta la generación asistida por IA de rutas de aprendizaje** (currículos) y sus assets multimedia. Un diseñador instruccional describe un tema; el sistema propone una estructura curricular, la persona la aprueba en *gates* de control, y luego pipelines generan lecciones, quizzes, infografías, guías de laboratorio y videos.

El flujo humano-en-el-loop está gobernado por **compuertas de aprobación (Gates)**: la IA propone, un humano aprueba, y solo entonces se desbloquea la siguiente fase.

---

## 2. Lenguaje ubicuo (glosario)

Términos canónicos. En el dominio se usa el español (**Ruta**, **tema**, **brief**); en código conviven con nombres en inglés (`LearningPath`, `RouteService`). Ambos apuntan al mismo concepto.

| Término (dominio) | En código | Definición |
| :--- | :--- | :--- |
| **Ruta / Learning Path** | `LearningPath`, `RouteService`, `learning_paths` | Currículo completo sobre un tema. Raíz del *Spine*. |
| **Tema** | `tema` | Asunto sobre el que se genera la ruta (payload de creación). |
| **Brief** | `brief` | Descripción/intención libre que el usuario da al crear una ruta. |
| **Contexto del Cliente** | `CustomerContext`, `customerContext` | Información capturada o inferida al crear cada Ruta y utilizada durante toda la generación para adaptar sus contenidos a las necesidades del cliente. Pertenece a esa Ruta; no representa un perfil de Cliente reutilizable independiente. Sus datos orientan prompts y filtros, pero no constituyen evidencia para la KB; el material base aportado por el cliente sí ingresa como Fuente. |
| **Estructura / Currículo propuesto** | `generate-structure`, `WorkflowService` | Árbol de módulos y componentes que la IA propone y que el humano revisa en `/estructura-propuesta`. |
| **Módulo** | `models/domain/module.py`, `modules` | Bloque de una ruta (`tipo`: intro/capsula/lab/evaluacion/cierre) con orden y duración objetivo. |
| **Componente** | `models/domain/component.py`, `components` | Pieza de contenido de un módulo: `lesson`/`video`/`lab`/`infografia`/`quiz`. |
| **Asset** | `models/domain/asset.py`, `assets` | Artefacto materializado de un componente, con `estado` de aprobación, `storage_path`, `word_budget`, `provenance`. |
| **AssetVersion** | `models/domain/asset_version.py`, `asset_versions` | Versión histórica de un asset. |
| **Source / Fuente** | `models/domain/source.py`, `sources` | Candidato encontrado por Deep Research o material subido. Las URLs documentales autorizadas se consolidan en `approved_research_sources`; YouTube se vincula al Video Asset; solo los uploads Vía 2 alimentan la KB. |
| **Approved Research Source** | `approved_research_sources` | URL documental autorizada para generación. Puede aprobarse automáticamente por allowlist o manualmente durante revisión. El agente la consume directamente; nunca se inserta en la KB ([[docs/adr/0016-approved-research-sources]]). |
| **asset_sources** | `asset_sources` | Tabla puente M:N entre `assets` y `sources` para la citación (Fase 5-6). Corrige el 1:N de ADR-0005. |
| **source_module_links** | `source_module_links` | Vinculación **Source↔Módulo**: qué fuente (típicamente un video de Vía 1) corresponde a qué módulo de la ruta. `origin` distingue `heuristic` (default, frontend) de `llm` (Job on-demand). La heurística de `RouteDetail` es el fallback client-side; solo el linker LLM persiste filas ([[docs/adr/0012-vinculacion-source-modulo-hibrida]]). |
| **Document (Vía 2)** | `documents`, `adapters/parser/` | Archivo(s) que sube el usuario (PDF/Office). Una ruta admite **múltiples**. Se guarda en Storage y se **parsea a Markdown verbatim en el momento del upload** (`parsed_md`, [[docs/adr/0013-parse-at-upload-parsed-md]]). Por default **siempre** genera un `Source` Vía 2 (`origin='upload'`) e ingesta a la KB; `use_as_source` queda deprecado (siempre true). El `parsed_md` alimenta además el contexto de `generate-structure` ([[docs/adr/0008-document-parsing-via2-ingestion]]). |
| **KB (Knowledge Base)** | `services/kb/`, puerto `KnowledgeBase` | Base de conocimiento RAG construida a partir de las fuentes **de Vía 2** (documentos con texto fiel); alimenta la generación de contenido. Puerto intercambiable ([[docs/adr/0006-kb-rag-ingestion-embeddings]]). |
| **Chunk** | `kb_chunks`, `chunk` | Fragmento de una fuente (parseada a Markdown) que se embebe e indexa en pgvector. Chunking **estructural** ~500 tokens / ~64 solape. |
| **Embedding** | `Embedder`, `text-embedding-3-small` | Vector de **1536 dim** (OpenAI) que representa un chunk; métrica **coseno** (HNSW). Adapter real + `MockEmbedder`. |
| **Grounding / Cita** | `KnowledgeBase.query`, `GroundedChunk` | Resultado de búsqueda con su fuente (`source_id`, título, url, snippet, score, `verificada_google`) que ancla la generación. |
| **Ingesta RAG** | `KnowledgeBase.ingest`, Job | parse → chunk → embed → upsert en `kb_chunks`, como **Job asíncrono** disparado tras Gate 1. Corpus = **solo uploads (Vía 2)**; reutiliza `documents.parsed_md` sin re-parsear ([[docs/adr/0011-kb-solo-via2-linking-por-modulo]]). |
| **Video Asset Renderizado** | `assets.tipo = video`, `storage_path` | Video final de un componente de tipo `video`. Su fuente de verdad es el Asset persistido en Supabase; el estado del navegador/localStorage solo puede actuar como caché temporal para reanudar o mostrar progreso. |
| **Video Asset Externo** | `assets.tipo = video`, `provenance` | Video externo, por ejemplo de YouTube, que se recomienda para un Componente `video` y, al ser aceptado, satisface ese Componente como su Asset final sin copiar ni renderizar el archivo. Se persiste su URL y procedencia; no es una Fuente para la KB. |
| **Plan de Render / Render Plan** | `RenderPlan`, `render_plan` | Especificación declarativa de las operaciones y sus entradas/salidas necesarias para producir un Video Asset Renderizado a partir de un Storyboard. Separar el plan de su ejecución permite cambiar el orquestador (determinista hoy, grafo/agente mañana) sin reescribir la lógica de cada etapa. |
| **Etapa de Render / Render Stage** | `RenderStage` | Operación atómica dentro de un Render Plan (por ejemplo: síntesis de narración, generación de visual, composición, mezcla de audio). |
| **Ejecutor de Render / Render Executor** | `RenderExecutor` | Componente responsable de ejecutar un Render Plan etapa por etapa de forma determinista. Hoy es código propio; mañana podría ser un grafo de LangGraph/ADK sin cambiar el contrato del plan. |
| **Job** | `JobsService`, `/jobs` | Unidad de trabajo asíncrona con estado y progreso. Toda generación pesada corre como job y se consulta por *polling*. |
| **Gate (Compuerta)** | ver §3 | Punto de aprobación humana que transiciona el estado de la ruta y desbloquea la siguiente fase. |
| **Storyboard** | `/ruta/:id/video-storyboard` | Guion visual del video antes de renderizar. |
| **Render Target** | `route_id` + `module_id` + `component_kind` | Identidad de dominio que indica a qué Componente pertenece un render de video antes de resolver o crear el `component_id` persistido. |
| **Tipo Visual / Visual Type** | `VideoScene.visual_type` (Literal con 14 valores) | Categoría de escena visual en un Storyboard. El vocabulario se expandió de 5 tipos heredados a 14 tipos alineados con los escenarios de Remotion (ver ADR-0009). Incluye `text_card`, `hero_title`, `stat_card`, `callout`, `comparison`, `bar_chart`, `line_chart`, `pie_chart`, `kpi_grid`, `progress_bar`, `terminal_scene`, `screenshot_scene`, `ai_video`, `ai_illustration`. |
| **Pacing dinámico** | `SCRIPTWRITER_SYSTEM_PROMPT` | Regulación del tiempo en pantalla adaptada a la complejidad del visual (ej. títulos cortos de 3s, terminales detalladas de 12s) gobernada por la extensión de la narración por escena (ver ADR-0012). |
| **Subtítulos / Captions** | `edit_decisions.captions` | Palabra destacada con timing word-level, renderizada por Remotion CaptionOverlay. El timing se extrae de la respuesta de Google Cloud TTS (`timepoints`), no de un transcriber externo. |
| **OpenMontage** | `openmontage/` (git submodule) | Repositorio externo (github.com/calesthio/OpenMontage) que provee herramientas Python de audio/música/composición y el proyecto Remotion `remotion-composer/`. Integrado como submódulo (ADR-0010), no como dependencia pip. Solo el equipo de video lo conoce. |
| **Biblioteca** | `/biblioteca` | Catálogo de rutas/assets ya producidos. |
| **Infografía** | `InfographicService`, `infografia` | Componente visual generado directamente como imagen PNG por `gpt-image-2` infiriendo colores y logo de marca de la compañía objetivo, y luego envuelto en un PDF de una página. |

### Estados de un Job
`queued` → `running` → (`rendering`) → `completed` | `failed`

### El *Spine* (jerarquía de dominio · [[docs/adr/0005-full-spine-schema]])
`Ruta → Módulo → Componente → Asset → { Source, AssetVersion }`. Es el modelo compartido que leen/escriben las 4 features; se implementa completo en `supabase/migrations` aunque el MVP cargue una sola ruta.

### Estados de una Ruta (LearningPath)
`borrador` → `en-revision` (tras Gate 0 · `/approve`) → `generado` (tras Gate 1 · `/sourcing/approve`) → `aprobado`.

> **Split de `estado` (ADR-0005):** hoy la Ruta lleva un vocabulario de *aprobación* (el `ContentStatus` del frontend) — es **interino**. En el Spine, la aprobación vive en el **Asset** (`draft`/`generado`/`en_revision`/`aprobado`) y la Ruta debería llevar un *ciclo de vida* (`borrador`/`en_produccion`/`publicada`). La migración a ese split requiere desacoplar `RouteStatus` del `ContentStatus` en el frontend (contrato de API) y queda como deuda registrada.

---

## 3. Gates (compuertas de aprobación humana)

| Gate | Momento | Transición / efecto |
| :--- | :--- | :--- |
| **Gate 0 — Aprobación de currículo** | Tras proponer la estructura | `borrador → en-revision`; desbloquea las siguientes fases. Endpoint `POST /learning-paths/{id}/approve`. |
| **Gate 1 — Sourcing** | Antes de ingestar KB | `en-revision → generado`; aprueba las fuentes recopiladas. Endpoint `POST /learning-paths/{id}/sourcing/approve`. |
| **Gate 3 — Revisión de assets (E2E)** | Antes de publicar | Revisión final de los assets generados de punta a punta. |

---

## 4. Arquitectura de contexto (bounded context)

Es un **repo de contexto único**: un solo `CONTEXT.md` en la raíz. Decisiones arquitectónicas se documentan como ADRs bajo `docs/adr/` (créalos de forma perezosa cuando una decisión se resuelva; ver `docs/agents/domain.md`).

Backend organizado por **capacidades desacopladas**, no por capas técnicas monolíticas:

```
Contracts (DTO) ──> Models (domain) ──> Services ──> Routers ──> Workflows
                                            │
                             Repositories (persistencia)
                             Adapters (llm / storage / parser / renderer)
```

- **Services** encapsulan una capacidad de negocio. El patrón esperado por servicio es `interface.py` + `service.py` + `mock.py` (contrato, implementación real, implementación simulada).
- **Adapters** aíslan lo externo por capacidad: `llm/`, `storage/`, `parser/`, `renderer/`.
- **Models** separan `domain/` (modelo de negocio) de `dto/` (contratos HTTP de entrada/salida).

---

## 5. Reglas de oro del MVP (invariantes de dominio)

Estas reglas gobiernan cómo se construye, y son parte del contrato del dominio:

1. **Ninguna feature bloquea a otra.** Si una dependencia no está lista, devuelve datos *mock* o *placeholder* que **cumplan el contrato**. De ahí que cada servicio tenga su `mock.py`.
2. **No cambies un contrato de API sin discutirlo primero.** Cambiar la implementación interna detrás de un contrato existente es libre; cambiar el contrato (DTO/endpoint) requiere pausar y acordar.
3. **Trabajar de izquierda a derecha:** `Contracts → Models → Endpoints → Frontend → IA real`. Primero el esqueleto determinista con mocks, la IA real al final.

---

## 6. Contradicciones conocidas (a corregir, no a imitar)

El `README.md` y el doc de arquitectura describen partes **aspiracionales** que aún difieren del código real. La verdad de campo es:

- El frontend es **Next.js 14 (App Router) + React 18 + Tailwind 4 + shadcn/ui (Radix)**, modular por feature (`src/app` routing · `src/modules/*` · `src/shared/*`). El gestor de paquetes es **pnpm**. El README dice "Next.js 15" (versión aproximada, ok).
- No existe (aún) la carpeta `packages/` con workspaces compartidos que mencionan el README y el doc de arquitectura.
- Los servicios reales presentes son `route`, `jobs`, `video`, `workflow` (no todos los del README todavía).
- El backend usa **`uv`** (no `venv`+`pip` como dice el README).
- **Supabase (ADR-0004):** los repos ya hacen CRUD real con fallback in-memory; la persistencia se activa al aplicar `supabase/migrations` + rellenar `apps/api/.env`. Mientras esos secretos sean placeholders, todo corre en memoria.
- **Sourcing route-céntrico (ADR-0007):** el Spine (ADR-0005) modeló `sources` como asset-céntrico (`asset_id NOT NULL`), pero el user-flow real las aprueba **por Ruta en Gate 1, antes de que existan assets**. ADR-0007 corrige: `sources` gana `learning_path_id`, se quita `asset_id`, y la citación asset↔source pasa a la tabla puente `asset_sources` (M:N). Esto cierra el FK de `kb_chunks.source_id`.
- **Embeddings (ADR-0006):** `architecture.md` proyecta `embeddings: text-embedding-google` vía un gateway `models.yaml` que **aún no existe**. El MVP de la KB usa **`text-embedding-3-small` (1536 dim) servido vía OpenRouter** (OpenAI-compatible) con la `OPENROUTER_KEY` existente; `MockEmbedder` si la clave es placeholder. Conflicto declarado y resuelto en [[docs/adr/0006-kb-rag-ingestion-embeddings]].
- **Corpus de la KB = solo Vía 2 (ADR-0011 revisa ADR-0008 §6):** ADR-0008 §6 definió el corpus de ingesta como `verificada_google OR upload`, metiendo las URLs de YouTube de Vía 1 al KB. Como una URL de YouTube sin transcript solo produce chunks de relleno (`_mock_markdown`), **ADR-0011 restringe el corpus a `origin == 'upload'`**; las de Vía 1 se **vinculan a un módulo** (`source_module_links`, ADR-0012) en vez de ingestarse. El `RealDocumentProvider` deja de sintetizar Markdown para URLs.
- **Colisión de numeración de ADRs (main × KB-RAG):** las ramas `main` (video) y `feature/KB-RAG` (KB) desarrollaron en paralelo y **reutilizaron los números 0006/0007/0008** para decisiones distintas (ver ambos archivos en `docs/adr/`). Deuda documental conocida; los ADRs nuevos de esta integración usan **0011+** para no colisionar. Renumerar los duplicados es un cleanup aparte.

Cuando algo aquí contradiga un ADR, **decláralo explícitamente** en tu output en vez de sobrescribirlo en silencio.

---

## 7. Punteros

- `README.md` — puesta en marcha (parcialmente desactualizado; ver §6).
- `AGENTS.md` — protocolo multi-desarrollador y matriz de propiedad de archivos.
- `CLAUDE.md` — guía operativa para Claude Code (stack, comandos, convenciones).
- `docs/backlog.md` — 15 vertical slices y ownership.
- `docs/issues/` — un ticket por slice para ejecución en paralelo.
- `docs/prd/` — requisitos de producto (PRD).
- `docs/adr/` — registro de decisiones de arquitectura (ADRs).
- `docs/arquitectura/` — documento de arquitectura consolidado.
- `supabase/` — schema versionado (CLI): `migrations/` + `seed.sql` (persistencia · ADR-0004).
- `docs/agents/` — issue tracker, triage y convención de dominio.

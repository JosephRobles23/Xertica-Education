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
| **Estructura / Currículo propuesto** | `generate-structure`, `WorkflowService` | Árbol de módulos y componentes que la IA propone y que el humano revisa en `/estructura-propuesta`. |
| **Módulo** | `models/domain/module.py`, `modules` | Bloque de una ruta (`tipo`: intro/capsula/lab/evaluacion/cierre) con orden y duración objetivo. |
| **Componente** | `models/domain/component.py`, `components` | Pieza de contenido de un módulo: `lesson`/`video`/`lab`/`infografia`/`quiz`. |
| **Asset** | `models/domain/asset.py`, `assets` | Artefacto materializado de un componente, con `estado` de aprobación, `storage_path`, `word_budget`, `provenance`. |
| **AssetVersion** | `models/domain/asset_version.py`, `asset_versions` | Versión histórica de un asset. |
| **Source / Fuente** | `models/domain/source.py`, `sources` | Material de referencia (con `verificada_google` y `estado`) que pertenece a una **Ruta** desde Gate 1 y alimenta la KB. Origen `deep_research` (Vía 1, con `url`) o `upload` (Vía 2, con `document_id`). La citación a assets concretos es M:N vía `asset_sources` ([[docs/adr/0007-source-route-centrica-sourcing]]). |
| **asset_sources** | `asset_sources` | Tabla puente M:N entre `assets` y `sources` para la citación (Fase 5-6). Corrige el 1:N de ADR-0005. |
| **Document (Vía 2)** | `documents`, `adapters/parser/` | Archivo que sube el usuario (PDF/Office). Se guarda en Storage; si `use_as_source`, genera un `Source` Vía 2 (`origin='upload'`, `document_id`) que se parsea **verbatim** e ingesta a la KB ([[docs/adr/0008-document-parsing-via2-ingestion]]). |
| **KB (Knowledge Base)** | `services/kb/`, puerto `KnowledgeBase` | Base de conocimiento RAG construida a partir de las fuentes; alimenta la generación de contenido. Puerto intercambiable ([[docs/adr/0006-kb-rag-ingestion-embeddings]]). |
| **Chunk** | `kb_chunks`, `chunk` | Fragmento de una fuente (parseada a Markdown) que se embebe e indexa en pgvector. Chunking **estructural** ~500 tokens / ~64 solape. |
| **Embedding** | `Embedder`, `text-embedding-3-small` | Vector de **1536 dim** (OpenAI) que representa un chunk; métrica **coseno** (HNSW). Adapter real + `MockEmbedder`. |
| **Grounding / Cita** | `KnowledgeBase.query`, `GroundedChunk` | Resultado de búsqueda con su fuente (`source_id`, título, url, snippet, score, `verificada_google`) que ancla la generación. |
| **Ingesta RAG** | `KnowledgeBase.ingest`, Job | parse → chunk → embed → upsert en `kb_chunks`, como **Job asíncrono** disparado tras Gate 1. |
| **Job** | `JobsService`, `/jobs` | Unidad de trabajo asíncrona con estado y progreso. Toda generación pesada corre como job y se consulta por *polling*. |
| **Gate (Compuerta)** | ver §3 | Punto de aprobación humana que transiciona el estado de la ruta y desbloquea la siguiente fase. |
| **Storyboard** | `/ruta/:id/video-storyboard` | Guion visual del video antes de renderizar. |
| **Biblioteca** | `/biblioteca` | Catálogo de rutas/assets ya producidos. |

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

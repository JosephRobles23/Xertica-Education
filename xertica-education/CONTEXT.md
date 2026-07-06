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
| **Source / Fuente** | `models/domain/source.py`, `sources` | Material de referencia (con `verificada_google`) que cita un asset y alimenta la KB. |
| **KB (Knowledge Base)** | `services/kb/` | Base de conocimiento RAG construida a partir de las fuentes; alimenta la generación de contenido. |
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

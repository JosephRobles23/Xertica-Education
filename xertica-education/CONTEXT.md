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
| **Ruta / Learning Path** | `LearningPath`, `RouteService`, `/learning-paths` | Currículo completo sobre un tema. Unidad de trabajo raíz. Atraviesa estados desde borrador hasta publicado. |
| **Tema** | `tema` | Asunto sobre el que se genera la ruta (payload de creación). |
| **Brief** | `brief` | Descripción/intención libre que el usuario da al crear una ruta. |
| **Estructura / Currículo propuesto** | `generate-structure`, `WorkflowService` | Árbol de módulos y componentes que la IA propone y que el humano revisa en `/estructura-propuesta`. |
| **Componente** | `models/domain/component.py` | Pieza de contenido dentro de una ruta: lección, quiz, infografía, lab o video. |
| **Asset** | `models/domain/asset.py` | Artefacto final generado (video renderizado, PDF de infografía, etc.). |
| **Source / Fuente** | `models/domain/source.py`, *sourcing* | Material de referencia recopilado (deep research) que alimenta la Knowledge Base. |
| **KB (Knowledge Base)** | `services/kb/` | Base de conocimiento RAG construida a partir de las fuentes; alimenta la generación de contenido. |
| **Job** | `JobsService`, `/jobs` | Unidad de trabajo asíncrona con estado y progreso. Toda generación pesada corre como job y se consulta por *polling*. |
| **Gate (Compuerta)** | ver §3 | Punto de aprobación humana que transiciona el estado de la ruta y desbloquea la siguiente fase. |
| **Storyboard** | `/ruta/:id/video-storyboard` | Guion visual del video antes de renderizar. |
| **Biblioteca** | `/biblioteca` | Catálogo de rutas/assets ya producidos. |

### Estados de un Job
`queued` → `running` → (`rendering`) → `completed` | `failed`

### Estados de una Ruta (LearningPath)
`DRAFT` → `PATH_READY` (tras Gate 0) → … → publicado. Las transiciones ocurren **solo** vía endpoints de aprobación.

---

## 3. Gates (compuertas de aprobación humana)

| Gate | Momento | Transición / efecto |
| :--- | :--- | :--- |
| **Gate 0 — Aprobación de currículo** | Tras proponer la estructura | `DRAFT → PATH_READY`; desbloquea las siguientes fases. Endpoint `POST /learning-paths/{id}/approve`. |
| **Gate 1 — Sourcing** | Antes de ingestar KB | Aprueba las fuentes recopiladas por deep research. |
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

El `README.md` describe una arquitectura **aspiracional** que difiere del código real. La verdad de campo es:

- El frontend **no es Next.js 15 App Router**: es **Vite + React 18 + React Router 6 + Tailwind 4 + Radix UI** (estilo shadcn/ui). Ver `apps/web/`.
- No existe (aún) la carpeta `packages/` con workspaces compartidos que menciona el README.
- Los servicios reales presentes son `route`, `jobs`, `video`, `workflow` (no todos los del README todavía).
- `apps/web/src/lib/api.ts` lee `import.meta.env.NEXT_PUBLIC_API_URL`, pero Vite solo expone variables con prefijo `VITE_` → hoy siempre cae al fallback `http://localhost:8000`. Es un residuo del plan Next.js.

Cuando algo aquí contradiga un ADR futuro, **decláralo explícitamente** en tu output en vez de sobrescribirlo en silencio.

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
- `docs/agents/` — issue tracker, triage y convención de dominio.

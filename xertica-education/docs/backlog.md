# Project Backlog — Xertica Education MVP

This backlog organizes the 5-day sprint tasks into prioritized vertical slices (tracer bullets). Each issue must be implemented and tested end-to-end.

---

## 1. Project Foundation (config, schemas, DI)
*   **Owner:** Sebas
*   **What to build:**
    *   Central configuration module `apps/api/config/settings.py` utilizing `pydantic-settings` to load `.env` variables (`SUPABASE_URL`, `OPENROUTER_KEY`, etc.).
    *   Shared domain Pydantic schemas in `apps/api/models/domain/` (`learning_path.py`, `component.py`, `asset.py`, `source.py`).
    *   Shared HTTP payload DTO schemas in `apps/api/models/dto/` (`requests.py`, `responses.py`).
    *   FastAPI root application setup (`apps/api/main.py`) with base routers folder.
*   **Acceptance criteria:**
    - [ ] `settings.py` loads environment variables correctly.
    - [ ] Domain and DTO models are compile-ready and separate.
    - [ ] FastAPI starts up without errors.
*   **Blocked by:** None - can start immediately.

---

## 2. Infrastructure Tracer Bullet
*   **Owner:** Seb
*   **What to build:**
    *   Router `/routers/jobs.py` exposing `POST /jobs` and `GET /jobs/{id}`.
    *   `JobsService` mock implementation tracking statuses (`queued`, `running`, `completed`).
    *   Frontend centralized fetch client wrapper configured using `NEXT_PUBLIC_API_URL`.
    *   Frontend polling logic to fetch job status periodically.
*   **Acceptance criteria:**
    - [ ] POST `/jobs` creates a mock job and returns a `job_id`.
    - [ ] GET `/jobs/{id}` returns the job state changes correctly over time.
    - [ ] Frontend successfully resolves the environment variable and polls the endpoint.
*   **Blocked by:** Issue 1.

---

## 3. LearningPath CRUD
*   **Owner:** Sebas
*   **What to build:**
    *   Expose endpoints in `/routers/learning_paths.py`: `POST /learning-paths` (create), `GET /learning-paths/{id}` (retrieve), and `PATCH /learning-paths/{id}` (edit).
    *   `LearningPathService` mock returning static curriculum arrays.
    *   Connect Dashboard page (`/`) to list paths and Detail page (`/ruta/:id`) to display properties.
*   **Acceptance criteria:**
    - [ ] CRUD endpoints return expected mock JSON payloads.
    - [ ] Frontend successfully displays mock data in dashboard and details.
*   **Blocked by:** Issue 2.

---

## 4. LearningPath Structure Generation (Mock)
*   **Owner:** Sebas
*   **What to build:**
    *   Workflow endpoint `POST /learning-paths/{id}/generate-structure`.
    *   `WorkflowService` pipeline trigger running as a mock async job.
    *   Connect the frontend `/nueva-ruta` submit button to call the generation endpoint and poll the job until complete, then redirect to `/estructura-propuesta`.
*   **Acceptance criteria:**
    - [ ] Generation endpoint initiates structural proposal.
    - [ ] Frontend triggers workflow, monitors job polling, and displays proposed curriculum tree.
*   **Blocked by:** Issue 3.

---

## 5. Gate 0 Curriculum Approval
*   **Owner:** Joseph
*   **What to build:**
    *   Orchestrator endpoint `POST /learning-paths/{id}/approve`.
    *   Transition `LearningPath` status from `DRAFT` to `PATH_READY` in database/mock store.
    *   Connect the "Approve" button on `/estructura-propuesta` to trigger approval and redirect the user back to the path dashboard with Gates unlocked.
*   **Acceptance criteria:**
    - [ ] POST `/approve` transitions state to `PATH_READY`.
    - [ ] UI reflects state transitions and unlocks subsequent gates.
*   **Blocked by:** Issue 4.

---

## 6. Gate 1 Sourcing
*   **Owner:** Arantza
*   **What to build:**
    *   Expose sourcing workflow endpoints: query candidate sources and delete/discard individual sources.
    *   Workflow trigger `POST /learning-paths/{id}/sourcing/approve` to lock sources and transition workflow state to `SOURCES_READY`.
    *   Connect `CorpusSection` in `/ruta/:id` to fetch mock candidate sources, trigger discards, and click "Aprobar corpus" to transition status.
*   **Acceptance criteria:**
    - [ ] Frontend fetches candidate sources and displays verification badges.
    - [ ] Clicking "Aprobar corpus" updates status to `SOURCES_READY` on the backend.
*   **Blocked by:** Issue 5.

---

## 7. Jobs Database Repository
*   **Owner:** Joseph
*   **What to build:**
    *   Create `repositories/jobs/` module using direct Postgres connection.
    *   Replace `JobsService` in-memory mock storage with database select/insert queries to Supabase.
*   **Acceptance criteria:**
    - [ ] Job rows are saved and updated in the Supabase database.
    - [ ] Frontend client polling behaves identically to mock phase.
*   **Blocked by:** Issue 2.

---

## 8. LearningPath Database Repository
*   **Owner:** Joseph
*   **What to build:**
    *   Create `repositories/learning_path/` module.
    *   Save and update learning path modules and components in Supabase Postgres.
*   **Acceptance criteria:**
    - [ ] Learning path data transitions persist in DB across restarts.
    - [ ] API endpoints behave identically to mock phase.
*   **Blocked by:** Issue 3, Issue 7.

---

## 9. Sourcing Database Repository
*   **Owner:** Arantza
*   **What to build:**
    *   Create `repositories/kb/` or sourcing repository module to persist approved sources.
*   **Acceptance criteria:**
    - [ ] Sourcing items and Google verification badges persist in DB.
*   **Blocked by:** Issue 6, Issue 7.

---

## 10. KB & RAG Ingestion
*   **Owner:** Joseph
*   **What to build:**
    *   Implement real `adapters/parser/` (MinerU file parser) and pgvector storage in Supabase.
    *   Build RAG pipeline that compiles the approved sources into a vector search space.
*   **Acceptance criteria:**
    - [ ] Documents parse successfully into markdown.
    - [ ] Sourced documents are indexed in pgvector and retrieved with matching quotes/citations.
*   **Blocked by:** Issue 6, Issue 9.

---

## 11. Lesson Generation Pipeline
*   **Owner:** Santiago
*   **What to build:**
    *   Create `workflows/pipelines/generate_lesson.py`.
    *   Connect `LessonService` to use `adapters/llm/` prompts grounded in the KB to generate structured lesson HTML/Markdown.
*   **Acceptance criteria:**
    - [ ] System generates grounded lesson text citing correct sources.
*   **Blocked by:** Issue 10.

---

## 12. Quiz Generation Pipeline
*   **Owner:** Shared (Lesson/Quiz)
*   **What to build:**
    *   Create quiz generation workflow.
    *   Connect `QuizService` to run LLM prompts grounded in the KB.
*   **Acceptance criteria:**
    - [ ] Quiz questions are generated correctly alongside answer choices.
*   **Blocked by:** Issue 10.

---

## 13. Infographic Generation Pipeline
*   **Owner:** Santiago
*   **What to build:**
    *   Replace mock infographic renderer with real HTML-to-PDF compiler calling `adapters/llm/`.
*   **Acceptance criteria:**
    - [ ] Generates clean, grounded infographic PDF file.
*   **Blocked by:** Issue 10.

---

## 14. Video Storyboard & Render (Gate 2 & Gate 3)
*   **Owner:** Sebas
*   **What to build:**
    *   Implement storyboard approval endpoints (`POST /video/storyboard/approve`).
    *   Connect Next.js script review page (`/ruta/:id/video-storyboard`) to display scripts and budgets.
    *   Implement video render adapter calling `adapters/renderer/` (Google Veo REST API).
*   **Acceptance criteria:**
    - [ ] Script and storyboard reviews block video generation.
    - [ ] Approving rendering initiates Veo call and updates status.
*   **Blocked by:** Issue 10.

---

## 15. Gate 3 Asset Review & E2E Demo
*   **Owner:** Shared (Frontend)
*   **What to build:**
    *   Connect `/ruta/:id/asset-final` to real backend endpoints.
    *   Verify Gate 3 state transitions: approving all assets changes Module status to `Ready for Classroom`.
    *   Perform complete E2E demo run.
*   **Acceptance criteria:**
    - [ ] All 4 asset previews display generated outputs.
    - [ ] Approving assets transitions module state to `Ready for Classroom` automatically.
*   **Blocked by:** Issue 11, Issue 12, Issue 13, Issue 14.

---

# Sprint actual — tareas adicionales por dev

> Detalle y cruces de arquitectura en [`docs/arquitectura/architecture.md`](arquitectura/architecture.md) §14.

## 16. Contexto del Cliente (formulario previo a la ruta)
*   **Owner:** Arantza
*   **What to build:**
    *   Formulario que captura `URL del cliente`, `industria`, `área` (RRHH, Finanzas, TI…) y uso de `Google Workspace`.
    *   Inyectar ese contexto en el prompt del `route_structurer` para personalizar la ruta.
*   **Acceptance criteria:**
    - [ ] El formulario persiste el contexto y precede a la creación de la ruta.
    - [ ] La estructura generada refleja industria/área en su contenido.

## 17. Spike — límites de Deep Research
*   **Owner:** Arantza
*   **What to build:** documento con **límites técnicos y de cuotas** de Deep Research (rate limits, costo, latencia).
*   **Acceptance criteria:**
    - [ ] Reporte con límites y recomendación de uso para el MVP.

## 18. Integración con Google Drive (ingesta y exportación)
*   **Owner:** Joseph
*   **What to build:**
    *   Adjuntar archivos **desde Drive** como fuentes (Vía 2).
    *   Guardar automáticamente los assets finales en Drive.
    *   Auto-organizar carpetas por **cliente → ruta → módulo**.
*   **Acceptance criteria:**
    - [ ] Se pueden seleccionar archivos de Drive como fuentes.
    - [ ] Los assets aprobados aparecen en Drive en la carpeta correcta.

## 19. Quick wins — descargas de assets
*   **Owner:** Joseph
*   **What to build:**
    *   Descarga de assets **agrupados por módulo**.
    *   Descarga **directa a Drive**.
*   **Acceptance criteria:**
    - [ ] Descarga por módulo funcional.
    - [ ] Descarga a Drive funcional.

## 20. Reutilización de videos de entrenamiento existentes
*   **Owner:** Sebas
*   **What to build:** indexar videos largos (ej. ~2 h) por **timestamps + transcripciones segmentadas**, sin edición física, para reaprovechar tramos en el guion.
*   **Acceptance criteria:**
    - [ ] Un segmento del guion puede referenciar un tramo (timestamp) de un video fuente.

## 21. Spike — procesamiento de video de larga duración
*   **Owner:** Sebas
*   **What to build:** análisis de **viabilidad y costos** del procesamiento de videos largos.
*   **Acceptance criteria:**
    - [ ] Reporte con viabilidad, costos y enfoque recomendado.

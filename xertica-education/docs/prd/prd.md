# Product Requirements Document (PRD) — Xertica Education MVP

## Problem Statement
Internal teams creating educational course content (learning paths, modules, video scripts, quizzes, labs, and infographics) face a massive bottleneck. Generating high-quality content takes hours of manual effort (~2h per video capsule, 3–4h per infographic/lab). Furthermore, the content must be strictly grounded in verified Google sources and approved by editors at multiple key cost boundaries (HITL gates) before rendering or publishing, to avoid hallucinations and licensing issues.

## Solution
A collaborative content authoring web workspace structured as a Turborepo monorepo (Next.js 15 frontend + FastAPI backend + Supabase). The platform allows editors to:
1. Input a topic brief or upload reference documents to generate a structured curriculum tree (**Gate 0**).
2. Gather and verify sourcing references, filtering out unverified links (**Gate 1**).
3. Draft and review segmented video scripts and scene storyboards under tight word-budgets before rendering (**Gate 2**).
4. Asynchronously generate, preview, and approve final assets (Video, Infographic, Quiz, Lab guide) (**Gate 3**) before marking them ready for Google Classroom.

---

## Domain Entity Hierarchy
The application structures content according to the following strict hierarchy:
```
LearningPath
   └── Module
         └── Component
               └── Asset
                     ├── Source
                     └── AssetVersion
```

---

## Core User Flow
```
Editor creates a Learning Path
        ↓
Approves curriculum (Gate 0)
        ↓
Approves sources (Gate 1)
        ↓
Approves script/storyboard (Gate 2)
        ↓
Reviews generated assets (Gate 3)
        ↓
Marks module Ready for Classroom
```

---

## Success Criteria (MVP)
The MVP is considered successful if an editor can:
1. Create a Learning Path.
2. Approve Gate 0.
3. Approve Gate 1.
4. Trigger generation.
5. Observe asynchronous job progress.
6. Approve final assets.
7. Mark the module as Ready for Classroom.

All of the above must work end-to-end using either real implementations or contract-compliant mocks.

---

## User Stories

### 1. Curriculum Generation & Review (Gate 0)
1. **As an** editor, **I want to** submit a text brief or upload syllabus files, **so that** the system proposes a modular curriculum structure (`LearningPath -> Modules -> Components`).
2. **As an** editor, **I want to** reorder modules via drag-and-drop, **so that** I can adjust the learning progression.
3. **As an** editor, **I want to** toggle specific components (e.g. choose to generate only a Video and Quiz for a module, and skip the Lab), **so that** I can control the cost and composition of the path.
4. **As an** editor, **I want to** approve the curriculum structure, **so that** the database creates the entities in a `borrador` state and enables the sourcing step.

### 2. Sourcing Verification (Gate 1)
5. **As an** editor, **I want to** view a list of candidate sourcing documents and videos retrieved by the automated sourcing agent, **so that** I can review their source URLs.
6. **As an** editor, **I want to** reject unverified or non-Google sources, **so that** the knowledge base is grounded only in verified references.
7. **As an** editor, **I want to** approve the verified corpus of sources, **so that** the RAG ingestion starts and builds the grounding context.

### 3. Video Scripting & Storyboarding (Gate 2)
8. **As an** editor, **I want to** review the generated script segmented by narrative blocks (Conceptual, Walkthrough, Onboarding), **so that** I can ensure the copy respects word-budgets.
9. **As an** editor, **I want to** preview the visual storyboard placeholders for each scene, **so that** I can authorize the expensive rendering pipeline before it starts.
10. **As an** editor, **I want to** approve the script and storyboard, **so that** the backend renders the video using Google Veo.

### 4. Asset Generation & Approval (Gate 3)
11. **As an** editor, **I want to** track the progress of long-running generation jobs, **so that** I know when my modules are fully compiled.
12. **As an** editor, **I want to** inspect the finished assets in a tabbed workspace (Video playback, Infographic PDF, Quiz questions, and Lab instructions), **so that** I can verify their formatting.
13. **As an** editor, **I want to** approve each asset, **so that** the module state updates.
14. **As an** editor, **I want to** request regeneration or reject a specific asset, **so that** the backend re-runs the pipeline.

### Gate 3 Asset Review Flow
```
Generated ──> Editor Reviews ──> Approve | Reject | Regenerate
                                    │
                                    └──> Updates Asset State
                                           │
                        (When every required asset is approved)
                                           │
                                           └──> Module ──> Ready for Classroom
```

---

## Implementation Decisions

### Replaceability Rule
> **Every feature is replaceable. A feature is considered replaceable if its implementation can change without modifying:**
> * **API contracts**
> * **Workflow contracts**
> * **Frontend code**

*   **Renaming Domain concept:** "Route" is renamed to "LearningPath" to prevent terminology clashes with HTTP router terminology.
*   **Decoupled Interface Client:** The frontend communicates only with the backend API. Internal orchestration is completely hidden from the client.
*   **Dependency Injection (DI):** Expose interface base classes for services/repositories/adapters. FastAPI's `Depends()` resolves service classes at the router layer. Services receive repositories and adapters via constructor injection.
*   **DTO/Domain Separation:** API payloads are kept inside `models/dto/` (requests.py and responses.py) while database/business models are kept inside `models/domain/`.
*   **Centralized Configuration:** Managed in `apps/api/config/settings.py` utilizing `pydantic-settings` to parse `.env` files.
*   **Mock-First Fallbacks:** If external adapters (Veo, Supabase, LLM) are disabled or unavailable, services return static payloads conforming to contracts without raising errors.

---

## Testing Decisions
*   **External Integration Tests first:** Before integrating real AI rendering or indexing, verify that the frontend can execute all flows (Gates 0, 1, 2, 3) end-to-end against mock HTTP responses and public bucket assets.
*   **Interface Testing:** Ensure all Pydantic DTO models validate successfully against mock inputs.
*   **Unit Tests Suite:** Set up test folders under `apps/api/tests/` matching domain areas (`learning_path/`, `workflow/`, `video/`) using standard mocks injected during setup.

---

## Out of Scope (for MVP)
*   **Automated Google Classroom Integration:** The final publication to Classroom will be simulated by toggling a status field; the actual Google API sync tool is out of scope.
*   **LiteLLM proxy / Self-hosted MinerU:** GPU MinerU deployment and LiteLLM proxy setups are postponed to Phase 2. Mocks and standard APIs will be used.
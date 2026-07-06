# Xertica Education Monorepo

Welcome to the **Xertica Education** application workspace. This project is structured as a modular monorepo containing a Next.js 15 App Router web application and a FastAPI Python backend orchestration API.

---

## MVP Golden Rules

> **1. No feature may block another feature. If a dependency is unavailable, return mock or placeholder data that conforms to the contract.**
> 
> **2. If an implementation decision requires changing an API contract, stop and discuss it first. If it only changes the internal implementation behind an existing contract, proceed.**

---

## Repository Structure

*   `apps/web/`: Next.js 15 App Router web application (coordinates UI, routes: `/nueva-ruta`, `/estructura-propuesta`, `/ruta/[id]`).
*   `apps/api/`: FastAPI backend application.
    *   `routers/`: Exposes HTTP routes (`learning_paths.py`, `workflow.py`, `jobs.py`).
    *   `workflows/`: Pipeline orchestrators (`pipelines/generate_module.py`, etc.).
    *   `services/`: Decoupled business capabilities (video, kb, infographic, lesson, quiz, lab, jobs, route, sourcing). Each service contains `interface.py` and `service.py`.
    *   `repositories/`: Mirrored persistence layer handling database transactions.
    *   `models/`: Separated into `domain/` models and `dto/` API contracts.
    *   `adapters/`: capability-based external adapters (`llm/`, `storage/`, `parser/`, `renderer/`).
*   `packages/`: Shared workspaces (`types/`, `ui/`, `config/`, `schemas/`).
*   `docs/`:
    *   `backlog.md`: The complete 15 vertical slice backlog and team ownership mappings.
    *   `issues/`: Independent ticket files representing each slice (e.g. `issue-01-foundation.md`) for coding agents to execute in parallel.

---

## Getting Started

### 1. Root Installation
This monorepo uses **pnpm** (see `packageManager` in the root `package.json` and `pnpm-workspace.yaml`). Ensure Node.js and pnpm are installed (`corepack enable` will provide pnpm), then run the workspace setup command from the monorepo root:
```bash
pnpm install
```

### 2. Backend Setup (`apps/api`)
1. Create and activate a Python virtual environment:
   ```bash
   cd apps/api
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server (runs FastAPI on port 8000):
   ```bash
   pnpm dev  # Triggered via package.json uv scripts at monorepo root
   ```

### 3. Frontend Setup (`apps/web`)
1. Create a local environment file `apps/web/.env.local` pointing to the API URL:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
2. Run the Next.js development server:
   ```bash
   pnpm --filter xertica-education-web dev
   ```

---

## Execution Guide for Coding Agents
Coding agents must:
1. Always work from **left-to-right**: `Contracts ──> Models ──> Endpoints ──> Frontend ──> Real AI`.
2. Pick up tickets inside `docs/issues/` sequentially in dependency order.
3. Keep services deterministic and prompts local to service folders.

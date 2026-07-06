# Agent Instructions

This repository is configured for AI agents and engineering skills.

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<developer-name>/`. External PRs are not treated as a triage surface. See [issue-tracker.md](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/agents/issue-tracker.md).

### Triage labels

Triage maps to the five canonical roles using default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See [triage-labels.md](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/agents/triage-labels.md).

### Domain docs

Layout is single-context (one global `CONTEXT.md` and `docs/adr/` directory at the repository root). See [domain.md](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/agents/domain.md).

## Multi-Developer Agent Protocol

To support parallel development by multiple developers without conflicts, agents must adhere to scoped ownership rules.

### 1. Identify Yourself
At startup, read the local identity file [identity.json](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/.agents/identity.json) (which is gitignored). It defines which developer you are representing (e.g., `sebas`).

If the file does not exist, ask the user to create it using the template [identity.json.example](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/.agents/identity.json.example).

### 2. Developer Ownership Matrix
Agents must respect file access and modification limits based on their active identity:

| Developer | Scope / Responsibility | Primary Folders & Files |
| :--- | :--- | :--- |
| **joseph** | (None currently assigned) | |
| **arantza** | Sourcing & Deep Research | `apps/api/services/sourcing.py`, `apps/api/services/sourcing/`, `apps/api/adapters/` (sourcing-related) |
| **sebas** | Learning Path, Workflows, Jobs, KB, Video Production | `apps/api/workflows/`, `apps/api/routers/`, `apps/api/services/kb/`, `apps/api/services/jobs/`, `apps/api/services/video/`, `apps/api/repositories/`, `apps/api/models/`, `apps/api/adapters/` (video/rendering-related), `packages/types/`, `supabase/` |
| **santiago** | Infographics & Common UI | `apps/api/services/infographic/`, `apps/web/` |
| *Shared* | Instructional Design, UI / Docs | `apps/web/` (general UI updates), `apps/api/services/lesson/`, `apps/api/services/quiz/`, `apps/api/services/lab/`, `docs/` |

### 3. Execution Rules
- **Write Actions**: You are only allowed to edit/modify files in the **Primary Folders & Files** of your active developer, or files under *Shared* directories.
- **Out-of-Scope Modifications**: If you need to modify a file outside of your scope, you **must** pause and ask the user for explicit confirmation before writing any changes.
- **Read Actions**: You are free to read any file in the workspace to gain context.

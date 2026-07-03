# To Issues (Generar tickets)

> **Trigger:** User invokes explicitly. Break a plan/PRD into vertical-slice issues and publish to Linear.

## Linear labels

`bug`, `enhancement`, `needs-info`, `ready-for-agent`, `ready-for-human`. Default: `ready-for-agent`.

## Process

1. **Gather context** from conversation. Fetch from Linear if user passes a reference.
2. **Explore codebase** (optional). Use `CONTEXT.md` vocabulary, respect ADRs in `docs/adr/`.
3. **Draft vertical slices** — each cuts through ALL layers end-to-end (schema, API, UI, tests). Each is demoable alone. Prefactoring goes first.
4. **Quiz the user** — present numbered list: Title, Blocked by, User stories covered. Iterate until approved.
5. **Publish to Linear** in dependency order (blockers first).

## Issue Template

```markdown
## Parent
## What to build (end-to-end, no file paths)
## Acceptance criteria (checkboxes)
## Blocked by
```

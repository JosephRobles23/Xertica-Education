---
name: to-issues
description: "Generar tickets — Romper un plan, spec o PRD en issues independientes tipo vertical-slice (tracer bullets) y publicarlos en Linear."
disable-model-invocation: true
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

## Issue tracker

Publish to **Linear** using the MCP tools. Labels for triage:

| Label | Meaning |
|-------|---------|
| `bug` | Something is broken |
| `enhancement` | New feature or improvement |
| `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | Fully specified, ready for an AFK AI agent |
| `ready-for-human` | Needs human implementation |

Default label for new issues: `ready-for-agent` unless the issue requires human judgment.

## Process

### 1. Gather context

Work from whatever is already in the conversation. If the user passes an issue reference, fetch it from Linear and read its full body and comments.

### 2. Explore the codebase (optional)

Use `CONTEXT.md` vocabulary and respect ADRs in `docs/adr/`. Look for prefactoring opportunities: "Make the change easy, then make the easy change."

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Any prefactoring should be done first

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice show:

- **Title**: short descriptive name
- **Blocked by**: which other slices must complete first
- **User stories covered**: which user stories this addresses

Ask: Does the granularity feel right? Are dependencies correct? Should any slices be merged or split? Iterate until the user approves.

### 5. Publish to Linear

For each approved slice, publish a new issue. Use the template below. Publish in dependency order (blockers first) so you can reference real issue identifiers.

## Issue Template

```markdown
## Parent
Reference to the parent issue (if the source was an existing issue).

## What to build
Concise description of this vertical slice. Describe end-to-end behavior,
not layer-by-layer implementation. No file paths or code snippets (they go
stale). Exception: prototype snippets that encode a decision precisely.

## Acceptance criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by
- Reference to blocking ticket(s)
Or "None - can start immediately" if no blockers.
```

Do NOT close or modify any parent issue.

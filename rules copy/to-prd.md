# To PRD (Generar PRD)

> **Trigger:** User invokes explicitly. Synthesize the current conversation into a PRD.

Do NOT interview the user — just synthesize what you already know.

## Issue tracker

Publish to **Linear**. Apply the `ready-for-agent` label.

## Process

1. Explore the repo. Use `CONTEXT.md` vocabulary and respect ADRs in `docs/adr/`.
2. Sketch test seams. Prefer existing seams. Check with the user.
3. Write the PRD using the template below and publish to Linear.

## PRD Template

```markdown
## Problem Statement
## Solution
## User Stories (extensive numbered list)
## Implementation Decisions (no file paths — they go stale)
## Testing Decisions
## Out of Scope
## Further Notes
```

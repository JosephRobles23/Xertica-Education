---
name: to-prd
description: "Generar PRD — Sintetizar la conversación actual en un PRD y publicarlo en Linear. Sin interrogatorio, solo síntesis de lo ya discutido."
disable-model-invocation: true
---

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

## Issue tracker

Publish to **Linear** using the MCP tools. Apply the `ready-for-agent` label. No additional triage needed.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary from `CONTEXT.md` throughout the PRD, and respect any ADRs in `docs/adr/`.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. Check with the user that these seams match their expectations.

3. Write the PRD using the template below, then publish it to Linear.

## PRD Template

```markdown
## Problem Statement
The problem the user is facing, from the user's perspective.

## Solution
The solution, from the user's perspective.

## User Stories
A LONG, numbered list. Each in the format:
1. As an <actor>, I want a <feature>, so that <benefit>

This list should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions
A list of implementation decisions made:
- Modules to build/modify
- Interface shapes
- Technical clarifications
- Architectural decisions
- Schema changes
- API contracts

Do NOT include specific file paths or code snippets — they go stale fast.
Exception: if a prototype produced a snippet that encodes a decision more
precisely than prose (state machine, schema, type shape), inline it and note
it came from a prototype.

## Testing Decisions
- What makes a good test (external behavior, not implementation details)
- Which modules will be tested
- Prior art for tests (similar tests in the codebase)

## Out of Scope
What is explicitly not included.

## Further Notes
Any additional context.
```

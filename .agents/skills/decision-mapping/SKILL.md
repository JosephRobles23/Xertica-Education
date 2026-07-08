---
name: decision-mapping
description: "Mapa de decisiones — Convertir una idea suelta en un mapa secuenciado de tickets de investigación, y resolverlos uno a uno."
disable-model-invocation: true
---

This skill turns a loose idea into a sequenced map of investigation tickets, then drives the user through them one at a time. Each ticket is sized to one agent session.

## The Decision Map

A single compact Markdown file, git-tracked alongside the project. The **whole map is loaded as context into every session**, so it must stay compact. Assets created during tickets should be linked, not duplicated within it.

### Structure

```markdown
## #1: <Question>

Blocked by: #<number>, #<number>
Type: Research | Prototype | Discuss

### Question
<question-here>

### Answer
<answer-here>
```

## Ticket Types

- **Research**: Reading documentation, third-party APIs, or local resources. Creates a markdown summary as an asset. Use when knowledge outside the working directory is required.
- **Prototype**: Writing UI or logic code to test a hypothesis. Uses the `/prototype` skill. Creates throwaway code as an asset. Use when "how should it look" or "how should it behave" is the key question.
- **Discuss**: Conversation with the agent. Uses `/grilling` and `/domain-modeling`. The default case.

## Fog of war

The map is *deliberately* incomplete beyond the frontier. Your job is to investigate the frontier and resolve tickets to push it forward. At some point the path to the finish line is clear and no more tickets are needed.

## Invocation

### Bootstrap

User invokes with a loose idea.

1. Run a `/grilling` and `/domain-modeling` session to surface the open decisions.
2. Write a new decision map — mostly fog, frontier identified, trivially-decidable entries resolved inline.
3. Stop. Map-building is one session's work; do not also resolve tickets.

### Resume

User invokes with a path to an existing map and a ticket number.

1. Load the **whole map** as context.
2. Run a session to resolve the ticket, invoking skills as needed. If in doubt, use `/grilling` and `/domain-modeling`.
3. Record what the session resolved in the ticket's body.
4. Add newly-discovered tickets (with correct `Blocked by` edges).
5. Stop.

If the decisions made invalidate other parts of the map, update or delete those nodes.

## Skipping The Decision Map

If the initial grilling reveals no fog of war — no unresolved tickets — offer the user the chance to skip the decision map. Recommend either implementing directly or using `/to-prd` to schedule implementation.

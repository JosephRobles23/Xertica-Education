---
name: prototype
description: "Prototipo — Construir código desechable que responda una pregunta: una app de terminal para lógica/state-machines, o varias variaciones de UI radicalmente diferentes en una ruta."
disable-model-invocation: true
---

# Prototype

A prototype is **throwaway code that answers a question**. The question decides the shape.

## Pick a branch

Identify which question is being answered:

- **"Does this logic / state model feel right?"** → **Logic branch.** Build a tiny interactive terminal app that pushes the state machine through cases that are hard to reason about on paper.
- **"What should this look like?"** → **UI branch.** Generate several radically different UI variations on a single route, switchable via a URL search param and a floating bottom bar.

If the question is ambiguous, default to whichever branch matches the surrounding code (a backend module → logic; a page or component → UI) and state the assumption.

## Rules for both branches

1. **Throwaway from day one, clearly marked.** Place it close to where it will actually be used. Name it so it's obviously a prototype, not production.
2. **One command to run.** Whatever the project's existing task runner supports.
3. **No persistence by default.** State lives in memory.
4. **Skip the polish.** No tests, no error handling beyond what makes it runnable, no abstractions.
5. **Surface the state.** After every action (logic) or on every variant switch (UI), print or render the full relevant state.
6. **Delete or absorb when done.** When the prototype has answered its question, either delete it or fold the validated decision into the real code.

## When done

The *answer* is the only thing worth keeping. Capture it somewhere durable — commit message, ADR, issue, or a note next to the prototype — along with the question it was answering. Then the prototype can be deleted.

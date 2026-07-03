# Prototype (Prototipo)

> **Trigger:** User invokes explicitly. Build throwaway code that answers a design question.

A prototype is **throwaway code that answers a question**. The question decides the shape.

## Pick a branch

- **"Does this logic / state model feel right?"** → **Logic.** Tiny interactive terminal app.
- **"What should this look like?"** → **UI.** Several radically different variations on a single route, switchable via URL param.

Default to whichever branch matches the surrounding code if ambiguous.

## Rules

1. **Throwaway from day one, clearly marked.** Place it close to where it will be used.
2. **One command to run.**
3. **No persistence.** State lives in memory.
4. **Skip the polish.** No tests, no error handling beyond runnable, no abstractions.
5. **Surface the state.** Print or render full state after every action.
6. **Delete or absorb when done.**

## When done

Capture the *answer* (commit message, ADR, issue). Delete the prototype.

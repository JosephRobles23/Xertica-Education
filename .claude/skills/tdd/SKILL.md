---
name: tdd
description: "Desarrollo guiado por tests — Implementar features o arreglar bugs con ciclos red-green-refactor. Usar cuando el usuario quiere TDD, dice 'test-first', 'red-green', o cuando se implementa lógica de negocio."
---

# Test-Driven Development

## Philosophy

**Core principle**: Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

**Good tests** exercise real code paths through public APIs. They describe *what* the system does, not *how*. A good test reads like a specification. These tests survive refactors.

**Bad tests** are coupled to implementation: they mock internal collaborators, test private methods, or verify through external means. Warning sign: your test breaks when you refactor, but behavior hasn't changed.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This produces crap tests that test *imagined* behavior, not *actual* behavior.

**Correct approach**: Vertical slices via tracer bullets.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

## Workflow

### 1. Planning

Read `CONTEXT.md` (if it exists) so that test names and interface vocabulary match the project's domain language. Respect ADRs in `docs/adr/`.

Before writing any code:

- Confirm with user what interface changes are needed
- Confirm which behaviors to test (prioritize)
- Identify opportunities for **deep modules** — small interface, deep implementation. A deep module hides complexity behind a simple API. The interface is the test surface: callers and tests cross the same seam.
- List the behaviors to test (not implementation steps)
- Get user approval on the plan

**You can't test everything.** Confirm which behaviors matter most.

### 2. Tracer Bullet

Write ONE test that confirms ONE thing:

```
RED:   Write test for first behavior → test fails
GREEN: Write minimal code to pass → test passes
```

### 3. Incremental Loop

For each remaining behavior:

```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

Rules:
- One test at a time
- Only enough code to pass current test
- Don't anticipate future tests
- Keep tests focused on observable behavior

### 4. Refactor

After all tests pass, look for refactor candidates:

- Extract duplication
- Deepen modules (move complexity behind simple interfaces)
- Run tests after each refactor step

**Never refactor while RED.** Get to GREEN first.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

## Design vocabulary (from codebase-design)

Use these terms when discussing architecture during TDD:

- **Module** — anything with an interface and an implementation. Scale-agnostic.
- **Interface** — everything a caller must know: type signature, invariants, error modes, performance.
- **Depth** — leverage at the interface: behavior per unit of interface learned. Deep = good.
- **Seam** — where you can alter behavior without editing in that place. The test surface.
- **The deletion test** — delete the module. If complexity reappears across callers, it was earning its keep.
- **The interface is the test surface** — callers and tests cross the same seam. If you need to test past the interface, the module is the wrong shape.

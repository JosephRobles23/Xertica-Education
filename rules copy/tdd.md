# TDD (Desarrollo guiado por tests)

> **Trigger:** User says "TDD", "test-first", "red-green", or implementation involves business logic.

## Philosophy

Tests verify **behavior** through **public interfaces**, not implementation details. Vertical slices only:

```
RED→GREEN: test1→impl1
RED→GREEN: test2→impl2
```

Never horizontal (all tests first, then all implementation).

## Workflow

1. **Plan**: Read `CONTEXT.md` for domain vocabulary. Confirm with user: interface shape, behaviors to test. Identify deep modules (small interface, lots of hidden complexity).
2. **Tracer bullet**: ONE test → ONE implementation.
3. **Incremental loop**: One test at a time. Only enough code to pass.
4. **Refactor**: Only when GREEN. Deepen modules, extract duplication.

## Rules

- One test at a time
- Tests use public interface only
- Tests survive internal refactors
- No speculative features
- Never refactor while RED

## Design vocabulary

- **Module** — anything with an interface and implementation.
- **Depth** — behavior per unit of interface. Deep = good.
- **Seam** — where you alter behavior without editing there. The test surface.
- **Deletion test** — delete the module; if complexity disperses, it was earning its keep.

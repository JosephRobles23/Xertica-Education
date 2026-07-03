---
name: improve-architecture
description: "Mejorar arquitectura — Escanear el codebase buscando oportunidades de profundización, presentarlas como reporte HTML visual, y luego grillear la que el usuario elija."
disable-model-invocation: true
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones.

## Design vocabulary

Use these terms exactly — don't substitute "component", "service", "API", or "boundary":

- **Module** — anything with an interface and an implementation. Scale-agnostic.
- **Interface** — everything a caller must know: type signature, invariants, error modes, performance.
- **Depth** — leverage at the interface: behavior per unit of interface learned. Deep = good, shallow = bad.
- **Seam** *(Michael Feathers)* — where you can alter behavior without editing in that place.
- **Adapter** — a concrete thing that satisfies an interface at a seam.
- **Leverage** — what callers get from depth: more capability per unit of interface.
- **Locality** — what maintainers get from depth: change concentrates in one place.

Key principles:
- **The deletion test**: delete the module. If complexity reappears across callers, it was earning its keep.
- **The interface is the test surface**: callers and tests cross the same seam.
- **One adapter = hypothetical seam. Two adapters = real seam.**

## Process

### 1. Explore

Read `CONTEXT.md` and ADRs in `docs/adr/` first. Then walk the codebase organically, noting friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as implementation?
- Where have pure functions been extracted just for testability, but bugs hide in how they're called?
- Where do tightly-coupled modules leak across their seams?
- Which parts are untested or hard to test through their current interface?

Apply the **deletion test** to anything suspect.

### 2. Present candidates as HTML report

Write a self-contained HTML file to the OS temp directory. Use **Tailwind via CDN** for layout and **Mermaid via CDN** for diagrams. Open it for the user.

For each candidate, render a card with:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture causes friction
- **Solution** — plain English what would change
- **Benefits** — in terms of locality and leverage, and how tests improve
- **Before / After diagram** — side-by-side
- **Recommendation strength** — `Strong`, `Worth exploring`, or `Speculative`

End with a **Top recommendation** section.

Use `CONTEXT.md` vocabulary for domain terms. If a candidate contradicts an existing ADR, only surface it when the friction is real enough to revisit. Mark it clearly.

Do NOT propose interfaces yet. Ask: "Which of these would you like to explore?"

### 3. Grilling loop

Once the user picks a candidate, run `/grilling` to walk the design tree — constraints, dependencies, module shape, what sits behind the seam, what tests survive.

Side effects inline as decisions crystallize — run `/domain-modeling`:

- New concept not in `CONTEXT.md`? Add it.
- Fuzzy term sharpened? Update `CONTEXT.md`.
- Candidate rejected with a load-bearing reason? Offer an ADR.

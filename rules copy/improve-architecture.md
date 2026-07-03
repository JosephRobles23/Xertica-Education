# Improve Architecture (Mejorar arquitectura)

> **Trigger:** User invokes explicitly. Scan codebase for deepening opportunities.

Surface architectural friction and propose **deepening opportunities** — shallow modules → deep modules.

## Vocabulary (use exactly)

- **Module** — anything with interface + implementation. Scale-agnostic.
- **Depth** — behavior per unit of interface. Deep = good.
- **Seam** — where you alter behavior without editing there.
- **Leverage** — callers get more capability per unit of interface.
- **Locality** — changes concentrate in one place.
- **Deletion test** — delete it; if complexity disperses, it was earning its keep.

## Process

### 1. Explore

Read `CONTEXT.md` and ADRs in `docs/adr/`. Walk the codebase noting: shallow modules, tight coupling, untestable interfaces, excessive module-hopping.

### 2. HTML report

Write to OS temp dir. Tailwind + Mermaid via CDN. Per candidate: Files, Problem, Solution, Benefits (locality + leverage), Before/After diagram, Recommendation strength.

End with Top recommendation. Do NOT propose interfaces. Ask which to explore.

### 3. Grilling loop

Run `grilling` on the chosen candidate. Run `domain-modeling` to update `CONTEXT.md` and offer ADRs as decisions land.

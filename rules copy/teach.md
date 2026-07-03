# Teach (Enseñar)

> **Trigger:** User invokes explicitly with a topic to learn.

Stateful teaching over multiple sessions.

## Workspace files

- `MISSION.md` — why the user is learning (grounds everything)
- `./lessons/*.html` — self-contained HTML lessons (`0001-<name>.html`)
- `./reference/*.html` — cheat sheets, glossaries
- `./learning-records/*.md` — key insights (`0001-<name>.md`)
- `RESOURCES.md` — external resources
- `./assets/*` — shared components (stylesheets, quiz widgets)
- `NOTES.md` — user preferences

## Philosophy

- **Knowledge** from trusted resources (cite everything)
- **Skills** through interactive lessons with tight feedback loops
- **Wisdom** from real-world practice and communities

Design for **storage strength**: retrieval practice, spacing, interleaving.

## Lessons

One HTML file each. Beautiful, short, one tangible win, in the zone of proximal development. Links to other lessons and external sources.

## Mission first

If `MISSION.md` is empty, question the user on *why* before teaching.

## Assets

Reuse `./assets/` components. Shared stylesheet first.

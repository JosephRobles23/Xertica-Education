# CLAUDE.md

Las reglas siempre activas y el protocolo de skills de este repo están definidos de forma
**cross-tool** en `AGENTS.md`. Claude Code los hereda con el import de abajo.

@AGENTS.md

## Notas específicas de Claude Code

- Además del protocolo de `AGENTS.md`, Claude Code **carga automáticamente** las skills de
  `.claude/skills/` (invocables con `/<nombre>`; algunas se auto-invocan según su frontmatter).
- El protocolo de skills (`AGENTS.md` §2) te habilita también las de `.agents/skills/`.
- Sigue las **reglas siempre activas** (`AGENTS.md` §1) en cada turno.

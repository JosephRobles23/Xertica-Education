# Ponytail Review (Revisión minimalista)

> **Trigger:** User invokes explicitly. Review diffs for over-engineering only.

One line per finding: location, what to cut, what replaces it.

## Tags

- `delete:` dead code, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled stdlib. Name the function.
- `native:` dependency doing what the platform does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets.
- `shrink:` same logic, fewer lines. Show shorter form.

## Format

`L<line>: <tag> <what>. <replacement>.`

End with: `net: -<N> lines possible.`
Nothing to cut: `Lean already. Ship.`

## Scope

Over-engineering and complexity only. Correctness, security, performance → separate review. Lists findings, applies nothing.

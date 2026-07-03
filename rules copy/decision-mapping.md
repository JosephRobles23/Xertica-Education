# Decision Mapping (Mapa de decisiones)

> **Trigger:** User invokes explicitly with a loose idea or an existing map + ticket number.

Turn a loose idea into a sequenced map of investigation tickets, then drive the user through them one at a time.

## The Decision Map

A single compact Markdown file, git-tracked. The whole map is loaded as context into every session, so keep it compact.

```markdown
## #1: <Question>

Blocked by: #<number>
Type: Research | Prototype | Discuss

### Question
<question>

### Answer
<answer>
```

## Ticket Types

- **Research**: Reading docs, APIs, resources. Creates a markdown summary.
- **Prototype**: Throwaway code to test a hypothesis. Uses `prototype` skill.
- **Discuss**: Conversation using `grilling` and `domain-modeling`. Default.

## Fog of war

The map is deliberately incomplete beyond the frontier. Resolve tickets to push it forward. When the path to the finish line is clear, no more tickets are needed.

## Bootstrap (new idea)

1. Run a grilling and domain-modeling session to surface open decisions.
2. Write a new decision map — mostly fog, frontier identified, trivial entries resolved inline.
3. Stop. Do not also resolve tickets.

## Resume (existing map + ticket number)

1. Load the whole map as context.
2. Resolve the ticket, invoking skills as needed.
3. Record the resolution. Add newly-discovered tickets with `Blocked by` edges.
4. Stop.

## Skip

If the initial grilling reveals no fog of war, offer to skip. Recommend `to-prd` instead.

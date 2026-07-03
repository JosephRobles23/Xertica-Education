# Grill With Docs (Interrogatorio con documentación)

> **Trigger:** User invokes explicitly. Combines grilling + domain-modeling in a single session.

Run a grilling session (see `grilling.md`) combined with domain modeling (see `domain-modeling.md`).

This means: interview the user relentlessly about the plan (one question at a time, with your recommended answer), AND actively maintain the domain model as decisions land:

- Update `CONTEXT.md` the moment a term is resolved
- Offer ADRs when a decision is hard-to-reverse, surprising, and the result of a real trade-off
- Challenge terms that conflict with the existing glossary
- Sharpen vague language into precise canonical terms

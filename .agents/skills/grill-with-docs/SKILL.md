---
name: grill-with-docs
description: "Interrogatorio con documentación — Sesión de grilling que también crea documentación (ADRs y glosario) sobre la marcha."
disable-model-invocation: true
---

Run a `/grilling` session, using the `/domain-modeling` skill.

This means: interview the user relentlessly about the plan (one question at a time, with your recommended answer), AND actively maintain the domain model as decisions land:

- Update `CONTEXT.md` the moment a term is resolved
- Offer ADRs when a decision is hard-to-reverse, surprising, and the result of a real trade-off
- Challenge terms that conflict with the existing glossary
- Sharpen vague language into precise canonical terms

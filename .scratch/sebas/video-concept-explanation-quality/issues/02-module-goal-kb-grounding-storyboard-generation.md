Status: ready-for-agent

## Parent

../PRD.md

## What to build

Make Storyboard generation use the Objetivo Pedagogico del Modulo as the spine and KB Grounding as evidence/examples. Given a module title, module description, optional route context, and useful KB chunks, the generated Storyboard should be a 5-7 scene Video de Explicacion Conceptual with Patrones Didacticos and reviewable teaching metadata.

This slice should replace generic scriptwriter behavior with a teaching-first prompt/output path while staying behind the existing `POST /videos/storyboard` endpoint.

## Acceptance criteria

- [ ] Given useful KB Grounding, `POST /videos/storyboard` returns a `KB-grounded` storyboard with 5-7 strong scenes.
- [ ] The module title and description define the teaching goal; KB chunks provide evidence, examples, and vocabulary.
- [ ] Each scene includes a teaching pattern, teaching point, visual rationale, and grounding status.
- [ ] The output avoids becoming a random summary of retrieved chunks.
- [ ] Tests are written first using fake module context and fake KB chunks at the `POST /videos/storyboard` seam.

## Blocked by

- 01-concept-explanation-storyboard-contract.md

## TDD seam

`POST /videos/storyboard` with fake module context and fake KB chunks.

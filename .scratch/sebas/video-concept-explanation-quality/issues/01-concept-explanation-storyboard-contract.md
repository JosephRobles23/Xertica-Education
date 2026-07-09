Status: ready-for-agent

## Parent

../PRD.md

## What to build

Define the public Storyboard contract for a Video de Explicacion Conceptual so backend and frontend can review the same educational intent before render. A Storyboard scene should expose the teaching point, pedagogical intent, teaching pattern, visual rationale, grounding status, narration, visual type, and visual config in a way that remains compatible with the existing render path.

This slice should establish the contract at the highest seam first: `POST /videos/storyboard` returns reviewable scene metadata while still returning a storyboard that can be passed to `POST /videos/generate`.

## Acceptance criteria

- [ ] `POST /videos/storyboard` can return scene-level teaching metadata without breaking existing storyboard consumers.
- [ ] The response distinguishes `KB-grounded` from `Module-grounded` storyboards at a public contract level.
- [ ] Existing `custom_storyboard` rendering remains compatible with the new metadata.
- [ ] Tests are written first at the `POST /videos/storyboard` response-contract seam.

## Blocked by

None - can start immediately

## TDD seam

`POST /videos/storyboard` response contract.

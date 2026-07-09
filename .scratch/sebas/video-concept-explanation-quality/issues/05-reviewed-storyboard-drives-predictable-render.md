Status: ready-for-agent

## Parent

../PRD.md

## What to build

Ensure the approved Storyboard is the creative source of truth for render. Once a user starts video generation from the Revisión de Storyboard, `POST /videos/generate` should use the supplied `custom_storyboard` exactly as the render input and avoid regenerating creative decisions inside the render pipeline.

The completed video job should retain lightweight provenance that ties the final Video Asset Renderizado back to the reviewed Storyboard.

## Acceptance criteria

- [ ] `POST /videos/generate` accepts the reviewed Storyboard with teaching metadata and starts a render job.
- [ ] Render execution uses the submitted Storyboard rather than regenerating or replacing the creative plan.
- [ ] Job/result provenance includes the approved Storyboard or a lightweight reference to it.
- [ ] The final Video Asset Renderizado can be traced back to the reviewed Storyboard.
- [ ] Tests are written first at the `POST /videos/generate` seam with a `custom_storyboard`.

## Blocked by

- 01-concept-explanation-storyboard-contract.md
- 04-storyboard-review-ui-with-teaching-intent.md

## TDD seam

`POST /videos/generate` with `custom_storyboard`.

Status: ready-for-agent

## Parent

../PRD.md

## What to build

Update the Revisión de Storyboard UI so a human can review the actual educational plan before render. The page should show each scene's teaching point, grounding status, visual type, narration, and visual rationale, and it should let the user correct bad narration or visual choices before starting render.

This slice should also fix the current module identifier mismatch that causes the page to fall back to hardcoded Storyboard blocks instead of calling the backend with a valid Render Target.

## Acceptance criteria

- [ ] The video storyboard page loads a real backend Storyboard for a valid Render Target instead of silently relying on hardcoded blocks.
- [ ] Each scene shows teaching point, grounding status, visual type, narration, and visual rationale.
- [ ] A user can edit narration before render.
- [ ] The reviewed scene data is what the page sends to `POST /videos/generate`.
- [ ] Tests are written first at the video storyboard page behavior seam.

## Blocked by

- 01-concept-explanation-storyboard-contract.md

## TDD seam

Video storyboard page behavior.

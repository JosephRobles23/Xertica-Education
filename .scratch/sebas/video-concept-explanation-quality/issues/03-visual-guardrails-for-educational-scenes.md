Status: ready-for-agent

## Parent

../PRD.md

## What to build

Enforce visual guardrails so the Storyboard generator chooses Remotion Tipos Visuales for learning value rather than decoration. The Paleta Visual MVP should be preferred, `ai_video` should be optional and rare, generated illustrations should explain concrete mental models, quantitative charts should not invent unsupported values, and screenshots should only appear for Walkthroughs Didacticos.

This slice should make bad visual choices observable through the public Storyboard output and either prevent, repair, or clearly label them.

## Acceptance criteria

- [ ] The generator no longer requires or defaults to a generic opening `ai_video`.
- [ ] `ai_video` appears at most once and only with a meaningful visual metaphor rationale.
- [ ] `ai_illustration` is used only for a concrete mental model or architecture rationale.
- [ ] Quantitative visual types require evidenced values or explicit illustrative labeling.
- [ ] `screenshot_scene` requires URL, purpose, ordered UI steps, and learning outcome.
- [ ] Tests are written first at the `POST /videos/storyboard` seam to cover guardrails and fallback choices.

## Blocked by

- 01-concept-explanation-storyboard-contract.md
- 02-module-goal-kb-grounding-storyboard-generation.md

## TDD seam

`POST /videos/storyboard` validation or repair behavior for visual choices.

Status: ready-for-agent

## Parent

../PRD.md

## What to build

Prove the full Video de Explicacion Conceptual path composes end to end with fakes: module + KB Grounding produces a reviewable Storyboard, the user reviews it, `POST /videos/generate` renders the reviewed Storyboard predictably, and the completed job returns a final video URL plus provenance.

This is the final tracer bullet after the focused slices land.

## Acceptance criteria

- [ ] A high-level smoke flow covers module + KB -> reviewable Storyboard -> reviewed render request -> completed video job.
- [ ] The smoke path verifies teaching metadata survives from Storyboard generation into the reviewed render request.
- [ ] The smoke path verifies the final job result contains a video URL and lightweight provenance.
- [ ] The smoke path uses fakes for external providers and does not require real Veo, Imagen, TTS, Supabase Storage, or Remotion.
- [ ] Tests are written first at the highest API/UI seam that can prove the integrated behavior.

## Blocked by

- 02-module-goal-kb-grounding-storyboard-generation.md
- 03-visual-guardrails-for-educational-scenes.md
- 04-storyboard-review-ui-with-teaching-intent.md
- 05-reviewed-storyboard-drives-predictable-render.md
- 06-render-artifact-retention-and-720p-mvp-output.md

## TDD seam

High-level API/UI smoke flow with fakes.

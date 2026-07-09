Status: ready-for-agent

# PRD: Video de Explicacion Conceptual

## Problem Statement

The current generated video output does not reliably feel like an educational video. It often starts with a generic Veo-style network-of-blue-lights intro, follows with static generated imagery, random Remotion widgets, or a generic Playwright capture, and fails to teach the module concept in a clear, memorable way.

The user wants the video to be grounded in the Objetivo Pedagogico del Modulo and, when available, in the KB. The final render should feel like a deliberate Concept Explanation Video: useful, reviewable, and predictable before Cloud Run spends time and money generating assets.

## Solution

Create a higher-quality video generation workflow centered on Video de Explicacion Conceptual.

The storyboard generator will use the module title and description as the spine of the teaching goal, use KB Grounding as evidence and examples, and produce 5-7 strong scenes with explicit teaching intent. It will choose Patrones Didacticos before choosing Remotion visual types, preferring the Paleta Visual MVP over decorative generated assets.

The Revisión de Storyboard will expose enough information for a human to catch bad videos before render: each scene's teaching point, visual type, narration, and visual rationale. The render step will then materialize the reviewed Storyboard predictably.

## User Stories

1. As an instructional designer, I want the generated video to teach the module concept, so that learners understand the point of the module.
2. As an instructional designer, I want the module title and description to drive the video, so that the Storyboard does not drift into a random KB summary.
3. As an instructional designer, I want KB chunks to provide evidence and examples, so that generated narration stays grounded when source material exists.
4. As an instructional designer, I want the system to say when a Storyboard is Module-grounded instead of KB-grounded, so that I know how much evidence supports it.
5. As an instructional designer, I want each scene to show its teaching point, so that I can judge whether the scene belongs in the video.
6. As an instructional designer, I want to see why a visual type was chosen, so that I can catch decorative or misleading visuals.
7. As an instructional designer, I want to edit narration before render, so that I can correct tone and clarity cheaply.
8. As an instructional designer, I want to correct bad visual choices before render, so that I do not waste Veo, Imagen, TTS, or Cloud Run time.
9. As an instructional designer, I want fewer but stronger scenes, so that the video feels coherent instead of busy.
10. As an instructional designer, I want videos around 90-120 seconds, so that learners get a concise explanation without filler.
11. As a learner, I want the video to start with a real question, contrast, or mental model, so that I immediately understand why the concept matters.
12. As a learner, I want comparisons to show meaningful differences, so that I can distinguish weak and strong approaches.
13. As a learner, I want progress visuals to explain a process or sequence, so that I can follow the concept step by step.
14. As a learner, I want callouts to highlight rules, warnings, or definitions, so that I can remember the key idea.
15. As a learner, I want terminal scenes only when there is a real command or worked example, so that procedural content feels concrete.
16. As a learner, I want screenshot walkthroughs only when they show a specific UI action, so that browser captures are not empty decoration.
17. As a learner, I want generated illustrations only when they explain a mental model or architecture, so that still images help me understand instead of filling time.
18. As a learner, I want Veo clips only when a metaphor clarifies the concept, so that generated video does not become a generic intro.
19. As a product owner, I want Remotion widgets to be selected through Patrones Didacticos, so that visual variety supports learning.
20. As a product owner, I want charts to require real or explicitly illustrative values, so that the video does not invent fake metrics.
21. As a product owner, I want the Storyboard review to happen before expensive render work, so that quality control happens early.
22. As a product owner, I want the render to be predictable after approval, so that the final MP4 matches what was reviewed.
23. As a platform operator, I want only the final MP4 and lightweight provenance persisted by default, so that Supabase Storage costs stay controlled.
24. As a platform operator, I want MVP renders to default to 720p H.264, so that Cloud Run render time and storage transfer stay reasonable during iteration.
25. As a developer, I want a clear Storyboard schema for teaching intent and visual rationale, so that backend and frontend agree on what is being reviewed.
26. As a developer, I want tests at the storyboard endpoint seam, so that behavior is verified without depending on provider internals.
27. As a developer, I want tests from Storyboard to video job creation, so that the reviewed Storyboard is the actual render input.
28. As a developer, I want fallback behavior for weak KB Grounding, so that the product remains usable without pretending to cite sources.
29. As a reviewer, I want failed or debug renders to optionally preserve intermediate assets briefly, so that visual problems can be diagnosed.
30. As a reviewer, I want successful renders to keep lightweight provenance, so that I can understand what was generated without storing every temporary file.

## Implementation Decisions

- The primary product concept is Video de Explicacion Conceptual.
- The Storyboard generator will target 5-7 strong scenes and 90-120 seconds by default.
- The module title and description define the Objetivo Pedagogico del Modulo; `module.tipo` is a soft hint for tone and structure.
- KB Grounding supplies evidence, examples, citations, and allowed vocabulary.
- The generator must distinguish Storyboard KB-grounded from Storyboard Module-grounded.
- The generator should produce scene-level teaching metadata: teaching point, pedagogical intent, teaching pattern, visual rationale, and grounding status.
- The generator should choose Patrones Didacticos before Remotion Tipos Visuales.
- The Paleta Visual MVP is first-class: `comparison`, `progress_bar`, `callout`, `text_card`, `terminal_scene`, `screenshot_scene`.
- `ai_video` is optional, at most once, and only for a meaningful teaching metaphor.
- `ai_illustration` is conditional on a concrete mental model or architecture diagram.
- Quantitative chart widgets require evidenced values or explicit illustrative labeling.
- `screenshot_scene` requires a Walkthrough Didactico: URL, purpose, ordered UI steps, and learning outcome.
- The Storyboard review UI must show teaching point, visual type, narration, and visual rationale.
- The render pipeline should execute an approved Storyboard predictably, with minimal invention during render.
- The final Video Asset Renderizado is the source of truth in Supabase Storage.
- Default artifact retention keeps final MP4, Storyboard, render settings, lightweight provenance, citations or Grounding IDs, and optionally a poster thumbnail.
- Intermediate TTS files, screenshots, Imagen PNGs, Veo clips, and Remotion copies are temporary by default.
- Debug or failed-job diagnostics may retain intermediates with explicit short retention.
- MVP render quality defaults to 720p H.264 MP4; higher quality is an explicit publish/high-quality render mode.
- The current older PRD remains historical context; this PRD supersedes the quality strategy for new Concept Explanation Video work.

## Testing Decisions

- Test external behavior rather than implementation details. Tests should assert the Storyboard output contract and render-job input behavior, not exact prompts or private helper calls.
- Primary seam: `POST /videos/storyboard`. Given a module and useful KB Grounding, it should return a Storyboard with 5-7 scenes, teaching metadata, appropriate visual choices, and `KB-grounded` status.
- Fallback seam: `POST /videos/storyboard`. Given no useful KB Grounding, it should return a Module-grounded Storyboard, avoid fake citations, and prefer Visuales Didacticos Cualitativos.
- Render seam: `POST /videos/generate`. Given a reviewed `custom_storyboard`, the video job should use that Storyboard as the render input without regenerating the creative plan.
- Validation seam: Storyboard scenes using `screenshot_scene` should require URL, purpose, ordered steps, and learning outcome.
- Validation seam: chart visual types should require evidenced or explicitly illustrative values.
- Frontend seam: the video storyboard page should render teaching point, visual type, narration, and visual rationale for review.
- Existing prior art includes API tests around `/videos/generate`, KB service tests for grounded chunks with citations, and video service harness behavior for Storyboard-to-render flow.
- Provider-specific calls to Veo, Imagen, TTS, and Remotion should be covered with mocks/fakes in ordinary tests; real provider testing belongs in separate smoke tests or manual environment checks.

## Out of Scope

- Replacing Remotion as the composition engine.
- Building a full visual editor for every Remotion config field.
- Implementing long-form video reuse or transcript segmentation.
- Solving all Supabase Storage cost modeling beyond the default retention and 720p MVP decision.
- Changing the KB ingestion corpus rules.
- Reworking the entire asset approval lifecycle.
- Supporting every possible Remotion widget as first-class in the MVP.
- Guaranteeing deterministic provider output from Veo or Imagen.

## Further Notes

- This PRD follows ADR-0017 for quality strategy and ADR-0016 for render artifact retention and default render quality.
- ADR-0017 refines ADR-0012: the previous 8-12 scene rule solved static-screen pacing, but the new target is 5-7 stronger teaching scenes.
- The immediate implementation risk is contract drift: the frontend and backend need to agree on any new Storyboard metadata before relying on it in review.
- The current live frontend may still fall back to hardcoded Storyboard blocks when the `module_id` is not a backend UUID; that should be addressed as part of making the reviewed Storyboard real.

Status: ready-for-agent

## Parent

../PRD.md

## What to build

Implement the render artifact retention and default quality behavior from ADR-0016. Successful renders should persist the final MP4 and lightweight provenance by default, clean up temporary intermediate assets, and record 720p H.264 MVP render settings. Failed jobs or debug mode may retain intermediate assets with explicit short retention.

This slice should make the storage behavior observable from the completed video job and storage/provenance interfaces using fakes.

## Acceptance criteria

- [ ] Successful renders persist only the final MP4 and lightweight provenance by default.
- [ ] Temporary TTS files, screenshots, Imagen PNGs, Veo clips, and Remotion copies are cleaned up after successful render.
- [ ] Completed job provenance records render quality settings, defaulting to 720p H.264 MP4.
- [ ] Failed-job or debug retention behavior is explicit and short-lived.
- [ ] Tests are written first with fake storage/render collaborators at the completed video job seam.

## Blocked by

- 05-reviewed-storyboard-drives-predictable-render.md

## TDD seam

Completed video job result plus storage/provenance behavior with fake storage.

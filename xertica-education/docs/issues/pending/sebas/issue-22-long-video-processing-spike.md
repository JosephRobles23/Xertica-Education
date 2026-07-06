## Parent
None

## What to build
Research spike (throwaway prototype + written report) to assess the **viability and cost** of processing long-form training videos (e.g. ~2 hours) so they can be reused via timestamps + segmented transcripts (see Issue 19). Evaluate: transcription approach (self-hosted Whisper vs managed API), whether the transcription yields usable per-segment timestamps, storage/egress cost of keeping the source video + transcript index, and end-to-end latency for a real 2h video. Deliver a recommendation (self-host vs API, index format) that feeds the implementation of Issue 19.

## Acceptance criteria
- [ ] Report with viability, per-video cost estimate, and recommended approach.
- [ ] A throwaway prototype transcribes a real long video and shows segment-level timestamps.
- [ ] Decision recorded as an ADR (transcription approach + index format).

## Blocked by
None (informs Issue 19 — Existing Video Reuse)

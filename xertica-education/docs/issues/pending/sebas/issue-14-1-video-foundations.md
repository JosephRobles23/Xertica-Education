## Parent

[Issue 14 (Video Storyboard & Render)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-video-storyboard-render.md)

## What to build

Build the core FastAPI routing structure and service interface for video generation. Create endpoints:
1. `POST /videos/generate` that accepts a JSON payload representing a storyboard of scenes (standalone mode).
2. `GET /videos/jobs/{job_id}` to check rendering progress.

Implement `VideoService` with a `MockVideoService` implementation that dynamically transitions job statuses (queued -> running -> completed) and returns a mock MP4 url upon completion to decouple frontend work from backend rendering.

## Acceptance criteria

- [ ] Endpoint `POST /videos/generate` accepts a list of scenes and returns a `job_id`.
- [ ] Endpoint `GET /videos/jobs/{job_id}` returns progress updates conforming to `JobStatus` (queued, running, rendering, completed).
- [ ] The service implements a mock fallback returning a static placeholder video URL when the `use_mock` parameter is true.
- [ ] Unit tests verify DTO validation for the JSON storyboard schema.

## Blocked by

None - can start immediately

## Parent

[Issue 14 (Video Storyboard & Render)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-video-storyboard-render.md)

## What to build

Integrate the video service with the Supabase database. Update `POST /videos/generate` to accept an optional `component_id`.
When `component_id` is provided:
1. Lookup the Component and its related script/storyboard Asset in the database.
2. If no script/storyboard exists (because the editor skipped review), automatically invoke the scriptwriter LLM to generate the storyboard, save it in the database, and proceed directly to rendering.
3. Track and persist the rendering job state in the Supabase `jobs` table.

## Acceptance criteria

- [ ] Endpoint `/videos/generate` accepts `component_id` and looks up storyboard data from the database.
- [ ] If storyboard review was skipped, the system automatically triggers LLM script generation, saves the draft storyboard, and starts rendering.
- [ ] Job status updates are persisted in the Supabase database.

## Blocked by

- [Issue 14-1 (Video Service Foundations & Mock Rendering)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-1-video-foundations.md)

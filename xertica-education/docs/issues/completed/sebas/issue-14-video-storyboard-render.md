## Parent
None

## What to build
Build the video generation workflow pipelines. Expose `/video/storyboard/approve` to update rendering authorization state. Connect Next.js script review and storyboard scene slots on `/ruta/:id/video-storyboard` page. Implement the real renderer adapter `adapters/renderer/` to call the Google Veo REST API.

## Acceptance criteria
- [ ] UI shows script sections and scene cards correctly.
- [ ] Submitting storyboard approval triggers the Google Veo render pipeline in the backend.

## Blocked by
- [Issue 10 (KB & RAG Ingestion)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-10-kb-rag-ingestion.md)

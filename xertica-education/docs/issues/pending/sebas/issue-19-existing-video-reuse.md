## Parent
None

## What to build
Support ingesting, segmenting, and reusing existing training videos (e.g. 2-hour recordings) in the video production pipeline.
- **Backend:** Allow uploading/attaching an existing video source. Extract audio from the video file, run audio transcription (e.g., Whisper/Gemini), and pass the transcript to an LLM to segment it into timestamped sub-topics (e.g. topic name, transcript summary, start/end times).
- **Frontend:** Update the storyboard screen (`/ruta/:id/video-storyboard`) to display these segmented topics. Allow the user to select one of these existing video segments (mapping the start/end timestamps as the video asset source) instead of generating a new AI video with Veo.

## Acceptance criteria
- [ ] Backend extracts audio, transcribes, and segments a long video into timestamped sections.
- [ ] Storyboard UI displays transcript segments, allowing the user to select one for a module's video component.
- [ ] Generating/saving the module's video storyboard records the selected video segment's start/end timestamps and registers the segment as the approved video asset.

## Blocked by
- [Issue 10 (KB & RAG Ingestion)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/joseph/issue-10-kb-rag-ingestion.md)
- [Issue 14 (Video Storyboard & Render)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-video-storyboard-render.md)

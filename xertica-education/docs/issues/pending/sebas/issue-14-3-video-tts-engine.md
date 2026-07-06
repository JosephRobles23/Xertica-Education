## Parent

[Issue 14 (Video Storyboard & Render)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-video-storyboard-render.md)

## What to build

Implement the Text-to-Speech (TTS) pipeline using the Google Cloud Text-to-Speech Python SDK.
Create a `GoogleCloudTTSAdapter` that:
1. Receives narration text and synthesizes it to speech using premium WaveNet or Journey voices.
2. Saves the synthesized audio to a temporary file (e.g. `/tmp/scene_{i}.mp3`).
3. Extracts and returns the exact duration in seconds of the generated audio file.

## Acceptance criteria

- [ ] `GoogleCloudTTSAdapter` successfully connects to Google Cloud TTS API.
- [ ] Voice synthesis produces clear audio files saved in local `/tmp`.
- [ ] The system accurately calculates the duration of the synthesized audio file.

## Blocked by

- [Issue 14-1 (Video Service Foundations & Mock Rendering)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-1-video-foundations.md)

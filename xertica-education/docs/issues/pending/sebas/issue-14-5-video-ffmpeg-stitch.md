## Parent

[Issue 14 (Video Storyboard & Render)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-video-storyboard-render.md)

## What to build

Implement scene compilation and final assembly using FFmpeg.
For each scene:
1. Merge the scene's audio track (`scene_{i}.mp3`) and visual asset (`scene_{i}.png` or `scene_{i}.mp4`) using FFmpeg, matching the exact audio duration.
2. Concatenate all compiled scene video clips into a single final MP4.
3. Upload the final MP4 to the public `videos` bucket in Supabase Storage.
4. Update the component Asset status to `generado` and store the public URL.
5. Delete all temporary assets from `/tmp`.

## Acceptance criteria

- [ ] FFmpeg CLI successfully stitches audio and visuals on a per-scene basis.
- [ ] Multiple scenes are concatenated into a single, cohesive MP4 video.
- [ ] Finished video is uploaded to Supabase Storage and returns a reachable public URL.
- [ ] Local temporary directory `/tmp` is completely cleaned up after rendering completes.

## Blocked by

- [Issue 14-1 (Video Service Foundations & Mock Rendering)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-1-video-foundations.md)
- [Issue 14-3 (Google Cloud TTS Voiceover Engine)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-3-video-tts-engine.md)
- [Issue 14-4 (Playwright Slide & Walkthrough Capture)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-4-video-playwright-capture.md)

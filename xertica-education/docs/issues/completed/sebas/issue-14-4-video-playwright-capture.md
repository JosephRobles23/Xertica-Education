## Parent

[Issue 14 (Video Storyboard & Render)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-video-storyboard-render.md)

## What to build

Implement visual asset capture using headless Chrome via Playwright.
For each scene in the storyboard:
1. **Slides (`visual_type = slide`):** Compile a Jinja2 HTML/CSS template containing the slide title, code blocks, and bullet points, render it in Playwright, and capture a screenshot (`scene_{i}.png`).
2. **Walkthroughs (`visual_type = walkthrough`):** Launch Playwright, navigate to the target URL, perform actions if specified, and record the browser window/canvas to an MP4 video clip for the exact duration of the scene's voiceover audio.

## Acceptance criteria

- [ ] HTML slide templates are dynamically compiled and rendered to high-resolution PNG screenshots.
- [ ] Playwright records browser walkthroughs for the specified scene duration.
- [ ] All captured image and video files are saved in `/tmp` for subsequent processing.

## Blocked by

- [Issue 14-1 (Video Service Foundations & Mock Rendering)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/sebas/issue-14-1-video-foundations.md)

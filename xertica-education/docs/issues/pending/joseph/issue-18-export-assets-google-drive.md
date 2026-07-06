## Parent
None

## What to build
Build a Google Drive exporter and organizer for final generated assets.
- **Backend:** Implement automated sync to Google Drive when assets are marked approved at Gate 3. Automatically construct a folder hierarchy on Google Drive: `[Client Name] / [Learning Path Name] / [Module Name] / [Asset Name]`.
- **Frontend:** Expose "Export directly to Drive" buttons on both the module detail views and the final asset reviews tabbed UI (`/ruta/:id/asset-final`).

## Acceptance criteria
- [ ] Export trigger creates the structured directory layout on Google Drive dynamically.
- [ ] Approved asset files (Markdown/HTML lessons, JSON/PDF quizzes, PDF infographics, MP4 videos) are uploaded to their corresponding folders on Google Drive.
- [ ] UI displays export status badges indicating successful sync to Drive.

## Blocked by
- [Issue 15 (Gate 3 Asset Review & E2E Demo)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/shared/issue-15-gate-3-asset-review-e2e.md)

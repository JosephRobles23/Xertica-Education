## Parent
None

## What to build
Build a quick-win zip packager utility to download all generated assets of a single module.
- **Backend:** Create a FastAPI route `GET /learning-paths/{id}/modules/{module_id}/download` that gathers all approved assets of that module (Markdown/HTML lesson, Quiz JSON/PDF, Infographic PDF, and Video files), packages them into a single ZIP archive, and streams it back to the client.
- **Frontend:** Add a "Descargar Módulo" (Download Module) action button in the module's detail card/view.

## Acceptance criteria
- [ ] ZIP packager endpoint successfully aggregates all existing assets of a module and returns a standard zip archive.
- [ ] The UI triggers the ZIP download smoothly.
- [ ] Handles missing or partially generated assets gracefully (e.g. including only what is ready or displaying a tooltip warning).

## Blocked by
- [Issue 15 (Gate 3 Asset Review & E2E Demo)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/shared/issue-15-gate-3-asset-review-e2e.md)

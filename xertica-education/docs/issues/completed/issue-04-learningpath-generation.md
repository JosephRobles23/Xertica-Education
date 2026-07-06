## Parent
None

## What to build
Build backend API endpoint `POST /learning-paths/{id}/generate-structure` triggered from `workflows/pipelines/generate_module.py` shell. Wire frontend `/nueva-ruta` page to trigger generation and poll until the job completes, then redirect the user to `/estructura-propuesta`.

## Acceptance criteria
- [x] Pipeline generates a proposed structure (mocked modules/components).
- [x] Frontend successfully displays curriculum structure at `/estructura-propuesta`.

## Blocked by
- [Issue 03 (LearningPath CRUD)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-03-learningpath-crud.md)

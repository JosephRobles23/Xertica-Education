## Parent
None

## What to build
Build the learning path database repository (`repositories/learning_path/repository.py` and `interface.py`). Connect to Supabase Postgres to save/retrieve `LearningPath`, `Module`, and `Component` entities, replacing `LearningPathService` local mock state.

## Acceptance criteria
- [x] LearningPath structure modifications (e.g. module order, component toggles) persist in DB.
- [x] Backend API endpoints resolve data identically to mock phase.

## Blocked by
- [Issue 03 (LearningPath CRUD)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-03-learningpath-crud.md)
- [Issue 07 (Jobs Database Repository)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-07-jobs-database-repository.md)

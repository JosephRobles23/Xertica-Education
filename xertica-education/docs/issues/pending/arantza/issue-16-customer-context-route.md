## Parent
None

## What to build
Build a customer context intake form in the UI before route generation (on the `/nueva-ruta` page) requesting: Client URL, Industry, Area/Department (HR, Finance, IT, etc.), and Google Workspace usage (Yes/No). Update the backend schemas and database tables to store the `ClientContext` entity linked to a `LearningPath`. Incorporate these context fields into the LLM system prompt for the route structure/curriculum generation endpoint (`POST /learning-paths/{id}/generate-structure`) to customize and personalize the generated modules and components.

## Acceptance criteria
- [ ] UI collects URL, Industry, Area/Department, and Google Workspace usage before creating the path.
- [ ] Backend stores `ClientContext` and associates it with `LearningPath`.
- [ ] Route structure generation uses the context to generate a personalized module plan.

## Blocked by
- [Issue 04 (LearningPath Structure Generation - Mock)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/completed/issue-04-learningpath-generation.md)
- [Issue 08 (LearningPath Database Repository)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/completed/issue-08-learningpath-database-repository.md)

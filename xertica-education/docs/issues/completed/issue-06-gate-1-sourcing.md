## Parent
None

## What to build
Build workflow endpoint `POST /learning-paths/{id}/sourcing/approve` to lock sources and transition path state to `SOURCES_READY`. Integrate `/ruta/:id` page's `CorpusSection` to list mock references, allow individual deletions/discards, and submit approved sources to trigger pgvector RAG compilation mock.

## Acceptance criteria
- [x] UI shows candidates sources list.
- [x] Approving corpus updates status to `SOURCES_READY` in backend.

## Blocked by
- [Issue 05 (Gate 0 Curriculum Approval)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-05-gate-0-curriculum-approval.md)

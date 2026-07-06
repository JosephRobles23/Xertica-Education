## Parent
None

## What to build
Integrate Google Drive file ingestion into the sourcing workflow.
- **Frontend:** Add a Google Drive file picker in the sourcing view (`/ruta/:id`) to allow selecting reference documents.
- **Backend:** Fetch files from Google Drive using the Drive API, register them as `Source` entities in Supabase, and feed them into the document parser (`adapters/parser/`) and vector ingestion pipeline (`KBService`).

## Acceptance criteria
- [ ] UI allows selecting reference files from Google Drive.
- [ ] Selected files are retrieved by the backend and successfully indexed in the pgvector database.
- [ ] RAG queries successfully retrieve facts grounded in Google Drive sources with correct citations.

## Blocked by
- [Issue 06 (Gate 1 Sourcing)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/completed/issue-06-gate-1-sourcing.md)
- [Issue 09 (Sourcing Database Repository)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/arantza/issue-09-sourcing-database-repository.md)
- [Issue 10 (KB & RAG Ingestion)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/pending/joseph/issue-10-kb-rag-ingestion.md)

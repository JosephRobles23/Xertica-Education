## Parent
None

## What to build
Build the FastAPI HTTP routes `/routers/jobs.py` exposing `POST /jobs` (returns a job_id) and `GET /jobs/{id}` (returns job details). Set up the mock `JobsService` class. Integrate the Next.js frontend centralised fetch client wrapper and polling mechanism.

## Acceptance criteria
- [x] POST `/jobs` returns a generated UUID job ID.
- [x] GET `/jobs/{id}` returns the job state changes correctly over time.
- [x] Frontend reads `NEXT_PUBLIC_API_URL` and polls correctly.

## Blocked by
- [Issue 01 (Foundation)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-01-foundation.md)

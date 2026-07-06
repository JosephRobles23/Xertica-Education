## Parent
None

## What to build
Build the jobs database repository (`repositories/jobs/repository.py` and `interface.py`). Connect to Supabase Postgres (using SQLModel or SQLAlchemy) and persist/read Job rows, replacing `JobsService` in-memory mock storage. Keep contracts and frontend unchanged.

## Acceptance criteria
- [ ] Job entries and updates persist inside Supabase database.
- [ ] API endpoints resolve jobs exactly as in the mock phase.

## Blocked by
- [Issue 02 (Infrastructure Tracer Bullet)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-02-infrastructure-tracer.md)

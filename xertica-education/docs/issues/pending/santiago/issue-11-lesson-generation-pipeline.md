## Parent
None

## What to build
Build the module pipeline `workflows/pipelines/generate_lesson.py`. Replace lesson mock generation with real LLM completion calls in `LessonService` leveraging `adapters/llm/` (OpenRouter/Vertex). Prompts must be grounded in the pgvector KB.

## Acceptance criteria
- [ ] Pipeline triggers lesson generation using grounding data.
- [ ] Returns generated lesson content citing correct sources.

## Blocked by
- [Issue 10 (KB & RAG Ingestion)](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/docs/issues/issue-10-kb-rag-ingestion.md)

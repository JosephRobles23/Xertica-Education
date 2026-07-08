# Xertica Education — API

FastAPI backend for Xertica Education.

## Deep Research YouTube Search

Deep Research uses the YouTube Data API when `YOUTUBE_API_KEY` is present in
`apps/api/.env`. If the key is missing or the API call fails, the service keeps
using the deterministic mock registry so the product flow remains testable.

```bash
YOUTUBE_API_KEY=your-youtube-data-api-key
```

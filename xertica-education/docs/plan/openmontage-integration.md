# Plan: OpenMontage Integration for Xertica Education Video Pipeline

> **Estado:** Aprobado para implementación
> **Decide:** sebas (Video) + Producto
> **Fecha:** 2026-07-07
> **Originado en:** Sesión de grilling con /domain-modeling

---

## Summary

Replace the current FFmpeg-based video composition with **Remotion** (via OpenMontage's Animated Explainer architecture). Keep existing adapters (Google TTS, Imagen, Veo, OpenRouter). Add Pixabay background music, word-level subtitles, and expand from 5 to 14 visual types. No human-in-the-loop gates. Deterministic orchestration with a declarative Render Plan.

## Architecture

```
Storyboard (LLM-generated, 14 visual types)
    ↓
RenderPlan (Pydantic model — declarative stage list)
    ↓
RenderExecutor runs stages:
  1. TTS (existing GoogleCloudTTSAdapter + extract word timestamps)
  2. Visual generation (existing Veo/Imagen adapters + Playwright screenshots)
  3. Background music (NEW — Pixabay Music tool)
  4. Transformation (storyboard → edit_decisions.json for Remotion)
  5. Remotion render (subprocess: npx remotion render ...)
  6. Post-render validation (ffprobe, frame sampling)
  7. Upload (existing SupabaseStorageAdapter)
    ↓
Final MP4 (Video Asset Renderizado)
```

---

## Resolved decisions (from grilling session)

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Integration mode | Option C — deterministic orchestration, keep `VideoService` as orchestrator | Server can't host interactive agent; deterministic is testable, mockable, cheap |
| 2 | Render Plan abstraction | Yes — declarative plan separate from executor | Enables future migration to LangGraph/ADK without rewriting logic |
| 3 | Composition engine | Remotion (Animated Explainer pipeline, no human gates) | 16 pre-built scene types, spring animations, word-level captions, native audio |
| 4 | Visual types | Expand from 5 to 14 | 5-block mold is why videos feel weak; Remotion's palette makes them impressive |
| 5 | Playwright | Keep for screenshot capture only (fix URL selection) | User wants real websites (Google Cloud docs, product pages) animated by Remotion |
| 6 | Scriptwriter context | Full learning path context (topic, sources, objective, module structure) | Current prompt gives zero context — every video is generic |
| 7 | Adapter strategy | Keep existing adapters (option A) | TTS, Imagen, Veo all work; biggest wins come from Remotion, not provider swaps |
| 8 | Image provider | Keep Imagen (no new API keys) | OpenRouter is LLM-only; user doesn't want new API keys |
| 9 | Background music | Pixabay Music (free API key) | Current static file is weak; Pixabay is free, searchable by mood |
| 10 | Subtitles | TTS timestamps (word-level timing) | Perfect accuracy for synthetic speech; no extra dependencies |
| 11 | Theme | `flat-motion-graphics` (default) | Matches current dark navy/purple palette; Space Grotesk font |
| 12 | OpenMontage integration | Git submodule | Isolated from other 3 developers; deployment-controlled; forkable |

---

## Visual types vocabulary (14 types)

| Visual type | Remotion scene | Source | Notes |
|---|---|---|---|
| `text_card` | TextCard | Remotion native | Replaces `slide` + `animated_slide` |
| `hero_title` | HeroTitle | Remotion native | Per-character spring animation for intros |
| `stat_card` | StatCard | Remotion native | Big number with subtitle (e.g., "8.1B people") |
| `callout` | CalloutBox | Remotion native | Boxed message (info/warning/tip/quote) |
| `comparison` | ComparisonCard | Remotion native | Side-by-side comparison ("before vs after") |
| `bar_chart` | BarChart | Remotion native | Animated bar chart for data comparisons |
| `line_chart` | LineChart | Remotion native | Animated line chart for trends over time |
| `pie_chart` | PieChart | Remotion native | Pie/donut chart for proportions |
| `kpi_grid` | KPIGrid | Remotion native | 2-4 column KPI grid for dashboards |
| `progress_bar` | ProgressBar | Remotion native | Animated progress bar for process flows |
| `terminal_scene` | TerminalScene | Remotion native | Synthetic terminal with typing animation (replaces `walkthrough` for CLI) |
| `screenshot_scene` | ScreenshotScene | Remotion native | Synthetic UI recording with cursor/click/typing overlays (replaces `walkthrough` for web) |
| `ai_video` | Video cut | Veo adapter | Play Veo 3.1 MP4 directly |
| `ai_illustration` | Image cut with Ken Burns | Imagen adapter | Imagen PNG with Remotion Ken Burns/parallax |

### Retired visual types

| Old type | Replaced by |
|---|---|
| `slide` | `text_card` |
| `animated_slide` | `text_card` (spring animations are native to Remotion) |
| `walkthrough` | `screenshot_scene` (web) or `terminal_scene` (CLI) |

---

## Phase 1: Foundation — OpenMontage + Remotion setup

### 1.1 Add OpenMontage as git submodule
- **New:** `openmontage/` at repo root (git submodule pinned to a specific commit)
- Add to `.gitmodules`
- Document `git submodule update --init --recursive` in README

### 1.2 Set up Remotion composer
- **New:** `apps/api/remotion/` — copy or symlink `openmontage/remotion-composer/`
- Install Node.js deps: `cd apps/api/remotion && npm install`
- Add `package.json` scripts for rendering
- **Deployment concern:** Server needs Node.js 18+ and npm

### 1.3 Add OpenMontage Python tools to import path
- Add `openmontage/` to Python path in `apps/api/config/settings.py` or `sys.path`
- Import only specific tools:
  - `tools.audio.audio_mixer.AudioMixerTool`
  - `tools.audio.pixabay_music.PixabayMusicTool` (or similar name)
  - `tools.video.video_stitch.VideoStitchTool` (if needed for fallback)
- **Do NOT call `tool_registry.discover()`** — import specific tools directly (avoids walking all 52 modules)

### 1.4 Settings/config changes
- **Edit:** `apps/api/config/settings.py` — add Pixabay API key field
- **Edit:** `apps/api/.env.example` — add `PIXABAY_API_KEY`
- Add Remotion paths config (where the composer lives, where to write props JSON, where to output MP4)

---

## Phase 2: Storyboard + Scriptwriter model

### 2.1 New Pydantic models for expanded visual types
- **Edit:** `apps/api/models/dto/requests.py`
- Replace bare `visual_type: str` with an enum (or Literal) of 14 types:
  ```python
  VisualType = Literal[
      # Remotion native scenes
      "text_card", "hero_title", "stat_card", "callout",
      "comparison", "bar_chart", "line_chart", "pie_chart",
      "kpi_grid", "progress_bar",
      "terminal_scene", "screenshot_scene",
      # Asset-based scenes
      "ai_video", "ai_illustration",
  ]
  ```
- Update `visual_config: dict` with typed sub-models per visual type (optional but ideal)
- Update `StoryboardRequest` and `VideoScene`

### 2.2 Rewrite the LLM scriptwriter prompt
- **Edit:** `apps/api/services/video/service.py` — replace `SCRIPTWRITER_SYSTEM_PROMPT` (lines 53-109)
- New prompt must:
  - Teach all 14 visual types with examples of when to use each
  - Specify `visual_config` schema per type (chart data, comparison values, stat numbers, screenshot URLs, terminal steps)
  - Include a "visual storytelling" section (think like a video editor, not a text writer)
  - Receive full learning path context: topic, objective, verified source URLs, module structure, lesson content
  - Pick the right URL for screenshot scenes from verified sources (not hallucinate)
  - Produce Remotion-compatible `visual_config` that maps directly to cut schema
  - 3Blue1Brown / Johnny Harris quality bar — progressive reveals, visual metaphors, data-driven beats

### 2.3 Update `_get_or_create_storyboard` to pass learning path context
- **Edit:** `apps/api/services/video/service.py` — lines 251-318
- Currently the LLM gets zero context ("component with ID X")
- New version queries the route, module, component, and sources from Supabase
- Passes structured context to the scriptwriter prompt:
  - Route name, objective, topic, brief
  - Module type (intro/capsula/lab/evaluacion/cierre)
  - Lesson sections (headings, body text)
  - Verified source URLs (for screenshot scene URL selection)

---

## Phase 3: Render Plan + Render Executor

### 3.1 New Render Plan Pydantic model
- **New file:** `apps/api/models/dto/render_plan.py`
- Defines:
  ```python
  class RenderStage(BaseModel):
      stage_type: Literal["tts", "visual", "music", "transform", "remotion_render", "validate", "upload"]
      inputs: dict
      outputs: dict
      status: JobStatus

  class RenderPlan(BaseModel):
      job_id: UUID
      storyboard: StoryboardRequest
      stages: List[RenderStage]
      edit_decisions: Optional[dict] = None  # built during transform stage
  ```
- This is the declarative plan — separate from execution

### 3.2 New RenderExecutor service
- **New file:** `apps/api/services/video/executor.py`
- Replaces the current `_run_render_job` method in `service.py`
- Runs stages in sequence, updates job status after each
- Catches per-stage failures, retries or falls back
- Writes the `RenderPlan` to the job record for auditability

### 3.3 Storyboard → edit_decisions transformation
- **New file:** `apps/api/services/video/transformer.py`
- Maps each visual type to a Remotion cut:
  - `text_card` → `{ "type": "text_card", "text": ..., "subtitle": ... }`
  - `hero_title` → `{ "type": "hero_title", "text": ... }`
  - `stat_card` → `{ "type": "stat_card", "stat": ..., "subtitle": ... }`
  - `bar_chart` → `{ "type": "bar_chart", "chartData": [...], "title": ... }`
  - `comparison` → `{ "type": "comparison", "leftLabel": ..., "leftValue": ..., "rightLabel": ..., "rightValue": ... }`
  - `screenshot_scene` → `{ "type": "screenshot_scene", "backgroundImage": ..., "screenshotSteps": [...] }`
  - `terminal_scene` → `{ "type": "terminal_scene", "steps": [...] }`
  - `ai_video` → `{ "source": "veo_clip.mp4", "animation": "ken-burns" }`
  - `ai_illustration` → `{ "source": "imagen.png", "animation": "parallax" }`
- Calculates `in_seconds` and `out_seconds` from TTS durations
- Adds `theme: "flat-motion-graphics"`
- Adds `audio` config (narration + music with fade curves)
- Adds `captions` array (word-level timing from TTS)

### 3.4 Remotion render via subprocess
- **Edit:** `apps/api/services/video/executor.py`
- After transformation, write `edit_decisions.json` to a temp file
- Stage assets to `remotion/public/` (copy images, videos, audio)
- Invoke:
  ```
  npx remotion render src/index.tsx Explainer output.mp4 --props edit_decisions.json --codec h264
  ```
- Set `cwd` to the Remotion composer directory
- Timeout: 300s per render
- **On failure: return structured error (do NOT fall back to FFmpeg — Remotion is the commitment)**

### 3.5 Update VideoService to use RenderExecutor
- **Edit:** `apps/api/services/video/service.py`
- Replace `_run_render_job` (lines 435-851) with a call to `RenderExecutor.execute(plan)`
- Keep `generate_video`, `get_video_job_status`, `segment_video` — they stay the same
- Remove the entire FFmpeg composition code (crossfade math, Ken Burns, audio mixing via FFmpeg)
- Keep `MockVideoService` unchanged (ADR-0002 — mocks are mandatory)
- **Edit:** Create a new `MockRenderExecutor` or have the existing mock delegate appropriately

---

## Phase 4: Audio + Subtitles

### 4.1 Extract word-level timing from TTS
- **Edit:** `apps/api/adapters/audio/google_tts.py`
- Google Cloud TTS returns `timepoints` in the response — extract them
- Return both the audio file path AND a list of `{word, startMs, endMs}` from `text_to_speech()`
- **Edit:** Update the TTS adapter interface if needed (return a tuple or dataclass)

### 4.2 Pixabay Music integration
- **New file:** `apps/api/adapters/audio/pixabay_music.py`
- Uses OpenMontage's `tools/audio/pixabay_music.py` tool (or reimplements the API call directly if simpler)
- Searches Pixabay by mood/genre ("corporate", "educational", "ambient")
- Downloads a royalty-free track to a local path
- Needs `PIXABAY_API_KEY` in settings

### 4.3 Audio mixing (Remotion native, no FFmpeg)
- **No separate audio mixing step needed** — Remotion handles this natively
- The `edit_decisions.json` `audio` config tells Remotion:
  - Narration track (volume 1.0)
  - Music track (volume 0.12, fadeIn 2s, fadeOut 3s)
- Remotion's `<Audio>` component handles ducking via volume curves
- If we need sidechain ducking later, we can use OpenMontage's `audio_mixer.py` tool as a post-processing step, but Remotion native is simpler first

### 4.4 Subtitles
- The transformation layer (3.3) adds the `captions` array to `edit_decisions.json`
- Remotion's `CaptionOverlay` component renders word-level highlighting
- No separate FFmpeg subtitle burn needed

---

## Phase 5: Playwright fixes

### 5.1 Fix URL selection for screenshot scenes
- **Edit:** `apps/api/adapters/renderer/playwright_capture.py`
- The `capture_walkthrough` method currently takes a URL from `visual_config`
- Add a new method `capture_screenshot(url, output_path, element_selector=None)` — takes a deterministic screenshot of a single page
- Wait for specific elements to load (not just a fixed timeout)
- Capture the full page or a specific region
- No interaction, no clicking, no scrolling — just a clean screenshot

### 5.2 Frontend URL selection
- **Edit:** `apps/web/src/modules/video/Storyboard.tsx`
- The `firstWalkthroughUrl` function (line 29) picks the first source URL blindly
- Replace with logic that picks the most relevant source based on the scene's topic
- Or: pass all verified source URLs to the LLM scriptwriter and let it pick the best one per scene

---

## Phase 6: Frontend (minimal changes)

### 6.1 Storyboard.tsx visual type display
- **Edit:** `apps/web/src/modules/video/Storyboard.tsx`
- Update the `ScriptBlock` type (line 23) to include all 14 visual types
- The `buildScriptBlocks` function (line 32) currently hardcodes 5 blocks — this should eventually become dynamic (LLM-generated), but for now, keep the hardcoded structure and just update the type union
- The storyboard display (lines 528-551) shows a badge with the visual type — no change needed except the type union

### 6.2 Editing UI (future phase)
- Optional: Add a visual type picker dropdown when editing a script block
- Optional: Show a preview of what each visual type looks like
- **Defer to a future phase** — the default flow is auto-generation
- User vision: storyboard editing is optional but powerful. Users can accept the LLM's auto-generated choices and just hit "generate," or they can dive in and customize everything.

---

## Phase 7: Documentation

### 7.1 CONTEXT.md updates
- **Edit:** `CONTEXT.md`
- Add term: **Tipo Visual / Visual Type** (expanded to 14 types, aligned with Remotion scene types)
- Add term: **Subtítulos / Captions** (word-level timing from TTS, rendered by Remotion CaptionOverlay)
- Add term: **OpenMontage** (external video production toolkit, integrated as git submodule)
- Confirm definitions for: **Render Plan / Render Executor / Render Stage** (already added during grilling session)
- Update the "Estados de un Job" section if the stage transitions change

### 7.2 ADRs to create
- **New:** `docs/adr/0007-declarative-render-plan.md` — why we split plan from execution
- **New:** `docs/adr/0008-remotion-composition-engine.md` — why Remotion (not HyperFrames or FFmpeg), no human gates
- **New:** `docs/adr/0009-expanded-visual-types.md` — why we expanded from 5 to 14 visual types, the trade-off (more upfront work vs. impressive videos)
- **New:** `docs/adr/0010-openmontage-git-submodule.md` — why submodule (not pip install or copy files), isolation for 4-developer team

---

## Execution Order

```
Phase 1 (Foundation)
  ├── 1.1 Git submodule
  ├── 1.2 Remotion npm install
  └── 1.3 Python import path
       ↓
Phase 2 (Model + Prompt)
  ├── 2.1 VisualType enum
  ├── 2.2 New scriptwriter prompt
  └── 2.3 Context injection
       ↓
Phase 3 (Render Pipeline) ← core work
  ├── 3.1 RenderPlan model
  ├── 3.2 RenderExecutor
  ├── 3.3 Transformer
  └── 3.4 Remotion subprocess
       ↓
Phase 4 (Audio + Subtitles)
  ├── 4.1 TTS timestamps
  ├── 4.2 Pixabay music
  └── 4.4 Captions in edit_decisions
       ↓
Phase 5 (Playwright fixes)
  └── 5.1 Screenshot capture
       ↓
Phase 6 (Frontend — minimal)
  └── 6.1 Type union update
       ↓
Phase 7 (Docs — throughout)
  ├── 7.1 CONTEXT.md
  └── 7.2 ADRs
```

---

## What gets removed

| File / Code | Lines | Why |
|---|---|---|
| FFmpeg composition code in `service.py` | 557-632 | Ken Burns, crossfade math, concatenation — replaced by Remotion |
| FFmpeg audio mixing code | 761-786 | Replaced by Remotion native audio |
| `PlaywrightAdapter.capture_animated_slide` | — | Replaced by Remotion native text_card |
| `PlaywrightAdapter.capture_illustrated_slide` | — | Replaced by Remotion native scenes |
| Buggy crossfade offset calculation | 677-683 | Remotion handles transitions natively |

## What stays

| File / Adapter | Why |
|---|---|
| `GoogleCloudTTSAdapter` | Works — keep it, add timestamp extraction |
| `GoogleVeoAdapter` | Works (confirmed from video analysis) — keep it |
| `GoogleImagenAdapter` | Keep (user doesn't want new API keys) |
| `OpenRouterLLMAdapter` | Works — keep it, upgrade the scriptwriter prompt |
| `SupabaseStorageAdapter` | Works — keep it |
| `MockVideoService` | Keep (ADR-0002: mocks are mandatory) |
| `PlaywrightCaptureAdapter` | Keep for screenshots only, fix URL selection, remove slide/animated methods |

---

## Future phases (out of scope for this plan)

- **Batch generation:** When user approves route structure, kick off video generation for all modules at once
- **ADK / LangGraph migration:** If we want adaptive provider selection or LLM-driven failure recovery, migrate `RenderExecutor` to LangGraph graph nodes (plan is already structured for this)
- **Custom Remotion components:** 3Blue1Brown-style mathematical animations require bespoke React components (OpenMontage's atelier mode)
- **Frontend visual type picker:** Let users pick visual types per scene in the storyboard UI
- **ElevenLabs / FLUX / Runway providers:** Add via OpenMontage's scored selector when ready
- **Antigravity SDK:** Revisit if it matures and we want agent orchestration
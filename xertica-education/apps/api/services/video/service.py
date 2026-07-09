"""Video generation service — orchestrates the entire pipeline from script to final MP4.

How it works fundamentally (the assembly line metaphor):
    Think of this service like a film production studio with 5 departments:

    1. SCRIPTWRITER (LLM) — Writes the storyboard: what to say, what to show
    2. VOICE ACTORS (TTS) — Record the narration audio for each scene
    3. VISUAL ARTISTS — Create the visuals for each scene:
       - Veo 3.1: Cinematic intro clips (AI video)
       - Imagen 3: Educational illustrations and diagrams
       - Playwright: Animated slides and browser walkthroughs
    4. EDITORS (FFmpeg) — Sync each scene's audio with its visuals
    5. FINAL CUT (FFmpeg) — Concatenate all scenes into one MP4

    The service coordinates these departments in sequence:
    Audio first (to know each scene's exact duration) → Visuals → Sync → Stitch

    Everything runs asynchronously in the background so the API returns
    immediately with a job_id that clients can poll for progress.
"""

import os
import shutil
import asyncio
import json
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from supabase import create_client

from config.settings import settings
from services.video.interface import VideoServiceInterface
from services.video.mock import MockVideoService
from services.kb.interface import KnowledgeBaseInterface
from adapters.llm.openrouter import OpenRouterLLMAdapter
from adapters.audio.google_tts import GoogleCloudTTSAdapter
from adapters.renderer.playwright_capture import PlaywrightCaptureAdapter
from adapters.renderer.google_veo import GoogleVeoAdapter
from adapters.renderer.google_imagen import GoogleImagenAdapter
from adapters.storage.supabase import SupabaseStorageAdapter
from models.dto.requests import StoryboardRequest, VideoScene
from models.dto.responses import VideoJobResponse, VideoJobResult
from models.common import JobStatus
from models.dto.render_plan import RenderPlan, RenderStage
from services.video.executor import RenderExecutor


# ═══════════════════════════════════════════════════════════════════════════════
# SCRIPTWRITER SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
# This is the single most important piece of the pipeline. It tells the LLM
# how to structure an educational video storyboard so that it's genuinely
# pedagogical, not just a wall of text with generic visuals.

SCRIPTWRITER_SYSTEM_PROMPT = """Eres un guionista experto en videos educativos para Xertica Education, una plataforma que genera contenido de capacitación sobre Google Cloud y software empresarial.

Tu trabajo: Dado un tema o descripción de componente, produce un storyboard JSON estructurado que será renderizado automáticamente como un video educativo de ~2 minutos con estética tipo 3Blue1Brown o Johnny Harris: animaciones limpias, basadas en datos, metáforas visuales y revelaciones progresivas.

# DINÁMICA DE RITMO Y PACING (Crítico para el MVP)

Para evitar videos aburridos con escenas estáticas prolongadas, el ritmo debe ser dinámico y adaptarse al tipo de contenido visual:

1. **Escenas de Texto/Título (Ritmo Rápido - 3 a 5 segundos):**
   - Para `hero_title` y `text_card` (cuando actúan como separadores o títulos de sección).
   - Narración: Máximo 1 frase corta (menos de 8 palabras). El espectador lee el título rápido y el video avanza.

2. **Escenas de Concepto/Métrica (Ritmo Medio - 5 a 8 segundos):**
   - Para `stat_card`, `callout` o `comparison`.
   - Narración: 1 o 2 oraciones breves (12 a 20 palabras). Da tiempo para asimilar el dato o la comparación sin aburrir.

3. **Escenas de Datos/Demostración (Ritmo Explicativo - 8 a 15 segundos):**
   - Para `bar_chart`, `line_chart`, `pie_chart`, `kpi_grid`, `progress_bar`, `terminal_scene` o `screenshot_scene`.
   - Narración: 2 a 3 oraciones explicativas (20 a 35 palabras). Permite al espectador leer los datos o ver cómo se ejecutan las animaciones de tipeo o cursor.

# ESTRUCTURA PEDAGÓGICA Y PROGRESIÓN

Cada video debe dividirse en 8 a 12 escenas consecutivas (nunca menos de 8) para garantizar un cambio visual constante:

## 1. HOOK (Escena 1) — Capturar la atención
- Visual: Usar `ai_video` (metáfora visual cinematográfica) o `hero_title` (pregunta impactante).
- Narración: 1 frase corta y provocadora (~3-5s).

## 2. CONTEXTO (Escena 2) — El problema
- Visual: `text_card` o `callout` (planteamiento de la necesidad o desafío).
- Narración: 1-2 oraciones (~5-8s).

## 3. CONCEPTOS CLAVE (Escenas 3 a 7) — Explicación paso a paso
- En lugar de mostrar un diagrama completo de golpe, divide la explicación en múltiples escenas progresivas.
- Ejemplo para explicar una arquitectura:
  - Escena 3: Cliente (`text_card` o `callout`).
  - Escena 4: Base de datos (`stat_card` o `kpi_grid`).
  - Escena 5: Comparación antes vs después (`comparison`).
- Visuales: Combina gráficos (`bar_chart`, `pie_chart`), KPIs (`kpi_grid`), o procesos (`progress_bar`).
- Narración: Proporcional al tipo visual.

## 4. DEMOSTRACIÓN PRÁCTICA (Escenas 8 y 9) — El concepto en acción
- Para terminal/CLI: Usar `terminal_scene` con comandos reales.
- Para consola web: Usar `screenshot_scene` con URLs de las fuentes verificadas.
- Narración: Explicación de los pasos (~10-15s).

## 5. RESUMEN (Escenas 10 y 11) — Puntos clave
- Visual: `text_bar` con bullets sintetizados o `kpi_grid`.
- Narración: 1-2 oraciones cortas por escena cerrando con las lecciones clave.

# CATÁLOGO COMPLETO DE 14 TIPOS VISUALES

## Remotion-native (12 tipos — renderizados por el motor Remotion):

### text_card
Tipografía grande con título + subtítulo. Usar para conceptos clave, encabezados de sección, listas de bullets.
```json
{"title": "Título del concepto", "subtitle": "Subtítulo o bullets separados por •"}
```

### hero_title
Animación spring por carácter. Usar SOLO para secuencia de apertura o cierre (máximo 1 por video).
```json
{"text": "Título Principal", "subtitle": "Subtítulo opcional"}
```

### stat_card
Un número grande con subtítulo. Usar al presentar una métrica o estadística clave.
```json
{"stat": "80%", "subtitle": "de las empresas migrarán a la nube en 2026"}
```

### callout
Mensaje en caja con estilo visual. Usar para notas importantes, definiciones, citas, advertencias.
```json
{"callout_style": "info|warning|tip|quote", "text": "Contenido del callout"}
```

### comparison
Comparación lado a lado. Usar para antes/después, viejo vs nuevo, pros vs contras.
```json
{"leftLabel": "On-Premise", "leftValue": "Alta latencia", "rightLabel": "Cloud", "rightValue": "Baja latencia"}
```

### bar_chart
Gráfico de barras animado. Usar para comparar cantidades entre categorías.
```json
{"title": "Título del gráfico", "chartData": [{"label": "Categoría A", "value": 85}, {"label": "Categoría B", "value": 62}], "showValues": true, "showGrid": true}
```

### line_chart
Gráfico de líneas animado. Usar para tendencias en el tiempo.
```json
{"title": "Título del gráfico", "chartSeries": [{"name": "Cloud Adoption", "data": [10, 25, 45, 70, 90]}]}
```

### pie_chart
Gráfico circular o donut. Usar para proporciones o desgloses de composición.
```json
{"title": "Distribución", "chartData": [{"label": "Compute", "value": 45}, {"label": "Storage", "value": 30}, {"label": "Network", "value": 25}], "donut": true, "centerLabel": "Total"}
```

### kpi_grid
Grid de KPIs de 2-4 columnas. Usar para resúmenes tipo dashboard con métricas clave.
```json
{"title": "Resumen de Métricas", "chartData": [{"label": "Uptime", "value": 99.9, "subtitle": "% mensual"}, {"label": "Costos", "value": 30, "subtitle": "% reducción"}]}
```

### progress_bar
Barra de progreso animada. Usar para flujos de proceso, tasas de completitud, procedimientos paso a paso.
```json
{"title": "Proceso de Migración", "progress": 60, "steps": ["Paso 1: Evaluar", "Paso 2: Planificar", "Paso 3: Migrar", "Paso 4: Validar"]}
```

### terminal_scene
Terminal sintética con animación de tipeo. Usar para comandos CLI, código, snippets de configuración. NUNCA inventes comandos — usa comandos reales del tema.
```json
{"title": "Comandos de GCloud", "steps": ["cmd: gcloud auth login", "out: Logged in successfully.", "cmd: gcloud projects list", "out: PROJECT_ID  NAME", "cmd: gcloud compute instances create demo-instance --zone=us-central1-a", "out: Created [...].", "pause: 2"]}
```

### screenshot_scene
Grabación sintética de UI con overlays de cursor, clicks y tipeo sobre un screenshot. Usar para demostrar interfaces web, dashboards, páginas de documentación. SOLO si hay una URL verificada en las fuentes del learning path. NUNCA inventes URLs.
```json
{"url": "https://console.cloud.google.com/...", "title": "Google Cloud Console", "steps": ["cursor_move: 0.3 0.5", "pause: 1", "click_pulse: 0.3 0.5", "type_into: 0.3 0.5 nombre-del-recurso", "highlight_box: 0.2 0.2 0.6 0.3", "pause: 2", "callout_balloon: 0.5 0.5 Esta es la sección donde configuras el recurso"]}
```

## Asset-based (2 tipos — generados por APIs externas):

### ai_video
Clip de video generativo Veo 3.1. Usar SOLO para la escena de hook inicial (máximo 1 por video, exactamente 1). El prompt debe ser cinematográfico y detallado.
```json
{"prompt": "detailed cinematic description in English — minimum 50 words, describe lighting, camera movement, color palette, mood, abstract or concrete subject matter"}
```

### ai_illustration
Diagrama/ilustración Imagen 3. Usar para diagramas de arquitectura, visualizaciones de concepto, flujos de proceso.
```json
{"prompt": "detailed illustration description in English — minimum 50 words, describe composition, style, color scheme, elements, layout", "title": "Título overlay opcional", "bullets": ["Punto 1 opcional", "Punto 2 opcional"]}
```

# INGENIERÍA DE PROMPTS PARA VISUALES

Para `ai_video` (Veo 3.1), escribe prompts CINEMATOGRÁFICOS en inglés:
- BUENO: "Glowing data streams flowing through a neural network, particles connecting into constellation patterns, cinematic slow motion, dark background with blue and purple bioluminescent light trails, abstract and metaphorical, no faces or text, 4K quality, smooth camera dollying forward"
- MALO: "abstract animation" o "tech background"

Para `ai_illustration` (Imagen 3), escribe prompts TÉCNICOS en inglés:
- BUENO: "A clean technical diagram showing client-server architecture with labeled arrows between a browser, API gateway, and database. Educational infographic style, dark navy background (#0f172a), blue (#3b82f6) and purple (#8b5cf6) accent colors, 16:9 wide format, no text labels, professional quality, flat design with subtle gradients"
- MALO: "cloud diagram" o "educational illustration"

# RESTRICCIONES DE GUION

- Narración total: ~300 palabras (150 palabras/min × ~2 minutos)
- Número de escenas: entre 8 y 12 por video (ritmo dinámico)
- Idioma: Español (toda la narración en español para TTS)
- ai_video: exactamente 1 escena (la escena de apertura / hook)
- hero_title: máximo 1 escena (apertura o cierre)
- screenshot_scene: solo si hay una URL verificada en las fuentes del learning path
- NO inventes URLs — usa únicamente URLs de las fuentes verificadas en el contexto del learning path

# FORMATO DE SALIDA

Devuelve ÚNICAMENTE JSON válido. Sin markdown, sin explicación. Esquema exacto:

```json
{
  "title": "Título del video en español",
  "total_word_budget": 300,
  "scenes": [
    {
      "scene_number": 1,
      "narration": "Texto de narración en español para esta escena.",
      "visual_type": "ai_video | ai_illustration | text_card | hero_title | stat_card | callout | comparison | bar_chart | line_chart | pie_chart | kpi_grid | progress_bar | terminal_scene | screenshot_scene",
      "visual_config": { ... configuración específica del tipo visual según el catálogo anterior ... }
    }
  ]
}
```

Recuerda: Tú NO estás escribiendo un guion genérico — estás orquestando 14 tipos de escenas Remotion para crear una experiencia de aprendizaje visualmente rica y pedagógicamente sólida. Cada elección de visual_type debe tener una razón pedagógica. Piensa como un director de cine educativo."""


class VideoService(VideoServiceInterface):
    def __init__(
        self,
        mock_service: Optional[MockVideoService] = None,
        llm_adapter: Optional[OpenRouterLLMAdapter] = None,
        tts_adapter: Optional[GoogleCloudTTSAdapter] = None,
        playwright_adapter: Optional[PlaywrightCaptureAdapter] = None,
        veo_adapter: Optional[GoogleVeoAdapter] = None,
        imagen_adapter: Optional[GoogleImagenAdapter] = None,
        storage_adapter: Optional[SupabaseStorageAdapter] = None
    ):
        self.mock_service = mock_service or MockVideoService()
        self.llm_adapter = llm_adapter or OpenRouterLLMAdapter()
        self.tts_adapter = tts_adapter or GoogleCloudTTSAdapter()
        self.playwright_adapter = playwright_adapter or PlaywrightCaptureAdapter()
        self.veo_adapter = veo_adapter or GoogleVeoAdapter()
        self.imagen_adapter = imagen_adapter or GoogleImagenAdapter()
        self.storage_adapter = storage_adapter or SupabaseStorageAdapter()

        self._supabase = None
        self._fallback_assets: Dict[UUID, dict] = {}
        self._fallback_jobs: Dict[UUID, dict] = {}

        url = settings.supabase_url
        key = settings.supabase_key
        if url and "placeholder" not in url and key and "placeholder" not in key:
            try:
                self._supabase = create_client(url, key)
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client in VideoService: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════

    async def generate_video(
        self,
        component_id: Optional[UUID] = None,
        custom_storyboard: Optional[StoryboardRequest] = None,
        use_mock: bool = False
    ) -> UUID:
        """Starts video generation job.

        There are three ways to trigger this:
        1. custom_storyboard: Render directly from a client-provided storyboard.
        2. component_id: Look up storyboard from DB, or auto-generate one.
        3. Neither: Render a default demo video.

        Returns a job_id that clients can poll via get_video_job_status().
        """
        if use_mock:
            return await self.mock_service.generate_video(component_id, custom_storyboard, use_mock)

        job_id = uuid4()
        now_str = datetime.now(timezone.utc).isoformat()
        job_data = {
            "id": str(job_id),
            "type": "video_generation",
            "status": JobStatus.QUEUED.value,
            "progress": 0,
            "created_at": now_str,
            "updated_at": now_str,
            "result": None,
            "error": None
        }

        # Save job to database (or in-memory fallback).
        if self._supabase:
            try:
                self._supabase.table("jobs").insert(job_data).execute()
            except Exception as e:
                print(f"Supabase create job error in VideoService, falling back to memory: {e}")
                self._fallback_jobs[job_id] = job_data
        else:
            self._fallback_jobs[job_id] = job_data

        # Determine the storyboard source.
        storyboard = None
        if custom_storyboard:
            storyboard = custom_storyboard.model_dump()
        elif component_id:
            storyboard = await self._get_or_create_storyboard(component_id)
        else:
            # Default demo storyboard showcasing all visual types.
            storyboard = self._get_default_storyboard()

        # Spawn the rendering pipeline as a background task.
        asyncio.create_task(self._run_render_job(job_id, component_id, storyboard))
        return job_id

    async def generate_storyboard(
        self,
        route_id: UUID,
        module_id: UUID,
        component_kind: str = "video",
        component_id: Optional[UUID] = None,
        k: int = 8,
        kb: Optional[KnowledgeBaseInterface] = None,
    ) -> dict:
        """KB-grounded storyboard for the Render Target (ADR-0015).

        Pure: KB query → scriptwriter LLM → JSON. No Asset / no Job persistence.

        Module grounding: builds the KB query from ``module.titulo`` and
        ``module.descripcion`` (+ ``component.titulo`` if any) and calls the
        existing route-scoped ``KnowledgeBase.query``. Verified URLs come from the
        KB hits' own citations, so URL provenance matches the grounding.
        """
        # ── Pull Spine context: component → module → route ──
        context = await self._load_render_target_context(
            route_id, module_id, component_id
        )
        module_title = context["module_title"] or "modulo"
        module_desc = context["module_description"] or ""

        # ── Module-grounded KB query ──
        query_text = " ".join(p for p in [module_title, module_desc] if p).strip()
        if context["component_title"]:
            query_text = f"{context['component_title']}. {query_text}".strip()

        grounded_chunks = []
        if kb is not None and query_text:
            try:
                grounded_chunks = await kb.query(route_id, query_text, k=k)
            except Exception as e:
                print(f"[storyboard] KB query failed, degrading ungrounded: {e}")
                grounded_chunks = []

        # ── Build LLM prompt parts ──
        context_parts: list[str] = []

        if context["component_title"]:
            context_parts.append(f"COMPONENT: {context['component_title']}")
        if module_title:
            context_parts.append(f"MODULE: {module_title}")
        if context["module_type"]:
            context_parts.append(f"MODULE TYPE: {context['module_type']}")
        if module_desc:
            context_parts.append(f"MODULE DESCRIPTION: {module_desc}")
        if context["route_title"]:
            context_parts.append(f"ROUTE: {context['route_title']}")
        if context["route_tema"]:
            context_parts.append(f"ROUTE TOPIC: {context['route_tema']}")
        if context["route_storytelling"]:
            context_parts.append(f"ROUTE OBJECTIVE / BRIEF: {context['route_storytelling']}")

        # Grounded excerpts with citations (the new "information from the KB").
        if grounded_chunks:
            excerpts = "\n\n".join(
                f"[Fuente: {c.citation.title or 'sin título'}"
                f"{' · ' + c.citation.url if c.citation.url else ''}"
                f"]\n{c.content}"
                for c in grounded_chunks
            )
            context_parts.append(
                f"GROUNDING (kb excerpts — base narration on these, cite sources):\n{excerpts}"
            )
            # Verified URL list reused from the KB hits (no second source query).
            urls = []
            seen = set()
            for c in grounded_chunks:
                u = c.citation.url
                if u and u not in seen:
                    seen.add(u)
                    urls.append(
                        f"  - {c.citation.title or 'Untitled'}: {u}"
                        f"{' (VERIFIED)' if c.citation.verificada_google else ''}"
                    )
            if urls:
                context_parts.append(
                    f"VERIFIED SOURCE URLS (use ONLY these for screenshot_scene):\n"
                    f"{chr(10).join(urls)}"
                )
        else:
            context_parts.append(
                "GROUNDING: No KB excerpts available for this module. "
                "Write a coherent script from the context above only."
            )
            context_parts.append(
                "VERIFIED SOURCE URLS: None available. Do NOT use screenshot_scene."
            )

        module_type_map = {
            "intro": "This module INTRODUCES the learning path. Focus on motivation, overview, and why this matters.",
            "capsula": "This is a CORE TEACHING module. Focus on explaining concepts clearly with examples and data.",
            "lab": "This is a HANDS-ON module. Focus on practical steps, commands, and demonstrations.",
            "evaluacion": "This is an ASSESSMENT module. Focus on reinforcing what was learned.",
            "cierre": "This is a CLOSING module. Focus on synthesis, takeaways, and next steps.",
        }
        if context["module_type"] in module_type_map:
            context_parts.append(
                f"PEDAGOGICAL ROLE: {module_type_map[context['module_type']]}"
            )

        learning_context = "\n\n".join(context_parts) if context_parts else (
            f"Generate a storyboard for module {module_id}."
        )

        user_prompt = (
            "Generate a 2-minute educational video storyboard using the full 14-visual-type catalog.\n\n"
            "=== LEARNING PATH CONTEXT ===\n"
            f"{learning_context}\n\n"
            "=== INSTRUCTIONS ===\n"
            "1. Follow the pedagogical structure: Hook → Context → Core → (Demo) → Summary\n"
            "2. Use the module type and pedagogical role to guide tone and depth\n"
            "3. Ground narration in the GROUNDING excerpts when provided; do not contradict them\n"
            "4. If verified source URLs are provided, include a screenshot_scene for the most relevant one\n"
            "5. All narration must be in Spanish\n"
            "6. Every visual_type choice must have a clear pedagogical reason\n"
            "7. Return ONLY valid JSON — no markdown, no explanation\n"
        )

        generated_json = await self.llm_adapter.chat_completion(
            role="scriptwriter",
            prompt=f"{SCRIPTWRITER_SYSTEM_PROMPT}\n\n---\n\nUSER REQUEST:\n{user_prompt}",
        )

        try:
            storyboard = json.loads(generated_json)
        except Exception:
            storyboard = self._get_default_storyboard()

        return {
            "storyboard": storyboard,
            "grounding": {
                "query": query_text,
                "k": k,
                "chunks": [c.model_dump(mode="json") for c in grounded_chunks],
            },
        }

    async def _load_render_target_context(
        self,
        route_id: UUID,
        module_id: UUID,
        component_id: Optional[UUID],
    ) -> dict:
        """Reads component/module/route fields from Supabase for the given
        Render Target. Tolerates missing tables or placeholder Supabase; returns
        blanks so callers can degrade gracefully."""
        ctx = {
            "component_title": None,
            "module_title": None,
            "module_type": None,
            "module_description": None,
            "route_title": None,
            "route_tema": None,
            "route_storytelling": None,
        }
        if not self._supabase:
            return ctx

        try:
            if component_id:
                comp = self._supabase.table("components").select("*").eq("id", str(component_id)).execute()
                if comp.data:
                    row = comp.data[0]
                    ctx["component_title"] = row.get("titulo") or row.get("tema")
        except Exception as e:
            print(f"[storyboard] component query error: {e}")

        try:
            mod = self._supabase.table("modules").select("*").eq("id", str(module_id)).execute()
            if mod.data:
                row = mod.data[0]
                ctx["module_title"] = row.get("titulo")
                ctx["module_type"] = row.get("tipo", "capsula")
                ctx["module_description"] = row.get("descripcion", "")
                actual_route_id = row.get("learning_path_id", route_id)
        except Exception as e:
            print(f"[storyboard] module query error: {e}")
            actual_route_id = route_id

        try:
            lp = self._supabase.table("learning_paths").select("*").eq("id", str(actual_route_id)).execute()
            if lp.data:
                row = lp.data[0]
                ctx["route_title"] = row.get("titulo", "")
                ctx["route_tema"] = row.get("tema", "")
                ctx["route_storytelling"] = row.get("storytelling", "") or row.get("brief", "")
        except Exception as e:
            print(f"[storyboard] learning_path query error: {e}")

        return ctx

    async def get_video_job_status(self, job_id: UUID) -> Optional[VideoJobResponse]:
        # Check mock registry first.
        mock_status = await self.mock_service.get_video_job_status(job_id)
        if mock_status:
            return mock_status

        # Query database or fallback.
        job = None
        if self._supabase:
            try:
                res = self._supabase.table("jobs").select("*").eq("id", str(job_id)).execute()
                if res.data:
                    job = res.data[0]
            except Exception as e:
                print(f"Supabase get job error in VideoService, falling back to memory: {e}")
                job = self._fallback_jobs.get(job_id)
        else:
            job = self._fallback_jobs.get(job_id)

        if not job:
            return None

        result_data = None
        if job.get("result"):
            result_data = VideoJobResult(
                video_url=job["result"].get("video_url", ""),
                duration_seconds=job["result"].get("duration_seconds", 0.0),
                cost_usd=job["result"].get("cost_usd", 0.0)
            )

        return VideoJobResponse(
            job_id=UUID(job["id"]),
            status=JobStatus(job["status"]),
            progress=job["progress"],
            result=result_data,
            error=job.get("error")
        )

    async def segment_video(self, video_url: str) -> List[dict]:
        """Segments long video into timestamped chunks.

        Delegates to mock service to avoid heavy processing in local/sandboxed runs.
        """
        return await self.mock_service.segment_video(video_url)

    # ═══════════════════════════════════════════════════════════════════
    # STORYBOARD GENERATION
    # ═══════════════════════════════════════════════════════════════════

    async def _get_or_create_storyboard(self, component_id: UUID) -> dict:
        """Queries asset table for storyboard; generates one if missing.

        On first generation, queries the full learning path context (route,
        module, lesson sections, verified sources) and passes it to the LLM
        as structured context so the storyboard is specific to the topic.
        """
        asset = None
        if self._supabase:
            try:
                res = self._supabase.table("assets").select("*").eq("componente_id", str(component_id)).eq("tipo", "video").execute()
                if res.data:
                    asset = res.data[0]
            except Exception as e:
                print(f"Supabase query asset error in VideoService: {e}")
                asset = self._fallback_assets.get(component_id)
        else:
            asset = self._fallback_assets.get(component_id)

        if asset and asset.get("provenance") and asset["provenance"].get("storyboard"):
            return asset["provenance"]["storyboard"]

        print(f"No storyboard found for component {component_id}. Auto-generating via scriptwriter LLM...")

        # ── Build learning path context for the LLM ──
        context_parts = []

        # 1. Query the component to find its title and module
        component_title = None
        module_id = None
        if self._supabase:
            try:
                comp_res = self._supabase.table("components").select("*").eq("id", str(component_id)).execute()
                if comp_res.data:
                    comp = comp_res.data[0]
                    component_title = comp.get("titulo") or comp.get("tema")
                    module_id = comp.get("modulo_id")
            except Exception as e:
                print(f"Supabase query component error: {e}")

        if component_title:
            context_parts.append(f"COMPONENT: {component_title}")

        # 2. Query the module to get its type, title, description, and learning_path_id
        module_title = None
        module_type = None
        learning_path_id = None
        if self._supabase and module_id:
            try:
                mod_res = self._supabase.table("modules").select("*").eq("id", str(module_id)).execute()
                if mod_res.data:
                    mod = mod_res.data[0]
                    module_title = mod.get("titulo")
                    module_type = mod.get("tipo", "capsula")
                    module_desc = mod.get("descripcion", "")
                    learning_path_id = mod.get("learning_path_id")

                    context_parts.append(f"MODULE: {module_title}")
                    context_parts.append(f"MODULE TYPE: {module_type}")
                    if module_desc:
                        context_parts.append(f"MODULE DESCRIPTION: {module_desc}")
            except Exception as e:
                print(f"Supabase query module error: {e}")

        # 3. Query the learning path (route) for its title, theme, storytelling brief
        if self._supabase and learning_path_id:
            try:
                lp_res = self._supabase.table("learning_paths").select("*").eq("id", str(learning_path_id)).execute()
                if lp_res.data:
                    lp = lp_res.data[0]
                    route_title = lp.get("titulo", "")
                    route_tema = lp.get("tema", "")
                    route_storytelling = lp.get("storytelling", "") or lp.get("brief", "")

                    context_parts.append(f"ROUTE: {route_title}")
                    context_parts.append(f"ROUTE TOPIC: {route_tema}")
                    if route_storytelling:
                        context_parts.append(f"ROUTE OBJECTIVE / BRIEF: {route_storytelling}")
            except Exception as e:
                print(f"Supabase query learning_path error: {e}")

        # 4. Query verified sources for the component's asset
        verified_urls = []
        if self._supabase:
            try:
                if asset and asset.get("id"):
                    asset_id = asset["id"]
                else:
                    # Even without an existing asset, try to find sources linked
                    # to any asset for this component
                    asset_id = None

                if asset_id:
                    src_res = self._supabase.table("sources").select("*").eq("asset_id", str(asset_id)).execute()
                    if src_res.data:
                        for src in src_res.data:
                            url = src.get("url", "")
                            title = src.get("title", "")
                            verified = src.get("verificada_google", False)
                            if url:
                                verified_urls.append({
                                    "url": url,
                                    "title": title,
                                    "verified": verified
                                })
            except Exception as e:
                print(f"Supabase query sources error: {e}")

        if verified_urls:
            urls_text = "\n".join(
                f"  - {s['title']}: {s['url']} {'(VERIFIED)' if s['verified'] else ''}"
                for s in verified_urls
            )
            context_parts.append(f"VERIFIED SOURCE URLS (use ONLY these for screenshot_scene):\n{urls_text}")
        else:
            context_parts.append("VERIFIED SOURCE URLS: None available. Do NOT use screenshot_scene.")

        # 5. Module pedagogical role hint
        module_type_map = {
            "intro": "This module INTRODUCES the learning path. Focus on motivation, overview, and why this matters.",
            "capsula": "This is a CORE TEACHING module. Focus on explaining concepts clearly with examples and data.",
            "lab": "This is a HANDS-ON module. Focus on practical steps, commands, and demonstrations.",
            "evaluacion": "This is an ASSESSMENT module. Focus on reinforcing what was learned.",
            "cierre": "This is a CLOSING module. Focus on synthesis, takeaways, and next steps."
        }
        if module_type and module_type in module_type_map:
            context_parts.append(f"PEDAGOGICAL ROLE: {module_type_map[module_type]}")

        # ── Build the user prompt ──
        learning_context = "\n\n".join(context_parts) if context_parts else (
            f"Generate a storyboard for a video component with ID {component_id}."
        )

        user_prompt = (
            f"Generate a 2-minute educational video storyboard using the full 14-visual-type catalog.\n\n"
            f"=== LEARNING PATH CONTEXT ===\n"
            f"{learning_context}\n\n"
            f"=== INSTRUCTIONS ===\n"
            f"1. Follow the pedagogical structure: Hook → Context → Core → (Demo) → Summary\n"
            f"2. Use the module type and pedagogical role to guide tone and depth\n"
            f"3. Use route topic and component title to make content specific and relevant\n"
            f"4. If verified source URLs are provided, include a screenshot_scene for the most relevant one\n"
            f"5. All narration must be in Spanish\n"
            f"6. Every visual_type choice must have a clear pedagogical reason\n"
            f"7. Return ONLY valid JSON — no markdown, no explanation"
        )

        generated_json = await self.llm_adapter.chat_completion(
            role="scriptwriter",
            prompt=f"{SCRIPTWRITER_SYSTEM_PROMPT}\n\n---\n\nUSER REQUEST:\n{user_prompt}",
        )

        try:
            storyboard = json.loads(generated_json)
        except Exception:
            storyboard = self._get_default_storyboard()

        # Save asset back to Supabase.
        asset_id = UUID(asset["id"]) if asset else uuid4()
        now_str = datetime.now(timezone.utc).isoformat()
        asset_data = {
            "id": str(asset_id),
            "componente_id": str(component_id),
            "tipo": "video",
            "estado": "generado",
            "word_budget": 300,
            "provenance": {"storyboard": storyboard},
            "created_at": now_str,
            "updated_at": now_str
        }

        if self._supabase:
            try:
                if asset:
                    self._supabase.table("assets").update(asset_data).eq("id", str(asset_id)).execute()
                else:
                    self._supabase.table("assets").insert(asset_data).execute()
            except Exception as e:
                print(f"Supabase save asset error in VideoService: {e}")
                self._fallback_assets[component_id] = asset_data
        else:
            self._fallback_assets[component_id] = asset_data

        return storyboard

    def _get_default_storyboard(self) -> dict:
        """Default demo storyboard that showcases all visual types.

        Used as a fallback when no component_id is provided or when the
        LLM scriptwriter fails to produce valid JSON.
        """
        return {
            "title": "Introducción a Xertica Education",
            "total_word_budget": 300,
            "scenes": [
                {
                    "scene_number": 1,
                    "narration": (
                        "¿Alguna vez te has preguntado cómo las empresas líderes capacitan a sus equipos "
                        "de manera eficiente? En esta cápsula, descubrirás cómo Xertica Education "
                        "transforma la creación de contenido educativo."
                    ),
                    "visual_type": "ai_video",
                    "visual_config": {
                        "prompt": (
                            "Streams of luminous data particles flowing through an abstract digital "
                            "landscape, forming interconnected nodes of knowledge. Cinematic slow motion, "
                            "dark navy background with electric blue and soft purple bioluminescent trails. "
                            "Abstract and metaphorical, no faces or text. Professional 4K quality, "
                            "smooth camera movement."
                        )
                    }
                },
                {
                    "scene_number": 2,
                    "narration": (
                        "Xertica Education es una plataforma de orquestación de aprendizaje que utiliza "
                        "inteligencia artificial para generar contenido educativo personalizado. "
                        "Cada ruta de aprendizaje se estructura en módulos con lecciones, videos, "
                        "infografías y evaluaciones."
                    ),
                    "visual_type": "ai_illustration",
                    "visual_config": {
                        "prompt": (
                            "A clean, modern technical diagram showing the architecture of an educational "
                            "platform. Central hub labeled 'Learning Path' connected to satellite nodes: "
                            "'Lessons', 'Videos', 'Infographics', 'Quizzes'. Each node has a distinct icon. "
                            "Style: flat design infographic, dark navy background (#0f172a), blue (#3b82f6) "
                            "and purple (#8b5cf6) color scheme, clean lines, professional educational poster, "
                            "16:9 wide format, no text labels, icons only."
                        ),
                        "title": "Arquitectura de la Plataforma",
                        "bullets": [
                            "Rutas de aprendizaje personalizadas",
                            "Módulos con múltiples tipos de contenido",
                            "IA generativa con verificación humana"
                        ]
                    }
                },
                {
                    "scene_number": 3,
                    "narration": (
                        "El proceso comienza cuando un autor define un tema. La plataforma genera "
                        "automáticamente una estructura de ruta, investiga fuentes verificables, "
                        "y crea un borrador completo que el equipo puede revisar y aprobar."
                    ),
                    "visual_type": "animated_slide",
                    "visual_config": {
                        "title": "Flujo de Creación de Contenido",
                        "bullets": [
                            "Definir tema → Estructura automática de ruta",
                            "Investigación con fuentes verificables Google",
                            "Generación de borradores con IA",
                            "Revisión y aprobación humana (HITL)",
                            "Publicación en Google Classroom"
                        ]
                    }
                },
                {
                    "scene_number": 4,
                    "narration": (
                        "Cada componente pasa por puertas de control donde el equipo humano "
                        "verifica la calidad, la precisión técnica y la relevancia del contenido. "
                        "Esto garantiza que ningún material educativo se publique sin supervisión."
                    ),
                    "visual_type": "animated_slide",
                    "visual_config": {
                        "title": "Control de Calidad",
                        "bullets": [
                            "Gate 0: Aprobación de estructura",
                            "Gate 1: Verificación de fuentes",
                            "Gate 2: Revisión de guiones y storyboards",
                            "Gate 3: Aprobación final de assets"
                        ]
                    }
                },
                {
                    "scene_number": 5,
                    "narration": (
                        "En resumen, Xertica Education combina la velocidad de la inteligencia "
                        "artificial con la precisión del juicio humano para crear contenido "
                        "educativo de alta calidad, verificable y listo para el aula."
                    ),
                    "visual_type": "animated_slide",
                    "visual_config": {
                        "title": "Puntos Clave",
                        "bullets": [
                            "IA + Supervisión humana = Calidad garantizada",
                            "Contenido verificable con fuentes rastreables",
                            "De idea a aula en horas, no semanas"
                        ]
                    }
                }
            ]
        }

    # ═══════════════════════════════════════════════════════════════════
    # RENDER PIPELINE (the assembly line)
    # ═══════════════════════════════════════════════════════════════════

    async def _run_render_job(self, job_id: UUID, component_id: Optional[UUID], storyboard: dict):
        """Background rendering orchestrated by RenderPlan."""
        temp_dir = f"/tmp/render_{job_id}"
        os.makedirs(temp_dir, exist_ok=True)
        try:
            scenes = storyboard.get("scenes", [])
            stages = [
                RenderStage(stage_type="tts"),
                RenderStage(stage_type="visual"),
                RenderStage(stage_type="music"),
                RenderStage(stage_type="transform"),
                RenderStage(stage_type="remotion_render"),
                RenderStage(stage_type="validate"),
                RenderStage(stage_type="upload"),
            ]
            plan = RenderPlan(job_id=job_id, storyboard=storyboard, stages=stages)

            executor = RenderExecutor(self)
            await executor.execute(plan)

            total_duration = executor.total_duration
            veo_scenes = sum(1 for s in scenes if s.get("visual_type") == "ai_video")
            imagen_scenes = sum(1 for s in scenes if s.get("visual_type") == "ai_illustration")
            estimated_cost = (veo_scenes * 0.20) + (imagen_scenes * 0.04) + (0.004 * total_duration)

            final_url = executor.stage_outputs.get("upload", {}).get("url", "")
            result = {
                "video_url": final_url,
                "duration_seconds": round(total_duration, 2),
                "cost_usd": round(estimated_cost, 2),
            }
            await self._update_job(job_id, JobStatus.COMPLETED, 100, result=result)

            if component_id:
                await self._update_asset_completed(component_id, final_url)

        except Exception as e:
            print(f"[Job {job_id}] Critical error during video rendering: {e}")
            import traceback
            traceback.print_exc()
            await self._update_job(job_id, JobStatus.FAILED, 100, error=str(e))

        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    # ═══════════════════════════════════════════════════════════════════
    # DATABASE HELPERS
    # ═══════════════════════════════════════════════════════════════════

    async def _update_job(self, job_id: UUID, status: JobStatus, progress: int, result: Optional[dict] = None, error: Optional[str] = None):
        now_str = datetime.now(timezone.utc).isoformat()
        payload = {
            "status": status.value,
            "progress": progress,
            "updated_at": now_str
        }
        if result is not None:
            payload["result"] = result
        if error is not None:
            payload["error"] = error

        if self._supabase:
            try:
                self._supabase.table("jobs").update(payload).eq("id", str(job_id)).execute()
            except Exception as e:
                print(f"Supabase update job error: {e}")
                if job_id in self._fallback_jobs:
                    self._fallback_jobs[job_id].update(payload)
        else:
            if job_id in self._fallback_jobs:
                self._fallback_jobs[job_id].update(payload)

    async def _update_asset_completed(self, component_id: UUID, video_url: str):
        now_str = datetime.now(timezone.utc).isoformat()
        payload = {
            "estado": "generado",
            "storage_path": video_url,
            "updated_at": now_str
        }
        if self._supabase:
            try:
                self._supabase.table("assets").update(payload).eq("componente_id", str(component_id)).eq("tipo", "video").execute()
            except Exception as e:
                print(f"Supabase update asset url error: {e}")
                if component_id in self._fallback_assets:
                    self._fallback_assets[component_id].update(payload)
        else:
            if component_id in self._fallback_assets:
                self._fallback_assets[component_id].update(payload)

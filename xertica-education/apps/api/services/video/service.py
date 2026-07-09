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

SCRIPTWRITER_SYSTEM_PROMPT = """Eres un guionista experto en Videos de Explicacion Conceptual para Xertica Education.

Tu trabajo: producir un storyboard JSON que ensene el Objetivo Pedagogico del Modulo con una secuencia clara de aprendizaje. El video no debe ser una intro decorativa ni un resumen aleatorio de chunks recuperados.

# OBJETIVO PEDAGOGICO DEL MODULO

El titulo y la descripcion del modulo son la columna vertebral del video. Primero define que debe entender el estudiante; despues usa la KB como soporte. La KB Grounding aporta evidencia, ejemplos y vocabulario, pero no reemplaza el objetivo del modulo.

# ESTRUCTURA PEDAGOGICA

Genera 5 a 7 escenas fuertes para ~90-120 segundos:

1. Pregunta, contraste o problema real.
2. Modelo mental o distincion clave.
3. Proceso, regla de decision o ejemplo trabajado.
4. Checkpoint, malentendido o riesgo comun.
5. Takeaway aplicable.

Cada escena debe incluir:
- teaching_point: que aprende el estudiante.
- pedagogical_intent: por que esta escena existe.
- teaching_pattern: patron didactico, por ejemplo framing_question, misconception_correction, process_explanation, worked_example, decision_rule, checkpoint, synthesis.
- visual_rationale: por que el Tipo Visual elegido ensena mejor esta idea.
- grounding_status: kb_grounded si usa chunks de KB, module_grounded si solo usa contexto del modulo.

# PALETA VISUAL MVP

Prioriza `comparison`, `progress_bar`, `callout`, `text_card`, `terminal_scene` y `screenshot_scene`.

`ai_video` es opcional, maximo una vez, y solo si una metafora visual concreta ayuda a entender el concepto. Nunca lo uses como intro generica.
`ai_illustration` solo para un modelo mental o arquitectura concreta.
Graficos cuantitativos requieren valores evidenciados o marcados explicitamente como ilustrativos.
`screenshot_scene` requiere URL especifica, proposito, pasos ordenados de UI y resultado de aprendizaje. Si no hay URL verificada, no uses `screenshot_scene`.

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

- Narración total: ~225-300 palabras
- Número de escenas: 5 a 7 escenas fuertes
- Idioma: Español (toda la narración en español para TTS)
- ai_video: maximo 1 escena y solo con metafora didactica concreta
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
      "visual_config": { ... configuración específica del tipo visual según el catálogo anterior ... },
      "teaching_point": "Que aprende el estudiante.",
      "pedagogical_intent": "Funcion pedagogica de esta escena.",
      "teaching_pattern": "Patron didactico.",
      "visual_rationale": "Por que este visual ayuda a aprender.",
      "grounding_status": "kb_grounded | module_grounded"
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
        storyboard_source = "default_storyboard"
        if custom_storyboard:
            storyboard = custom_storyboard.model_dump()
            storyboard_source = "reviewed_storyboard"
        elif component_id:
            storyboard = await self._get_or_create_storyboard(component_id)
            storyboard_source = "component_storyboard"
        else:
            # Default demo storyboard showcasing all visual types.
            storyboard = self._get_default_storyboard()

        # Spawn the rendering pipeline as a background task.
        asyncio.create_task(
            self._run_render_job(job_id, component_id, storyboard, storyboard_source)
        )
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

        grounding_status = "kb_grounded" if grounded_chunks else "module_grounded"
        user_prompt = (
            "Generate a Video de Explicacion Conceptual using the full 14-visual-type catalog.\n\n"
            "=== LEARNING PATH CONTEXT ===\n"
            f"{learning_context}\n\n"
            "=== INSTRUCTIONS ===\n"
            "1. Treat OBJETIVO PEDAGOGICO DEL MODULO as the spine: module title + module description define what must be taught\n"
            "2. KB Grounding aporta evidencia, ejemplos y vocabulario; do not turn the video into a random summary of retrieved chunks\n"
            "3. Produce 5 a 7 escenas with explicit teaching_pattern, teaching_point, pedagogical_intent, visual_rationale, and grounding_status\n"
            "4. Think first in Patrones Didacticos, then choose the Remotion visual_type that teaches that idea\n"
            "5. If verified source URLs are provided, include screenshot_scene only when it becomes a real Walkthrough Didactico\n"
            f"6. Set scene grounding_status to {grounding_status}\n"
            "7. Prefer comparison, progress_bar, callout, text_card, terminal_scene, and useful screenshot_scene over decorative assets\n"
            "8. ai_video is optional, max one, and only for a meaningful teaching metaphor; never use it as a generic blue-network intro\n"
            "9. All narration must be in Spanish\n"
            "10. Every visual_type choice must have a clear pedagogical reason\n"
            "11. Return ONLY valid JSON — no markdown, no explanation\n"
        )

        generated_json = await self.llm_adapter.chat_completion(
            role="scriptwriter",
            prompt=f"{SCRIPTWRITER_SYSTEM_PROMPT}\n\n---\n\nUSER REQUEST:\n{user_prompt}",
        )

        try:
            storyboard = json.loads(generated_json)
        except Exception:
            storyboard = self._get_default_storyboard()
        verified_urls = {
            c.citation.url
            for c in grounded_chunks
            if c.citation.url and c.citation.verificada_google
        }
        storyboard = self._normalize_storyboard_grounding(
            storyboard,
            grounding_status,
            verified_urls=verified_urls,
        )

        return {
            "storyboard": storyboard,
            "grounding": {
                "status": grounding_status,
                "query": query_text,
                "k": k,
                "chunks": [c.model_dump(mode="json") for c in grounded_chunks],
            },
        }

    def _normalize_storyboard_grounding(
        self,
        storyboard: dict,
        grounding_status: str,
        verified_urls: Optional[set[str]] = None,
    ) -> dict:
        """Keep scene-level provenance honest and repair decorative visuals."""
        verified_urls = verified_urls or set()
        ai_video_count = 0
        hero_title_count = 0

        for scene in storyboard.get("scenes", []):
            scene["grounding_status"] = grounding_status

            if scene.get("visual_type") == "screenshot_scene" and not self._is_valid_walkthrough_scene(
                scene,
                verified_urls,
            ):
                self._replace_with_text_card(
                    scene,
                    title=scene.get("teaching_point") or "Walkthrough no verificable",
                    subtitle="Sin URL verificada o sin pasos didacticos suficientes para un walkthrough.",
                    rationale=(
                        "Sin walkthrough verificable, una tarjeta explicativa evita fingir una demostracion de UI."
                    ),
                )

            if scene.get("visual_type") in {"stat_card", "bar_chart", "line_chart", "pie_chart", "kpi_grid"}:
                if not self._supports_quantitative_visual(scene, grounding_status):
                    self._replace_with_callout(
                        scene,
                        text=scene.get("teaching_point") or scene.get("narration") or "Explicacion cualitativa",
                        rationale=(
                            "Sin valores evidenciados o etiquetados como ilustrativos, un visual cualitativo evita inventar metricas."
                        ),
                    )

            if scene.get("visual_type") == "ai_illustration" and not self._is_concrete_illustration_scene(scene):
                self._replace_with_text_card(
                    scene,
                    title=scene.get("teaching_point") or "Modelo a explicar",
                    subtitle=scene.get("narration") or "La escena necesita un modelo mental mas concreto.",
                    rationale=(
                        "Sin un modelo mental o arquitectura concreta, una tarjeta explicativa ensena mejor que una ilustracion generica."
                    ),
                )

            if scene.get("visual_type") == "ai_video":
                if ai_video_count >= 1 or not self._has_meaningful_visual_metaphor(scene):
                    self._replace_with_callout(
                        scene,
                        text=scene.get("teaching_point") or scene.get("narration") or "Idea clave del modulo",
                        rationale=(
                            "ai_video solo se permite como metafora didactica concreta y como maximo una vez."
                        ),
                    )
                else:
                    ai_video_count += 1

            if scene.get("visual_type") == "hero_title":
                if hero_title_count >= 1:
                    self._replace_with_text_card(
                        scene,
                        title=scene.get("teaching_point") or "Idea clave",
                        subtitle=scene.get("narration") or "La escena se simplifico para evitar pantallas de titulo repetidas.",
                        rationale="Evitar title-screen spam deja mas espacio para escenas que realmente ensenan.",
                    )
                else:
                    hero_title_count += 1

        return storyboard

    def _is_valid_walkthrough_scene(self, scene: dict, verified_urls: set[str]) -> bool:
        config = scene.get("visual_config") or {}
        url = config.get("url")
        steps = config.get("steps")
        purpose = config.get("purpose")
        learning_outcome = config.get("learning_outcome")
        return bool(
            url
            and url in verified_urls
            and purpose
            and learning_outcome
            and isinstance(steps, list)
            and len(steps) >= 2
        )

    def _supports_quantitative_visual(self, scene: dict, grounding_status: str) -> bool:
        numbers = self._extract_numbers(scene.get("visual_config") or {})
        if not numbers:
            return False
        if grounding_status == "module_grounded" and not self._is_explicitly_illustrative(scene):
            return False
        return True

    def _has_meaningful_visual_metaphor(self, scene: dict) -> bool:
        text = self._scene_text(scene)
        if "metafor" in text:
            return True
        generic_markers = (
            "blue network",
            "glowing particles",
            "tech background",
            "intro generica",
            "se ve moderno",
        )
        return not any(marker in text for marker in generic_markers)

    def _is_concrete_illustration_scene(self, scene: dict) -> bool:
        text = self._scene_text(scene)
        return any(
            marker in text
            for marker in (
                "modelo mental",
                "arquitect",
                "diagrama",
                "pipeline",
                "flujo",
                "sistema",
                "component",
            )
        )

    def _is_explicitly_illustrative(self, scene: dict) -> bool:
        return "ilustrativ" in self._scene_text(scene)

    def _scene_text(self, scene: dict) -> str:
        parts = [
            str(scene.get("narration") or ""),
            str(scene.get("teaching_point") or ""),
            str(scene.get("pedagogical_intent") or ""),
            str(scene.get("teaching_pattern") or ""),
            str(scene.get("visual_rationale") or ""),
        ]
        parts.extend(self._flatten_strings(scene.get("visual_config") or {}))
        return " ".join(parts).lower()

    def _flatten_strings(self, value) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            items = []
            for nested in value.values():
                items.extend(self._flatten_strings(nested))
            return items
        if isinstance(value, list):
            items = []
            for nested in value:
                items.extend(self._flatten_strings(nested))
            return items
        return []

    def _extract_numbers(self, value) -> list[float]:
        if isinstance(value, bool):
            return []
        if isinstance(value, (int, float)):
            return [float(value)]
        if isinstance(value, dict):
            items = []
            for nested in value.values():
                items.extend(self._extract_numbers(nested))
            return items
        if isinstance(value, list):
            items = []
            for nested in value:
                items.extend(self._extract_numbers(nested))
            return items
        return []

    def _replace_with_text_card(self, scene: dict, title: str, subtitle: str, rationale: str) -> None:
        scene["visual_type"] = "text_card"
        scene["visual_config"] = {
            "title": title,
            "subtitle": subtitle,
        }
        scene["visual_rationale"] = rationale

    def _replace_with_callout(self, scene: dict, text: str, rationale: str) -> None:
        scene["visual_type"] = "callout"
        scene["visual_config"] = {
            "callout_style": "info",
            "text": text,
        }
        scene["visual_rationale"] = rationale

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
                elif job_id in self._fallback_jobs:
                    job = self._fallback_jobs.get(job_id)
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
                cost_usd=job["result"].get("cost_usd", 0.0),
                provenance=job["result"].get("provenance"),
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
        """Default demo storyboard using valid VisualType values (ADR-0009).

        Used as a fallback when no component_id is provided or when the
        LLM scriptwriter fails to produce valid JSON.  Every scene uses one of
        the 14 Remotion-native types (never the legacy ``animated_slide``) and
        includes teaching metadata per ADR-0017.
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
                    "visual_type": "callout",
                    "visual_config": {
                        "callout_style": "info",
                        "text": "¿Cómo capacitar equipos con calidad y velocidad?",
                    },
                    "teaching_point": "Plantear por qué la creación de contenido educativo necesita una solución nueva.",
                    "pedagogical_intent": "Abrir con una pregunta que conecte con la experiencia del espectador.",
                    "teaching_pattern": "framing_question",
                    "visual_rationale": "Un callout concentra la pregunta guía sin depender de una intro generativa.",
                    "grounding_status": "module_grounded",
                },
                {
                    "scene_number": 2,
                    "narration": (
                        "Xertica Education es una plataforma de orquestación de aprendizaje que utiliza "
                        "inteligencia artificial para generar contenido educativo personalizado. "
                        "Cada ruta de aprendizaje se estructura en módulos con lecciones, videos, "
                        "infografías y evaluaciones."
                    ),
                    "visual_type": "comparison",
                    "visual_config": {
                        "leftLabel": "Creación manual",
                        "leftValue": "Semanas de trabajo por ruta",
                        "rightLabel": "Con Xertica Education",
                        "rightValue": "Horas con supervisión humana",
                    },
                    "teaching_point": "Contrastar la creación manual de contenido con la orquestación asistida por IA.",
                    "pedagogical_intent": "Establecer el modelo mental de la plataforma como orquestación, no como reemplazo.",
                    "teaching_pattern": "misconception_correction",
                    "visual_rationale": "La comparación muestra el contraste central sin inventar métricas.",
                    "grounding_status": "module_grounded",
                },
                {
                    "scene_number": 3,
                    "narration": (
                        "El proceso comienza cuando un autor define un tema. La plataforma genera "
                        "automáticamente una estructura de ruta, investiga fuentes verificables, "
                        "y crea un borrador completo que el equipo puede revisar y aprobar."
                    ),
                    "visual_type": "progress_bar",
                    "visual_config": {
                        "title": "Flujo de Creación de Contenido",
                        "progress": 60,
                        "steps": [
                            "Definir tema",
                            "Estructura automática de ruta",
                            "Investigación con fuentes verificables",
                            "Generación de borradores con IA",
                            "Revisión y aprobación humana",
                        ],
                    },
                    "teaching_point": "Presentar la secuencia de producción para que el estudiante entienda el flujo completo.",
                    "pedagogical_intent": "Convertir el proceso en una secuencia ordenada y repetible.",
                    "teaching_pattern": "process_explanation",
                    "visual_rationale": "La barra de progreso comunica orden y avance sin inventar métricas.",
                    "grounding_status": "module_grounded",
                },
                {
                    "scene_number": 4,
                    "narration": (
                        "Cada componente pasa por puertas de control donde el equipo humano "
                        "verifica la calidad, la precisión técnica y la relevancia del contenido. "
                        "Esto garantiza que ningún material educativo se publique sin supervisión."
                    ),
                    "visual_type": "callout",
                    "visual_config": {
                        "callout_style": "warning",
                        "text": (
                            "Gate 0: Aprobación de estructura · "
                            "Gate 1: Verificación de fuentes · "
                            "Gate 3: Aprobación final de assets"
                        ),
                    },
                    "teaching_point": "Explicar que la supervisión humana ocurre en puntos específicos, no al final.",
                    "pedagogical_intent": "Corregir el supuesto de que la IA actúa sin supervisión.",
                    "teaching_pattern": "checkpoint",
                    "visual_rationale": "El callout tipo warning resalta una regla operativa importante.",
                    "grounding_status": "module_grounded",
                },
                {
                    "scene_number": 5,
                    "narration": (
                        "En resumen, Xertica Education combina la velocidad de la inteligencia "
                        "artificial con la precisión del juicio humano para crear contenido "
                        "educativo de alta calidad, verificable y listo para el aula."
                    ),
                    "visual_type": "text_card",
                    "visual_config": {
                        "title": "Puntos Clave",
                        "subtitle": (
                            "IA + Supervisión humana = Calidad garantizada • "
                            "Contenido verificable con fuentes rastreables • "
                            "De idea a aula en horas, no semanas"
                        ),
                    },
                    "teaching_point": "Cerrar con los tres beneficios principales para que el estudiante los recuerde.",
                    "pedagogical_intent": "Sintetizar el aprendizaje en una regla aplicable.",
                    "teaching_pattern": "synthesis",
                    "visual_rationale": "Una tarjeta de texto concentra el takeaway sin ruido visual.",
                    "grounding_status": "module_grounded",
                },
            ],
        }

    # ═══════════════════════════════════════════════════════════════════
    # RENDER PIPELINE (the assembly line)
    # ═══════════════════════════════════════════════════════════════════

    async def _run_render_job(
        self,
        job_id: UUID,
        component_id: Optional[UUID],
        storyboard: dict,
        storyboard_source: str,
    ):
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
            render_provenance = self._build_render_provenance(storyboard, storyboard_source)
            result = {
                "video_url": final_url,
                "duration_seconds": round(total_duration, 2),
                "cost_usd": round(estimated_cost, 2),
                "provenance": render_provenance,
            }
            await self._update_job(job_id, JobStatus.COMPLETED, 100, result=result)

            if component_id:
                await self._update_asset_completed(component_id, final_url, render_provenance)

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

    def _build_render_provenance(self, storyboard: dict, storyboard_source: str) -> dict:
        return {
            "storyboard_source": storyboard_source,
            "storyboard": storyboard,
            "render_profile": {
                "resolution": "1280x720",
                "codec": "h264",
                "container": "mp4",
            },
            "artifact_retention": {
                "successful_render": {
                    "retained_artifacts": ["final_mp4", "render_provenance"],
                    "discarded_intermediates": [
                        "scene_tts",
                        "playwright_screenshots",
                        "imagen_pngs",
                        "veo_clips",
                        "remotion_workdir",
                    ],
                },
                "failed_render": {
                    "mode": "explicit_short_lived_only",
                    "ttl_hours": 24,
                },
                "debug_mode": {
                    "mode": "explicit_short_lived_only",
                    "ttl_hours": 24,
                },
            },
        }

    async def _update_asset_completed(
        self,
        component_id: UUID,
        video_url: str,
        render_provenance: Optional[dict] = None,
    ):
        now_str = datetime.now(timezone.utc).isoformat()
        existing_asset = await self._get_video_asset(component_id)
        existing_provenance = (
            existing_asset.get("provenance")
            if existing_asset and isinstance(existing_asset.get("provenance"), dict)
            else {}
        )
        payload = {
            "estado": "generado",
            "storage_path": video_url,
            "updated_at": now_str,
        }
        if render_provenance:
            payload["provenance"] = {**existing_provenance, **render_provenance}
        if self._supabase:
            try:
                self._supabase.table("assets").update(payload).eq("componente_id", str(component_id)).eq("tipo", "video").execute()
            except Exception as e:
                print(f"Supabase update asset url error: {e}")
                current_asset = self._fallback_assets.get(component_id, existing_asset or {})
                current_asset.update(payload)
                self._fallback_assets[component_id] = current_asset
        else:
            current_asset = self._fallback_assets.get(component_id, existing_asset or {})
            current_asset.update(payload)
            self._fallback_assets[component_id] = current_asset

    async def _get_video_asset(self, component_id: UUID) -> dict:
        if self._supabase:
            try:
                res = (
                    self._supabase.table("assets")
                    .select("*")
                    .eq("componente_id", str(component_id))
                    .eq("tipo", "video")
                    .execute()
                )
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"Supabase get asset error in VideoService: {e}")
        return self._fallback_assets.get(component_id, {})

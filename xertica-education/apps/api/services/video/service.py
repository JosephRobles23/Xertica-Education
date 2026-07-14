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
import hashlib
import copy
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
# SCRIPTWRITER_SYSTEM_PROMPT is the single most important piece of the
# pipeline. It tells the LLM how to structure an educational video storyboard
# so that it's genuinely pedagogical, not just a wall of text with generic
# visuals. It lives in prompts/video.py.
from prompts.video import SCRIPTWRITER_SYSTEM_PROMPT


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
        self._render_tasks: Dict[UUID, asyncio.Task] = {}
        self._job_observability: Dict[UUID, dict] = {}

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
        route_id: Optional[str] = None,
        module_id: Optional[str] = None,
        component_kind: Optional[str] = None,
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
            return await self.mock_service.generate_video(
                component_id=component_id,
                route_id=route_id,
                module_id=module_id,
                component_kind=component_kind,
                custom_storyboard=custom_storyboard,
                use_mock=use_mock,
            )

        render_target = (
            {
                "route_id": str(route_id),
                "module_id": str(module_id),
                "component_kind": component_kind or "video",
            }
            if route_id and module_id
            else None
        )

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
        self._job_observability[job_id] = {"current_stage": "queue", "events": []}

        # Save job to database (or in-memory fallback).
        if self._supabase:
            try:
                self._supabase.table("jobs").insert(job_data).execute()
            except Exception as e:
                print(f"Supabase create job error in VideoService, falling back to memory: {e}")
                self._fallback_jobs[job_id] = job_data
        else:
            self._fallback_jobs[job_id] = job_data

        # Storyboard generation can call the LLM. Keep it inside the job so every
        # entry point acknowledges the render immediately.
        task = asyncio.create_task(
            self._prepare_and_run_render_job(
                job_id=job_id,
                component_id=component_id,
                render_target=render_target,
                custom_storyboard=custom_storyboard,
            )
        )
        if task is not None:
            self._render_tasks[job_id] = task
            task.add_done_callback(lambda _task: self._render_tasks.pop(job_id, None))
        await self._record_job_event(job_id, "queue", "queued", "Video generation job created")
        return job_id

    async def _prepare_and_run_render_job(
        self,
        job_id: UUID,
        component_id: Optional[UUID],
        render_target: Optional[dict],
        custom_storyboard: Optional[StoryboardRequest],
    ) -> None:
        """Prepare a render without delaying the ``POST /videos/generate`` response."""
        try:
            await self._update_job(job_id, JobStatus.RUNNING, 1)

            if render_target and component_id is None:
                component_id = await self._resolve_video_component_id(
                    route_id=render_target["route_id"],
                    module_id=render_target["module_id"],
                    component_kind=render_target["component_kind"],
                    create_if_missing=True,
                )

            if custom_storyboard:
                storyboard = custom_storyboard.model_dump()
                storyboard_source = "reviewed_storyboard"
            elif component_id:
                storyboard = await self._get_or_create_storyboard(component_id)
                storyboard_source = "component_storyboard"
            else:
                storyboard = self._get_default_storyboard()
                storyboard_source = "default_storyboard"

            if component_id:
                await self._ensure_video_asset_started(
                    component_id=component_id,
                    storyboard=storyboard,
                    storyboard_source=storyboard_source,
                )

            await self._run_render_job(
                job_id,
                component_id,
                storyboard,
                storyboard_source,
                render_target,
            )
        except asyncio.CancelledError:
            await self._record_job_event(job_id, "cancel", "cancelled", "Video generation cancelled")
            await self._update_job(job_id, JobStatus.CANCELLED, 100, error="Cancelled by user")
            raise
        except Exception as error:
            print(f"[Job {job_id}] Failed while preparing video render: {error}")
            await self._record_job_event(job_id, "prepare", "failed", str(error))
            await self._update_job(job_id, JobStatus.FAILED, 100, error=str(error))

    async def cancel_video_job(self, job_id: UUID) -> bool:
        job = await self.get_video_job_record(job_id)
        if not job:
            return False
        if job.get("status") in {JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
            return False

        task = self._render_tasks.get(job_id)
        if task:
            task.cancel()
        await self._record_job_event(job_id, "cancel", "requested", "Cancellation requested by user")
        await self._update_job(job_id, JobStatus.CANCELLED, 100, error="Cancelled by user")
        return True

    async def generate_storyboard(
        self,
        route_id: str,
        module_id: str,
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
        resolved_route_id = self._resolve_learning_path_id(route_id)
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
                grounded_chunks = await kb.query(resolved_route_id, query_text, k=k)
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
            cleaned_json = generated_json.strip()
            if cleaned_json.startswith("```"):
                first_nl = cleaned_json.find("\n")
                if first_nl != -1:
                    cleaned_json = cleaned_json[first_nl:].strip()
                if cleaned_json.endswith("```"):
                    cleaned_json = cleaned_json[:-3].strip()
            storyboard = json.loads(cleaned_json)
        except Exception as e:
            print(f"[storyboard] JSON parse error: {e}")
            print(f"[storyboard] Raw LLM response:\n{generated_json}\n---")
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

        scenes = storyboard.get("scenes", [])
        if not scenes:
            return storyboard

        # Repair unsafe or decorative choices before the reviewed storyboard is returned.
        for index, scene in enumerate(scenes):
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

            if scene.get("visual_type") == "ai_illustration":
                if not self._is_concrete_illustration_scene(scene):
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
                            "Sin una metafora didactica concreta, un visual explicativo ensena mejor que video generativo."
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

    def _hydrate_storyboard_for_render(self, storyboard: dict) -> dict:
        scenes = storyboard.get("scenes", [])
        if not isinstance(scenes, list):
            return storyboard

        title = str(storyboard.get("title") or "Explicacion visual")
        for index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                continue
            scene["visual_config"] = self._hydrate_visual_config(scene, index, title)
            self._repair_sparse_render_scene(scene)
        return storyboard

    def _repair_sparse_render_scene(self, scene: dict) -> None:
        """Keep direct render payloads visible without fabricating evidence."""
        visual_type = scene.get("visual_type")
        config = scene.get("visual_config") or {}
        focus = self._scene_focus_label(scene, "Idea clave")

        if visual_type == "screenshot_scene" and not (
            isinstance(config.get("steps"), list) and config["steps"]
        ):
            self._replace_with_text_card(
                scene,
                title=focus,
                subtitle="Demostracion visual no disponible; conserva la accion que debe aprenderse.",
                rationale="Sin pasos reales, una explicacion cualitativa evita fingir una interfaz.",
            )
        elif visual_type == "terminal_scene" and not config.get("steps"):
            self._replace_with_text_card(
                scene,
                title=focus,
                subtitle="Secuencia operativa explicada sin inventar comandos.",
                rationale="Sin comandos verificables, una tarjeta mantiene el contenido honesto.",
            )
        elif visual_type in {"bar_chart", "pie_chart", "kpi_grid"} and not self._has_renderable_chart_data(config.get("chartData")):
            self._replace_with_callout(
                scene,
                text=focus,
                rationale="Sin datos proporcionados, un visual cualitativo evita inventar cantidades.",
            )
        elif visual_type == "line_chart" and not self._normalize_line_chart_series(config.get("chartSeries"), focus):
            self._replace_with_callout(
                scene,
                text=focus,
                rationale="Sin una serie proporcionada, un visual cualitativo evita inventar una tendencia.",
            )
        elif visual_type == "stat_card" and not config.get("stat"):
            self._replace_with_callout(
                scene,
                text=focus,
                rationale="Sin una cantidad proporcionada, un callout evita presentar una metrica falsa.",
            )

    def _hydrate_visual_config(self, scene: dict, index: int, storyboard_title: str) -> dict:
        config = dict(scene.get("visual_config") or {})
        visual_type = scene.get("visual_type")
        focus = self._scene_focus_label(scene, storyboard_title)
        accent_title = config.get("title") or focus

        if visual_type == "text_card":
            config.setdefault("title", focus)
            config.setdefault("subtitle", str(scene.get("pedagogical_intent") or scene.get("narration") or storyboard_title)[:150])
            return config

        if visual_type == "hero_title":
            config.setdefault("text", focus)
            config.setdefault("subtitle", str(scene.get("pedagogical_intent") or storyboard_title)[:120])
            return config

        if visual_type == "stat_card":
            config.setdefault("title", accent_title)
            config.setdefault("stat", self._build_illustrative_stat(scene, index))
            config.setdefault("subtitle", focus)
            return config

        if visual_type == "callout":
            pattern = str(scene.get("teaching_pattern") or "").lower()
            default_style = "warning" if "misconception" in pattern else "tip" if "decision" in pattern else "info"
            config.setdefault("title", accent_title)
            config.setdefault("callout_style", default_style)
            config.setdefault("text", focus)
            return config

        if visual_type == "comparison":
            config.setdefault("title", accent_title)
            config.setdefault("leftLabel", "Sin aplicar")
            config.setdefault("leftValue", str(scene.get("pedagogical_intent") or "Estado inicial")[:90])
            config.setdefault("rightLabel", "Aplicado")
            config.setdefault("rightValue", focus[:90])
            return config

        if visual_type == "bar_chart":
            config.setdefault("title", accent_title)
            config.setdefault("chartData", self._build_illustrative_chart_data(scene, index, count=4))
            config.setdefault("showValues", True)
            config.setdefault("showGrid", True)
            config.setdefault("chartAnimation", "grow-up")
            return config

        if visual_type == "terminal_scene":
            config.setdefault("title", accent_title or "Terminal")
            steps = config.get("steps")
            if not isinstance(steps, list) or not steps:
                config["steps"] = [
                    {"kind": "out", "text": focus},
                ]
            return config

        if visual_type == "screenshot_scene":
            config.setdefault("title", accent_title or "Walkthrough")
            steps = config.get("steps")
            if not isinstance(steps, list) or not steps:
                config["steps"] = [
                    "cursor_move: 0.28 0.34",
                    "click_pulse: 0.28 0.34",
                    f"callout_balloon: 0.50 0.42 {focus[:90]}",
                    "highlight_box: 0.18 0.24 0.64 0.28",
                ]
            config.setdefault("purpose", str(scene.get("pedagogical_intent") or focus)[:120])
            config.setdefault("learning_outcome", str(scene.get("teaching_point") or focus)[:120])
            return config

        if visual_type == "kpi_grid":
            config.setdefault("title", accent_title or "Resumen de metricas")
            chart_data = config.get("chartData")
            if chart_data is None:
                chart_data = self._build_illustrative_chart_data(scene, index, count=3)
                config["chartData"] = chart_data
            config.setdefault("columns", min(4, max(2, len(chart_data))) if isinstance(chart_data, list) else 3)
            config.setdefault("chartAnimation", "count-up")
            return config

        if visual_type == "pie_chart":
            config.setdefault("title", accent_title or "Distribucion")
            chart_data = config.get("chartData")
            if chart_data is None:
                chart_data = self._build_illustrative_chart_data(scene, index, count=3, total=100)
                config["chartData"] = chart_data
            config.setdefault("donut", True)
            config.setdefault("centerLabel", "Composicion")
            total = (
                sum(float(item.get("value", 0)) for item in chart_data if isinstance(item, dict))
                if isinstance(chart_data, list)
                else 0
            )
            config.setdefault("centerValue", f"{total:g}%" if total == 100 else f"{total:g}")
            config.setdefault("showLegend", True)
            config.setdefault("chartAnimation", "expand")
            return config

        if visual_type == "line_chart":
            config.setdefault("title", accent_title or "Tendencia")
            series = config.get("chartSeries")
            config["chartSeries"] = self._normalize_line_chart_series(series, config.get("title") or focus)
            if not config["chartSeries"] and series is None:
                config["chartSeries"] = self._build_illustrative_line_series(scene, index)
            config.setdefault("showLegend", False)
            config.setdefault("showMarkers", True)
            config.setdefault("showGrid", True)
            config.setdefault("xLabel", "Intento")
            first_label = config["chartSeries"][0].get("label") if config["chartSeries"] else None
            config.setdefault("yLabel", first_label or "Valor")
            config.setdefault("chartAnimation", "draw")
            return config

        if visual_type == "progress_bar":
            config.setdefault("title", accent_title)
            steps = config.get("steps")
            if not isinstance(steps, list) or not steps:
                steps = [focus, str(scene.get("pedagogical_intent") or "Verificar el resultado")[:96]]
                config["steps"] = steps
            config.setdefault("progress", 100)
            config.setdefault("progressLabel", "Secuencia completa")
            config.setdefault("progressAnimation", "step")
            return config

        if visual_type == "ai_video":
            config.setdefault("prompt", self._build_video_prompt(scene, storyboard_title))
            return config

        if visual_type == "ai_illustration":
            config.setdefault("title", accent_title or "Diagrama conceptual")
            config.setdefault("prompt", self._build_illustration_prompt(scene, storyboard_title))
            bullets = config.get("bullets")
            if not isinstance(bullets, list) or not bullets:
                config["bullets"] = [
                    str(scene.get("teaching_point") or focus)[:96],
                    str(scene.get("pedagogical_intent") or scene.get("visual_rationale") or "Explicar el concepto con una ilustración técnica.")[:120],
                ]
            return config

        return config

    def _build_illustrative_stat(self, scene: dict, index: int) -> str:
        pattern = str(scene.get("teaching_pattern") or "").lower()
        if "process" in pattern or "proceso" in pattern:
            return "3 pasos"
        if "synthesis" in pattern or "decision" in pattern:
            return "1 accion"
        return f"{index + 1} clave"

    def _build_illustrative_chart_data(
        self,
        scene: dict,
        index: int,
        count: int,
        total: Optional[int] = None,
    ) -> list[dict]:
        labels = self._chart_labels_for_scene(scene, count)
        if total == 100:
            if count == 3:
                values = [45, 35, 20]
            elif count == 4:
                values = [35, 25, 22, 18]
            else:
                base = round(100 / count)
                values = [base for _ in range(count)]
                values[-1] += 100 - sum(values)
        else:
            start = 35 + (index % 3) * 5
            values = [start + step * (12 + index % 4) for step in range(count)]
        return [{"label": label, "value": values[i]} for i, label in enumerate(labels)]

    def _build_illustrative_line_series(self, scene: dict, index: int) -> list[dict]:
        label = self._scene_focus_label(scene, "Progreso")[:36]
        base = 25 + (index % 3) * 5
        points = [
            {"x": 1, "y": base},
            {"x": 2, "y": base + 18},
            {"x": 3, "y": base + 36},
            {"x": 4, "y": base + 50},
        ]
        return [{"label": label, "data": points}]

    def _chart_labels_for_scene(self, scene: dict, count: int) -> list[str]:
        pattern = str(scene.get("teaching_pattern") or "").lower()
        if "process" in pattern or "proceso" in pattern:
            labels = ["Explorar", "Aplicar", "Verificar", "Ajustar"]
        elif "synthesis" in pattern or "decision" in pattern:
            labels = ["Criterio", "Accion", "Evidencia", "Mejora"]
        elif "modelo" in pattern or "mental" in pattern:
            labels = ["Contexto", "Modelo", "Uso", "Resultado"]
        else:
            labels = ["Base", "Practica", "Aplicacion", "Impacto"]
        return labels[:count]

    def _has_renderable_chart_data(self, chart_data: Any) -> bool:
        if not isinstance(chart_data, list) or not chart_data:
            return False
        return all(
            isinstance(item, dict)
            and str(item.get("label") or "").strip()
            and isinstance(item.get("value"), (int, float))
            and not isinstance(item.get("value"), bool)
            for item in chart_data
        )

    def _normalize_line_chart_series(self, series: Any, fallback_label: str) -> list[dict]:
        if not isinstance(series, list) or not series:
            return []

        normalized = []
        for item in series:
            if not isinstance(item, dict):
                continue
            label = item.get("label") or item.get("name") or fallback_label or "Serie"
            raw_points = item.get("data") or []
            points = []
            if isinstance(raw_points, list):
                for point_index, point in enumerate(raw_points, start=1):
                    if isinstance(point, dict) and "x" in point and "y" in point:
                        points.append({"x": point["x"], "y": point["y"]})
                    elif isinstance(point, (int, float)):
                        points.append({"x": point_index, "y": point})
            if points:
                normalized.append({"label": label, "data": points})

        if normalized:
            return normalized

        return []

    def _scene_focus_label(self, scene: dict, storyboard_title: str) -> str:
        for key in ("teaching_point", "narration", "pedagogical_intent"):
            value = str(scene.get(key) or "").strip()
            if value:
                compact = value.replace("\n", " ")
                return compact[:72]
        return storyboard_title[:72]

    def _build_illustration_prompt(self, scene: dict, storyboard_title: str) -> str:
        focus = self._scene_focus_label(scene, storyboard_title)
        narration = str(scene.get("narration") or "").strip()
        teaching_point = str(scene.get("teaching_point") or focus).strip()
        intent = str(scene.get("pedagogical_intent") or "").strip()
        rationale = str(scene.get("visual_rationale") or "").strip()
        context = " | ".join(part for part in [teaching_point, narration, intent, rationale] if part)

        return (
            "A premium editorial educational illustration for a training video. "
            f"Video topic: {storyboard_title}. "
            f"Primary concept: {focus}. "
            f"Scene context: {context}. "
            "Show one coherent system, process, interface, or conceptual diagram directly related to the scene context, emphasizing the teaching relationship between action and evidence. "
            "Use clear visual hierarchy, directional flow, generous negative space, tactile geometric forms, deep ink background, teal and warm gold accents, subtle gradients, 16:9 wide composition, professional presentation quality. "
            "Avoid decorative stock imagery. Avoid biology, photosynthesis, plants, chloroplasts, classroom posters, and unrelated science diagrams. "
            "No logos, watermarks, decorative text, or text labels embedded in the illustration unless essential for diagram structure."
        )

    def _build_video_prompt(self, scene: dict, storyboard_title: str) -> str:
        focus = self._scene_focus_label(scene, storyboard_title)
        intent = str(scene.get("pedagogical_intent") or "Make the relationship visible").strip()
        return (
            f"A cinematic educational visual metaphor for {storyboard_title}. "
            f"The concrete concept is: {focus}. The visual action must communicate: {intent}. "
            "Show a specific subject changing through a clear cause-and-effect action over time, with a restrained documentary camera move, layered foreground and background, natural cinematic lighting, deep ink shadows, teal highlights and warm gold focal accents. "
            "Premium editorial cinematography, realistic materials, coherent spatial continuity, 16:9 composition, no people speaking to camera. "
            "No text, captions, logos, interfaces, glowing data streams, generic neural networks, random particles, or abstract technology background."
        )

    async def _load_render_target_context(
        self,
        route_id: str,
        module_id: str,
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
            route = await self._load_route_context_without_supabase(route_id, module_id)
            if route:
                ctx.update(route)
            return ctx

        resolved_route_id = self._resolve_learning_path_id(route_id)
        route_details = {}
        actual_route_id = resolved_route_id

        try:
            if component_id:
                comp = self._supabase.table("components").select("*").eq("id", str(component_id)).execute()
                if comp.data:
                    row = comp.data[0]
                    ctx["component_title"] = row.get("titulo") or row.get("tema")
        except Exception as e:
            print(f"[storyboard] component query error: {e}")

        try:
            lp = self._supabase.table("learning_paths").select("*").eq("id", str(resolved_route_id)).execute()
            if lp.data:
                row = lp.data[0]
                route_details = row.get("details") or {}
                ctx["route_title"] = row.get("titulo", "")
                ctx["route_tema"] = row.get("tema", "")
                ctx["route_storytelling"] = (
                    row.get("storytelling", "")
                    or row.get("brief", "")
                    or route_details.get("objective", "")
                    or route_details.get("brief", "")
                )
        except Exception as e:
            print(f"[storyboard] learning_path query error: {e}")

        try:
            mod = self._supabase.table("modules").select("*").eq("id", str(module_id)).execute()
            if mod.data:
                row = mod.data[0]
                ctx["module_title"] = row.get("titulo")
                ctx["module_type"] = row.get("tipo", "capsula")
                ctx["module_description"] = row.get("descripcion", "")
                actual_route_id = row.get("learning_path_id", resolved_route_id)
            else:
                modules = route_details.get("modules") or []
                matched = next(
                    (module for module in modules if str(module.get("id")) == str(module_id)),
                    None,
                )
                if matched:
                    ctx["module_title"] = (
                        matched.get("titulo")
                        or matched.get("title")
                        or matched.get("name")
                    )
                    ctx["module_type"] = matched.get("tipo") or matched.get("type") or "capsula"
                    ctx["module_description"] = (
                        matched.get("descripcion")
                        or matched.get("description")
                        or ""
                    )
        except Exception as e:
            print(f"[storyboard] module query error: {e}")

        if str(actual_route_id) != str(route_id):
            try:
                lp = self._supabase.table("learning_paths").select("*").eq("id", str(actual_route_id)).execute()
                if lp.data:
                    row = lp.data[0]
                    details = row.get("details") or {}
                    ctx["route_title"] = row.get("titulo", "")
                    ctx["route_tema"] = row.get("tema", "")
                    ctx["route_storytelling"] = (
                        row.get("storytelling", "")
                        or row.get("brief", "")
                        or details.get("objective", "")
                        or details.get("brief", "")
                    )
            except Exception as e:
                print(f"[storyboard] learning_path refresh error: {e}")

        # Fallback to local in-memory route context if Supabase has no record for this route/module
        if not ctx["module_title"]:
            fallback_route = await self._load_route_context_without_supabase(route_id, module_id)
            if fallback_route:
                for k, v in fallback_route.items():
                    if ctx.get(k) is None or ctx.get(k) == "":
                        ctx[k] = v

        return ctx

    def _resolve_learning_path_id(self, route_id: str) -> UUID:
        try:
            return UUID(str(route_id))
        except ValueError:
            try:
                return UUID(int=int(str(route_id)))
            except Exception:
                import hashlib
                return UUID(hashlib.md5(str(route_id).encode("utf-8")).hexdigest())

    async def _load_route_context_without_supabase(self, route_id: str, module_id: str) -> Optional[dict]:
        try:
            from config.dependencies import get_route_service

            route = await get_route_service().get_route(str(route_id))
            if not route:
                return None

            modules = route.get("modules") or []
            matched = next(
                (module for module in modules if str(module.get("id")) == str(module_id)),
                None,
            )

            return {
                "route_title": route.get("name") or route.get("titulo") or "",
                "route_tema": route.get("tema") or "",
                "route_storytelling": route.get("objective") or route.get("brief") or "",
                "module_title": (
                    matched.get("titulo")
                    or matched.get("title")
                    or matched.get("name")
                    if matched
                    else None
                ),
                "module_type": (
                    matched.get("tipo")
                    or matched.get("type")
                    if matched
                    else None
                ),
                "module_description": (
                    matched.get("descripcion")
                    or matched.get("description")
                    if matched
                    else ""
                ),
                "component_title": None,
            }
        except Exception as e:
            print(f"[storyboard] fallback route context error: {e}")
            return None

    async def get_video_job_status(self, job_id: UUID) -> Optional[VideoJobResponse]:
        job = await self.get_video_job_record(job_id)
        if not job:
            return None

        result_data = None
        if job.get("result") and job["result"].get("video_url"):
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
            error=job.get("error"),
            observability=(job.get("result") or {}).get("observability"),
        )

    async def get_video_job_record(self, job_id: UUID) -> Optional[dict]:
        """Return the shared Job shape so generic polling can resume video jobs."""
        mock_status = await self.mock_service.get_video_job_status(job_id)
        if mock_status:
            now_str = datetime.now(timezone.utc).isoformat()
            return {
                "id": str(mock_status.job_id),
                "type": "video_generation",
                "status": mock_status.status.value,
                "progress": mock_status.progress,
                "created_at": now_str,
                "updated_at": now_str,
                "result": mock_status.result.model_dump() if mock_status.result else None,
                "error": mock_status.error,
            }

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

        return job

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
        render_target: Optional[dict] = None,
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

            effective_storyboard = executor.effective_storyboard or storyboard
            scenes = effective_storyboard.get("scenes", [])
            total_duration = executor.total_duration
            veo_scenes = sum(1 for s in scenes if s.get("visual_type") == "ai_video")
            imagen_scenes = sum(1 for s in scenes if s.get("visual_type") == "ai_illustration")
            estimated_cost = (veo_scenes * 0.20) + (imagen_scenes * 0.04) + (0.004 * total_duration)

            final_url = executor.stage_outputs.get("upload", {}).get("url", "")
            render_provenance = self._build_render_provenance(effective_storyboard, storyboard_source)
            if executor.visual_fallbacks:
                render_provenance["visual_fallbacks"] = executor.visual_fallbacks
            result = {
                "video_url": final_url,
                "duration_seconds": round(total_duration, 2),
                "cost_usd": round(estimated_cost, 2),
                "provenance": render_provenance,
            }
            await self._update_job(job_id, JobStatus.COMPLETED, 100, result=result)
            await self._record_job_event(job_id, "job", "completed", "Video generation completed")

            if component_id:
                await self._update_asset_completed(
                    component_id,
                    final_url,
                    render_provenance,
                    render_target=render_target,
                    job_id=job_id,
                )

        except Exception as e:
            print(f"[Job {job_id}] Critical error during video rendering: {e}")
            import traceback
            traceback.print_exc()
            await self._record_job_event(job_id, "job", "failed", str(e))
            await self._update_job(job_id, JobStatus.FAILED, 100, error=str(e))

        finally:
            remotion_job_dir = os.path.join(settings.remotion_composer_path, "public", str(job_id))
            await asyncio.gather(
                asyncio.to_thread(shutil.rmtree, temp_dir, True),
                asyncio.to_thread(shutil.rmtree, remotion_job_dir, True),
            )
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
            payload["result"] = {
                **result,
                "observability": self._job_observability.get(job_id, {"current_stage": None, "events": []}),
            }
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

    async def _record_job_event(
        self,
        job_id: UUID,
        stage: str,
        status: str,
        message: str,
        *,
        elapsed_ms: Optional[int] = None,
        completed_scenes: Optional[int] = None,
        total_scenes: Optional[int] = None,
    ) -> None:
        telemetry = self._job_observability.setdefault(job_id, {"current_stage": None, "events": []})
        telemetry["current_stage"] = None if status in {"completed", "failed", "cancelled"} else stage
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "status": status,
            "message": message,
        }
        if elapsed_ms is not None:
            event["elapsed_ms"] = elapsed_ms
        if completed_scenes is not None:
            event["completed_scenes"] = completed_scenes
        if total_scenes is not None:
            event["total_scenes"] = total_scenes
        telemetry["events"].append(event)

        job = await self.get_video_job_record(job_id)
        if not job:
            return
        current_result = job.get("result") or {}
        await self._update_job(
            job_id,
            JobStatus(job["status"]),
            job.get("progress", 0),
            result={**current_result, "observability": telemetry},
        )

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

    async def get_video_asset_for_render_target(
        self,
        route_id: str,
        module_id: str,
        component_kind: str = "video",
    ) -> dict:
        component_id = await self._resolve_video_component_id(
            route_id=route_id,
            module_id=module_id,
            component_kind=component_kind,
            create_if_missing=False,
        )
        if component_id:
            asset = await self._get_video_asset(component_id)
            if asset:
                return asset

        detail_asset = await self._get_route_detail_video_asset(route_id, module_id, component_kind)
        return detail_asset or {}

    async def _resolve_video_component_id(
        self,
        route_id: str,
        module_id: str,
        component_kind: str,
        create_if_missing: bool,
    ) -> UUID:
        if self._supabase:
            try:
                res = (
                    self._supabase.table("components")
                    .select("*")
                    .eq("modulo_id", str(module_id))
                    .eq("tipo", component_kind)
                    .execute()
                )
                if res.data:
                    return UUID(res.data[0]["id"])
            except Exception as e:
                print(f"Supabase query video component error: {e}")

            if create_if_missing:
                try:
                    module_uuid = UUID(str(module_id))
                    component_id = uuid4()
                    now_str = datetime.now(timezone.utc).isoformat()
                    payload = {
                        "id": str(component_id),
                        "modulo_id": str(module_uuid),
                        "titulo": "Video",
                        "tipo": component_kind,
                        "orden": 0,
                        "created_at": now_str,
                        "updated_at": now_str,
                    }
                    self._supabase.table("components").insert(payload).execute()
                    return component_id
                except Exception as e:
                    print(f"Supabase create video component error, using render-target fallback: {e}")

        return self._render_target_component_id(route_id, module_id, component_kind)

    def _render_target_component_id(self, route_id: str, module_id: str, component_kind: str) -> UUID:
        key = f"{route_id}:{module_id}:{component_kind}"
        return UUID(hashlib.md5(key.encode("utf-8")).hexdigest())

    async def _ensure_video_asset_started(
        self,
        component_id: UUID,
        storyboard: dict,
        storyboard_source: str,
    ) -> None:
        existing_asset = await self._get_video_asset(component_id)
        existing_provenance = (
            existing_asset.get("provenance")
            if existing_asset and isinstance(existing_asset.get("provenance"), dict)
            else {}
        )
        asset_id = existing_asset.get("id") if existing_asset else str(uuid4())
        now_str = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": str(asset_id),
            "componente_id": str(component_id),
            "tipo": "video",
            "estado": "draft",
            "word_budget": storyboard.get("total_word_budget", 300),
            "provenance": {
                **existing_provenance,
                **self._build_render_provenance(storyboard, storyboard_source),
            },
            "updated_at": now_str,
        }
        if not existing_asset:
            payload["created_at"] = now_str

        if self._supabase:
            try:
                if existing_asset:
                    self._supabase.table("assets").update(payload).eq("id", str(asset_id)).execute()
                else:
                    self._supabase.table("assets").insert(payload).execute()
                return
            except Exception as e:
                print(f"Supabase start video asset error, falling back to memory: {e}")

        current_asset = self._fallback_assets.get(component_id, existing_asset or {})
        current_asset.update(payload)
        self._fallback_assets[component_id] = current_asset

    async def _update_asset_completed(
        self,
        component_id: UUID,
        video_url: str,
        render_provenance: Optional[dict] = None,
        render_target: Optional[dict] = None,
        job_id: Optional[UUID] = None,
    ):
        now_str = datetime.now(timezone.utc).isoformat()
        existing_asset = await self._get_video_asset(component_id)
        existing_provenance = (
            existing_asset.get("provenance")
            if existing_asset and isinstance(existing_asset.get("provenance"), dict)
            else {}
        )
        payload = {
            "id": str(existing_asset.get("id") or uuid4()),
            "componente_id": str(component_id),
            "tipo": "video",
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

        if render_target:
            await self._persist_route_detail_video_asset(
                route_id=render_target["route_id"],
                module_id=render_target["module_id"],
                component_kind=render_target["component_kind"],
                asset={
                    **payload,
                    "job_id": str(job_id) if job_id else None,
                },
            )

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

    async def _persist_route_detail_video_asset(
        self,
        route_id: str,
        module_id: str,
        component_kind: str,
        asset: dict,
    ) -> None:
        if not self._supabase:
            return
        try:
            resolved_route_id = self._resolve_learning_path_id(route_id)
            res = self._supabase.table("learning_paths").select("*").eq("id", str(resolved_route_id)).execute()
            if not res.data:
                return
            row = res.data[0]
            details = row.get("details") or {}
            video_assets = details.get("video_assets") or {}
            video_assets[self._route_detail_asset_key(module_id, component_kind)] = asset
            details["video_assets"] = video_assets
            self._supabase.table("learning_paths").update({"details": details}).eq("id", str(resolved_route_id)).execute()
        except Exception as e:
            print(f"Supabase route-detail video asset fallback error: {e}")

    async def _get_route_detail_video_asset(
        self,
        route_id: str,
        module_id: str,
        component_kind: str,
    ) -> dict:
        if not self._supabase:
            return {}
        try:
            resolved_route_id = self._resolve_learning_path_id(route_id)
            res = self._supabase.table("learning_paths").select("*").eq("id", str(resolved_route_id)).execute()
            if not res.data:
                return {}
            details = res.data[0].get("details") or {}
            return (details.get("video_assets") or {}).get(
                self._route_detail_asset_key(module_id, component_kind),
                {},
            )
        except Exception as e:
            print(f"Supabase get route-detail video asset error: {e}")
            return {}

    def _route_detail_asset_key(self, module_id: str, component_kind: str) -> str:
        return f"{module_id}:{component_kind}"

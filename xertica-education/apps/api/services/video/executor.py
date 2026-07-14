import os
import sys
import json
import shutil
import subprocess
import asyncio
import copy
import time
from pathlib import Path
from uuid import UUID
from typing import Optional, Dict, Any, List

from config.settings import settings
from models.common import JobStatus
from models.dto.render_plan import RenderPlan, RenderStage
from services.video.transformer import transform_storyboard_to_edit_decisions
from adapters.audio.pixabay_music import PixabayMusicAdapter


class RenderExecutor:

    def __init__(self, video_service):
        self.video_service = video_service
        self.stage_outputs: Dict[str, Any] = {}
        self.audio_paths: List[str] = []
        self.durations: List[float] = []
        self.visual_paths: List[str] = []
        self.visual_is_video: List[bool] = []
        self.music_path: Optional[str] = None
        self.captions: Optional[List[dict]] = None
        self.edit_decisions: Optional[dict] = None
        self.effective_storyboard: Optional[dict] = None
        self.total_duration: float = 0.0
        self.visual_fallbacks: List[dict] = []

    async def execute(self, plan: RenderPlan) -> None:
        job_id = plan.job_id
        storyboard = plan.storyboard.model_dump() if hasattr(plan.storyboard, "model_dump") else plan.storyboard
        storyboard = self.video_service._hydrate_storyboard_for_render(copy.deepcopy(storyboard))
        self.effective_storyboard = storyboard
        scenes = storyboard.get("scenes", [])
        temp_dir = f"/tmp/render_{job_id}"
        os.makedirs(temp_dir, exist_ok=True)

        await self._run_stage(plan, "tts", 5, self._stage_tts, job_id, scenes, temp_dir)
        await self._run_stage(plan, "visual", 25, self._stage_visual, job_id, scenes, temp_dir)
        await self._run_stage(plan, "music", 35, self._stage_music, job_id, temp_dir)
        await self._run_stage(plan, "transform", 45, self._stage_transform, job_id, storyboard)
        await self._run_stage(plan, "remotion_render", 65, self._stage_remotion_render, job_id, temp_dir)
        await self._run_stage(plan, "validate", 85, self._stage_validate, job_id, temp_dir)
        await self._run_stage(plan, "upload", 95, self._stage_upload, job_id, temp_dir)

    async def _run_stage(self, plan: RenderPlan, stage_type: str, progress: int, fn, *args):
        stage = next(s for s in plan.stages if s.stage_type == stage_type)
        stage.status = JobStatus.RUNNING
        started_at = time.monotonic()
        await self._record_event(plan.job_id, stage_type, "running", f"Started {stage_type}")
        await self.video_service._update_job(plan.job_id, JobStatus.RUNNING, progress)
        try:
            await fn(*args)
            stage.status = JobStatus.COMPLETED
            await self._record_event(
                plan.job_id, stage_type, "completed", f"Completed {stage_type}",
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
        except asyncio.CancelledError:
            await self._record_event(
                plan.job_id, stage_type, "cancelled", f"Cancelled during {stage_type}",
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
            raise
        except Exception as e:
            stage.status = JobStatus.FAILED
            stage.error = str(e)
            await self._record_event(
                plan.job_id, stage_type, "failed", str(e),
                elapsed_ms=round((time.monotonic() - started_at) * 1000),
            )
            raise

    async def _stage_tts(self, job_id: UUID, scenes: list, temp_dir: str):
        all_captions: List[dict] = []
        cumulative_ms = 0
        total_scenes = len(scenes)
        ordered_results: List[Optional[dict]] = [None] * total_scenes

        tasks = [
            asyncio.create_task(
                self._synthesize_scene_audio(index, scene, temp_dir)
            )
            for index, scene in enumerate(scenes)
        ]
        try:
            for completed_count, task in enumerate(asyncio.as_completed(tasks), start=1):
                result = await task
                ordered_results[result["index"]] = result
                await self._update_stage_scene_progress(
                    job_id=job_id,
                    stage_start=5,
                    stage_end=24,
                    completed=completed_count,
                    total=total_scenes,
                )
                await self._record_event(
                    job_id, "tts", "progress", "Narration synthesized",
                    completed_scenes=completed_count, total_scenes=total_scenes,
                )
        except Exception:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        for result in ordered_results:
            if result is None:
                continue

            for cap in result["captions"]:
                cap["startMs"] += cumulative_ms
                cap["endMs"] += cumulative_ms
            all_captions.extend(result["captions"])

            self.audio_paths.append(result["audio_path"])
            self.durations.append(result["duration"])
            cumulative_ms += int(result["duration"] * 1000)

        self.total_duration = sum(self.durations)
        if all_captions:
            self.captions = all_captions

        merged_path = f"{temp_dir}/narration_merged.mp3"
        if len(self.audio_paths) > 1:
            await asyncio.to_thread(self._concat_audio_files, self.audio_paths, merged_path)
        elif len(self.audio_paths) == 1:
            await asyncio.to_thread(shutil.copy, self.audio_paths[0], merged_path)

    async def _stage_visual(self, job_id: UUID, scenes: list, temp_dir: str):
        total_scenes = len(scenes)
        ordered_results: List[Optional[dict]] = [None] * total_scenes
        tasks = [
            asyncio.create_task(
                self._render_scene_visual(index, scene, temp_dir)
            )
            for index, scene in enumerate(scenes)
        ]
        try:
            for completed_count, task in enumerate(asyncio.as_completed(tasks), start=1):
                result = await task
                ordered_results[result["index"]] = result
                await self._update_stage_scene_progress(
                    job_id=job_id,
                    stage_start=25,
                    stage_end=34,
                    completed=completed_count,
                    total=total_scenes,
                )
                await self._record_event(
                    job_id, "visual", "progress", "Visual prepared",
                    completed_scenes=completed_count, total_scenes=total_scenes,
                )
        except Exception:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        for result in ordered_results:
            if result is None:
                continue
            self.visual_paths.append(result["path"])
            self.visual_is_video.append(result["is_video"])

    async def _stage_music(self, job_id: UUID, temp_dir: str):
        try:
            adapter = PixabayMusicAdapter()
            music_path = await adapter.search_and_download(
                query="corporate educational ambient",
                output_path=f"{temp_dir}/bg_music.mp3"
            )
            if music_path:
                self.music_path = music_path
        except Exception as e:
            print(f"Music stage failed: {e}")

    async def _stage_transform(self, job_id: UUID, storyboard: dict):
        self.edit_decisions = await transform_storyboard_to_edit_decisions(
            storyboard=storyboard,
            audio_paths=self.audio_paths,
            durations=self.durations,
            visual_paths=self.visual_paths,
            visual_is_video=self.visual_is_video,
            music_path=self.music_path,
            captions=self.captions,
            total_duration=self.total_duration,
            job_id=str(job_id),
        )
        self.stage_outputs["transform"] = {"edit_decisions": self.edit_decisions}

    async def _stage_remotion_render(self, job_id: UUID, temp_dir: str):
        composer_dir = Path(settings.remotion_composer_path)
        public_dir = composer_dir / "public" / str(job_id)
        public_dir.mkdir(parents=True, exist_ok=True)

        for path in self.visual_paths:
            if path and os.path.exists(path):
                shutil.copy(path, public_dir / Path(path).name)

        merged_narration = f"{temp_dir}/narration_merged.mp3"
        if os.path.exists(merged_narration):
            shutil.copy(merged_narration, public_dir / "narration_merged.mp3")

        if self.music_path and os.path.exists(self.music_path):
            shutil.copy(self.music_path, public_dir / Path(self.music_path).name)

        props_path = public_dir / "edit_decisions.json"
        with open(props_path, "w") as f:
            json.dump(self.edit_decisions, f)

        output_path = public_dir / "output.mp4"
        local_bin = composer_dir / "node_modules" / ".bin" / "remotion"
        if local_bin.exists():
            cmd = [
                str(local_bin), "render", "src/index.tsx", "Explainer",
                str(output_path),
                "--props", str(props_path),
                "--codec", "h264",
            ]
        else:
            cmd = [
                "npx", "--package=@remotion/cli", "remotion", "render", "src/index.tsx", "Explainer",
                str(output_path),
                "--props", str(props_path),
                "--codec", "h264",
            ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=composer_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=1200)
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise

        if process.returncode:
            print(f"Remotion render failed with code {process.returncode}")
            print(f"Remotion render stderr: {stderr.decode(errors='replace')}")
            print(f"Remotion render stdout: {stdout.decode(errors='replace')}")
            raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)

        final_output = f"{temp_dir}/final_{job_id}.mp4"
        shutil.copy(str(output_path), final_output)
        self.stage_outputs["remotion_render"] = {"output_path": final_output}

    async def _stage_validate(self, job_id: UUID, temp_dir: str):
        output_path = self.stage_outputs.get("remotion_render", {}).get("output_path", "")
        if not output_path or not os.path.exists(output_path):
            return
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size",
            "-of", "default=noprint_wrappers=1:nokey=1",
            output_path,
        ]
        result = await asyncio.to_thread(
            subprocess.run,
            probe_cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().split("\n")
        self.stage_outputs["validate"] = {
            "duration": float(lines[0]) if lines and lines[0] else 0.0,
            "size_bytes": int(lines[1]) if len(lines) > 1 and lines[1] else 0,
        }

    async def _stage_upload(self, job_id: UUID, temp_dir: str):
        output_path = self.stage_outputs.get("remotion_render", {}).get("output_path", "")
        if not output_path or not os.path.exists(output_path):
            return
        video_data = await asyncio.to_thread(Path(output_path).read_bytes)
        storage_path = f"videos/{job_id}/capsule.mp4"
        url = await self.video_service.storage_adapter.upload_file(
            settings.storage_bucket, storage_path, video_data
        )
        self.stage_outputs["upload"] = {"url": url}

    def _concat_audio_files(self, audio_paths: list, output_path: str):
        """Concatenate multiple audio files using FFmpeg's concat audio filter."""
        if len(audio_paths) == 1:
            shutil.copy(audio_paths[0], output_path)
            return

        inputs = []
        filter_inputs = []
        for i, p in enumerate(audio_paths):
            inputs.extend(["-i", os.path.abspath(p)])
            filter_inputs.append(f"[{i}:a]")

        filter_complex = "".join(filter_inputs) + f"concat=n={len(audio_paths)}:v=0:a=1"
        codec = "libmp3lame" if output_path.endswith(".mp3") else "aac"
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-c:a", codec, "-b:a", "192k",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg concat stderr: {result.stderr}")
            print(f"FFmpeg concat stdout: {result.stdout}")
            print(f"Audio paths: {audio_paths}")
            raise subprocess.CalledProcessError(result.returncode, cmd)

    async def _capture_url_screenshot(self, url: str, output_path: str) -> bool:
        if not url:
            await asyncio.to_thread(self._create_placeholder_image, output_path)
            return True
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                await page.goto(url, timeout=30000)
                await page.wait_for_timeout(1000)
                await page.screenshot(path=output_path)
                await browser.close()
            return True
        except Exception as e:
            print(f"Screenshot capture failed for {url}: {e}")
            await asyncio.to_thread(self._create_placeholder_image, output_path)
            return True

    def _create_placeholder_image(self, output_path: str, width: int = 1920, height: int = 1080):
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(img)
            for y in range(height):
                ratio = y / height
                r = int(12 + (24 - 12) * ratio)
                g = int(22 + (44 - 22) * ratio)
                b_val = int(38 + (58 - 38) * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b_val))
            draw.rounded_rectangle((180, 150, 1740, 930), radius=36, outline=(92, 211, 181), width=6)
            draw.rounded_rectangle((250, 230, 1650, 330), radius=20, fill=(26, 46, 70), outline=(244, 185, 66), width=3)
            draw.rounded_rectangle((250, 380, 1050, 840), radius=24, fill=(18, 35, 55), outline=(86, 123, 156), width=3)
            draw.rounded_rectangle((1120, 380, 1650, 840), radius=24, fill=(18, 35, 55), outline=(86, 123, 156), width=3)
            img.save(output_path, "PNG")
        except Exception:
            pass

    async def _synthesize_scene_audio(self, index: int, scene: dict, temp_dir: str) -> dict:
        scene_num = scene.get("scene_number", index + 1)
        audio_path = f"{temp_dir}/audio_{scene_num}.mp3"
        narration = scene.get("narration", "")

        if hasattr(self.video_service.tts_adapter, "text_to_speech_with_timestamps"):
            result = await self._run_async_callable_in_thread(
                self.video_service.tts_adapter.text_to_speech_with_timestamps,
                narration,
                audio_path,
            )
            return {
                "index": index,
                "audio_path": audio_path,
                "duration": result.duration_seconds,
                "captions": list(result.captions),
            }

        duration = await self._run_async_callable_in_thread(
            self.video_service.tts_adapter.text_to_speech,
            narration,
            audio_path,
        )
        return {
            "index": index,
            "audio_path": audio_path,
            "duration": duration,
            "captions": [],
        }

    async def _render_scene_visual(self, index: int, scene: dict, temp_dir: str) -> dict:
        scene_num = scene.get("scene_number", index + 1)
        visual_type = scene.get("visual_type", "")
        config = scene.get("visual_config", {})
        duration = self.durations[index] if index < len(self.durations) else 5.0

        if visual_type == "ai_video":
            vid_path = f"{temp_dir}/visual_{scene_num}.mp4"
            prompt = config.get("prompt", "abstract cinematic animation, dark background, blue tones")
            try:
                await self._run_async_callable_in_thread(
                    self.video_service.veo_adapter.render_clip,
                    prompt,
                    duration,
                    vid_path,
                )
            except Exception as error:
                self._fallback_generated_visual(scene, error)
                return {"index": index, "path": "", "is_video": False}
            return {"index": index, "path": vid_path, "is_video": True}

        if visual_type == "ai_illustration":
            img_path = f"{temp_dir}/visual_{scene_num}.png"
            prompt = config.get("prompt", "educational diagram, clean design")
            try:
                await self._run_async_callable_in_thread(
                    self.video_service.imagen_adapter.generate_illustration,
                    prompt,
                    img_path,
                )
            except Exception as error:
                self._fallback_generated_visual(scene, error)
                return {"index": index, "path": "", "is_video": False}
            return {"index": index, "path": img_path, "is_video": False}

        if visual_type == "screenshot_scene":
            img_path = f"{temp_dir}/visual_{scene_num}.png"
            url = config.get("url", "")
            captured = await self._capture_url_screenshot(url, img_path)
            if not captured:
                self._fallback_generated_visual(scene, RuntimeError("screenshot unavailable"))
                return {"index": index, "path": "", "is_video": False}
            return {"index": index, "path": img_path, "is_video": False}

        return {"index": index, "path": "", "is_video": False}

    def _fallback_generated_visual(self, scene: dict, error: Exception) -> None:
        original_visual_type = str(scene.get("visual_type") or "unknown")
        teaching_point = str(scene.get("teaching_point") or scene.get("narration") or "Idea clave").strip()
        intent = str(scene.get("pedagogical_intent") or "Idea clave").strip()
        self.visual_fallbacks.append({
            "scene_number": scene.get("scene_number"),
            "original_visual_type": original_visual_type,
            "fallback_visual_type": "callout",
            "reason": str(error)[:240],
        })
        scene["visual_type"] = "callout"
        scene["visual_config"] = {
            "title": intent,
            "text": teaching_point,
            "callout_style": "tip",
        }
        print(f"Generated visual failed; using native callout: {error}")

    async def _update_stage_scene_progress(
        self,
        job_id: UUID,
        stage_start: int,
        stage_end: int,
        completed: int,
        total: int,
    ) -> None:
        if total <= 0:
            return

        span = max(stage_end - stage_start, 0)
        progress = stage_start + round((completed / total) * span)
        await self.video_service._update_job(job_id, JobStatus.RUNNING, progress)

    async def _record_event(self, job_id: UUID, stage: str, status: str, message: str, **details) -> None:
        record_event = getattr(self.video_service, "_record_job_event", None)
        if record_event:
            await record_event(job_id, stage, status, message, **details)

    async def _run_async_callable_in_thread(self, async_callable, *args):
        return await asyncio.to_thread(self._run_async_callable_sync, async_callable, *args)

    @staticmethod
    def _run_async_callable_sync(async_callable, *args):
        return asyncio.run(async_callable(*args))

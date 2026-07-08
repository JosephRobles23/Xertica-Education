"""Google Veo 3.1 adapter for generating AI video clips.

How it works fundamentally:
    Video generation is computationally expensive — it takes 60-120 seconds to
    render even a short 6-8 second clip. Because of this, the Veo API uses a
    "long-running operation" pattern:

    1. You SUBMIT the request (prompt + duration) → API returns an "operation" object
    2. You POLL the operation every ~20 seconds, asking "is it done yet?"
    3. When operation.done == True, you DOWNLOAD the video file

    Think of it like ordering food at a restaurant:
    - You place your order (submit request)
    - You get a receipt number (operation ID)
    - You keep checking the pickup counter (polling)
    - When your number is called (operation.done), you pick up your food (download)

    The google-genai SDK handles most of this, but we still need to manage
    the polling loop and timeout ourselves.

    In mock mode (no credentials), we write a minimal valid MP4 file header
    so the pipeline doesn't crash during FFmpeg composition.
"""

import os
import time
import asyncio
import subprocess
from typing import Optional

from config.settings import settings
from adapters.renderer.base import BaseRendererAdapter

# Try to import the Google GenAI SDK.
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GoogleVeoAdapter(BaseRendererAdapter):
    """Generates short cinematic video clips using Google Veo 3.1 via Vertex AI.

    The adapter has two modes:
      - REAL: Calls the Veo 3.1 API to generate a video from a text prompt.
              Uses long-running operations with polling. The result is a real
              MP4 file suitable for stitching into the final educational video.
      - MOCK: Writes a minimal valid MP4 header (16 bytes) so FFmpeg can still
              process the file without crashing.
    """

    # How often to check if the video is ready (seconds).
    POLL_INTERVAL_SECONDS = 20

    # Maximum time to wait for a video to generate (seconds).
    # Veo typically takes 60-120s for a 6-8s clip; 5 minutes is a safe ceiling.
    MAX_WAIT_SECONDS = 300

    def __init__(self, api_key: Optional[str] = None):
        # The api_key parameter is kept for backward compatibility with the
        # old interface, but the real SDK uses Application Default Credentials.
        self.api_key = api_key or os.getenv("VEO_KEY")
        self.is_mock = (
            not GENAI_AVAILABLE
            or "placeholder" in settings.google_cloud_project
            or not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )

        self._client = None
        if not self.is_mock:
            try:
                self._client = genai.Client(
                    vertexai=True,
                    project=settings.google_cloud_project,
                    location=settings.google_cloud_location,
                )
            except Exception as e:
                print(f"Failed to initialize GenAI client for Veo: {e}")
                self.is_mock = True

        if self.is_mock:
            print("Google Veo 3.1 credentials not found. GoogleVeoAdapter running in MOCK mode.")

    async def render_video(self, prompt: str, storyboard: Optional[dict] = None) -> str:
        """Legacy interface from BaseRendererAdapter. Use render_clip() instead."""
        raise NotImplementedError("Use render_clip() for scene-level rendering.")

    async def render_clip(self, prompt: str, duration_seconds: float, output_path: str) -> str:
        """Generate an AI video clip and save it as an MP4 file.

        Args:
            prompt: A text description of the video to generate. For educational
                    intros, use abstract visual metaphors (e.g., "Glowing neural
                    network pathways forming connections, cinematic, dark
                    background, blue tones").
            duration_seconds: Target clip length in seconds. Veo 3.1 supports
                              approximately 6 or 8 second clips. Values are
                              rounded to the nearest supported duration.
            output_path: Where to save the resulting MP4 file.

        Returns:
            The output_path where the video was saved.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.is_mock:
            return self._write_mock_mp4(output_path, duration_seconds, prompt)

        try:
            return await self._generate_real_video(prompt, duration_seconds, output_path)
        except Exception as e:
            print(f"Veo 3.1 API error: {e}. Falling back to mock MP4.")
            return self._write_mock_mp4(output_path, duration_seconds, prompt)

    async def _generate_real_video(
        self, prompt: str, duration_seconds: float, output_path: str
    ) -> str:
        """Call the Veo 3.1 API and poll until the video is ready.

        This is the heart of the adapter. Here's the step-by-step:
        1. Send generate_videos() → get back an "operation" (a ticket)
        2. Loop: sleep 20s, then ask "is my video ready?"
        3. When ready: download the video bytes and write to disk
        """
        # Clamp duration to a Veo-supported value.
        # Veo 3.1 works best with 6 or 8 second durations.
        veo_duration = 8 if duration_seconds > 7 else 6

        # Step 1: Submit the generation request.
        # This returns immediately with an operation handle — the actual
        # rendering happens on Google's servers.
        operation = self._client.models.generate_videos(
            model=settings.veo_model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=veo_duration,
            ),
        )

        # Step 2: Poll until the operation completes.
        # We run the polling in a thread pool so we don't block the async
        # event loop (asyncio can't natively "await" a time.sleep loop).
        result_video = await asyncio.to_thread(
            self._poll_until_done, operation
        )

        if result_video is None:
            print("Veo 3.1 timed out or returned no video. Falling back to mock.")
            return self._write_mock_mp4(output_path, duration_seconds, prompt)

        # Step 3: Download the video file.
        # The SDK provides a download method that fetches the actual bytes.
        video_bytes = await asyncio.to_thread(
            self._download_video, result_video
        )

        if video_bytes:
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            print(f"Veo 3.1 video saved: {output_path} ({len(video_bytes)} bytes)")
            return output_path
        else:
            print("Failed to download Veo video. Falling back to mock.")
            return self._write_mock_mp4(output_path, duration_seconds, prompt)

    def _poll_until_done(self, operation):
        """Synchronous polling loop (runs in a thread).

        Checks every POLL_INTERVAL_SECONDS whether the Veo operation has
        finished. Returns the first generated video, or None on timeout.
        """
        elapsed = 0
        while not operation.done:
            if elapsed >= self.MAX_WAIT_SECONDS:
                print(f"Veo 3.1 operation timed out after {elapsed}s.")
                return None

            print(f"Veo 3.1: waiting... ({elapsed}s elapsed)")
            time.sleep(self.POLL_INTERVAL_SECONDS)
            elapsed += self.POLL_INTERVAL_SECONDS

            # Refresh the operation status from the API.
            try:
                operation = self._client.operations.get(operation)
            except Exception as e:
                print(f"Error polling Veo operation: {e}")
                return None

        # Operation is done — extract the video from the response.
        if operation.response and operation.response.generated_videos:
            return operation.response.generated_videos[0]

        print("Veo 3.1 operation completed but returned no videos.")
        return None

    def _download_video(self, generated_video):
        """Download the video bytes from the generated video object.

        Under Vertex AI, the bytes are often already populated in the video_bytes
        field of the response object, and calling files.download() is unsupported.
        """
        try:
            # 1. Direct check: under Vertex AI, bytes are already on the object
            if hasattr(generated_video, 'video') and hasattr(generated_video.video, 'video_bytes'):
                if generated_video.video.video_bytes:
                    print("  Veo video bytes extracted directly from response.")
                    return generated_video.video.video_bytes

            # 2. Fallback: try calling download (for Gemini Developer API)
            try:
                self._client.files.download(file=generated_video.video)
                if hasattr(generated_video.video, 'video_bytes'):
                    return generated_video.video.video_bytes
            except Exception as dl_err:
                print(f"  Warning: files.download failed or unsupported: {dl_err}")

            # 3. Alternate check: file-like object read
            if hasattr(generated_video, 'video'):
                video_obj = generated_video.video
                if hasattr(video_obj, 'read'):
                    return video_obj.read()

            print("Could not extract video bytes from Veo response object.")
            return None
        except Exception as e:
            print(f"Error downloading Veo video: {e}")
            return None

    def _write_mock_mp4(self, output_path: str, duration_seconds: float = 6.0, prompt: str = "") -> str:
        """Write a valid mock MP4 file by generating an image and converting it with FFmpeg.

        This ensures the mock mode produces a fully playable video clip with matching
        attributes (1920x1080, 30fps) that FFmpeg can stitch without errors.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            PILLOW_AVAILABLE = True
        except ImportError:
            PILLOW_AVAILABLE = False

        temp_img_path = output_path + ".temp.png"

        if PILLOW_AVAILABLE:
            width, height = 1920, 1080
            img = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(img)

            # Draw a beautiful dark navy to purple gradient matching the slide styling
            for y in range(height):
                ratio = y / height
                r = int(15 + (30 - 15) * ratio)
                g = int(23 + (27 - 23) * ratio)
                b = int(42 + (75 - 42) * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
                font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            except Exception:
                font = ImageFont.load_default()
                font_title = ImageFont.load_default()

            # Header box
            draw.rectangle([80, 150, width - 80, 250], fill=(20, 20, 40))
            draw.text((100, 175), "[GOOGLE VEO 3.1 MOCK VIDEO]", fill=(255, 100, 100), font=font_title)

            # Word-wrap prompt to overlay it
            max_chars = 60
            lines = []
            words = prompt.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_chars:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            y_start = 350
            for i, line in enumerate(lines):
                text_y = y_start + i * 40
                draw.rectangle([80, text_y - 5, width - 80, text_y + 35], fill=(20, 20, 40))
                draw.text((100, text_y), line, fill=(200, 200, 255), font=font)

            # Info box
            draw.rectangle([80, height - 120, width - 80, height - 60], fill=(15, 15, 30))
            draw.text((100, height - 100), f"Duración simulada: {duration_seconds}s", fill=(150, 150, 200), font=font)

            img.save(temp_img_path, "PNG")

            # Convert single image to a video of duration_seconds at 30fps
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", temp_img_path,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-t", str(duration_seconds),
                "-r", "30",
                output_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            try:
                os.remove(temp_img_path)
            except Exception:
                pass
        else:
            # Fallback to FFmpeg color filter source if Pillow is unavailable
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=0x0f172a:s=1920x1080:d={duration_seconds}:r=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output_path

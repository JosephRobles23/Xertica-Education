"""Playwright-based visual capture adapter for slides and walkthroughs.

How it works fundamentally:
    Playwright is a browser automation library. We use it in two distinct ways:

    1. SCREENSHOT MODE (slides):
       - We create a beautiful HTML page with CSS styling
       - We open it in a headless (invisible) Chrome browser
       - We take a screenshot → produces a PNG image
       - FFmpeg later turns this static image into a video by looping it

    2. VIDEO RECORDING MODE (walkthroughs + animated slides):
       - We create an HTML page (or navigate to a URL)
       - We tell Playwright to record the browser window as video
       - CSS animations play out while the recording runs
       - We stop after the narration duration → produces a WebM video file

    The animated slide capture is what transforms the videos from boring static
    screenshots into dynamic, engaging content. Bullets fade in one by one,
    titles animate, and the background has subtle motion — all via pure CSS
    animations timed to match the narration duration.

    In mock mode (Playwright not installed), we write placeholder files.
"""

import os
import asyncio
import math
from typing import List, Optional

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class PlaywrightCaptureAdapter:
    def __init__(self):
        self.is_mock = not PLAYWRIGHT_AVAILABLE
        if self.is_mock:
            print("Playwright SDK not found. PlaywrightCaptureAdapter running in MOCK mode.")

    # ──────────────────────────────────────────────────────────────────
    # 1. STATIC SLIDE — Screenshot capture (PNG)
    # ──────────────────────────────────────────────────────────────────

    async def capture_slide(self, title: str, bullets: List[str], output_path: str):
        """Render a static slide as an HTML page and capture a PNG screenshot.

        This is the simplest visual type: title + bullet points on a dark
        gradient background with glassmorphic styling. The resulting PNG gets
        looped by FFmpeg to match the audio duration.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.is_mock:
            self._write_mock_png(output_path)
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})

            html_content = self._build_static_slide_html(title, bullets)
            await page.set_content(html_content)
            # Wait for fonts to load before taking the screenshot.
            await page.wait_for_timeout(500)
            await page.screenshot(path=output_path)
            await browser.close()

    # ──────────────────────────────────────────────────────────────────
    # 2. ANIMATED SLIDE — Video recording with CSS animations
    # ──────────────────────────────────────────────────────────────────

    async def capture_animated_slide(
        self,
        title: str,
        bullets: List[str],
        duration: float,
        output_path: str,
    ):
        """Render an animated slide as video: bullets appear one-by-one.

        How this works:
        - We create an HTML page where each bullet has a CSS animation that
          makes it fade-in + slide-up after a staggered delay.
        - We open the page in Playwright with VIDEO RECORDING enabled.
        - We wait for the exact audio duration (so the video matches the narration).
        - Playwright saves the recording as a WebM file.
        - We rename/move it to the output_path.

        The animation timing is calculated from the narration duration:
        - Title appears immediately (0.3s fade-in)
        - Each bullet gets an equal slice of the remaining time
        - There's a small overlap so it feels natural, not robotic
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.is_mock:
            self._write_mock_mp4(output_path)
            return

        temp_video_dir = f"/tmp/playwright_animated_{id(self)}"
        os.makedirs(temp_video_dir, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                record_video_dir=temp_video_dir,
                record_video_size={"width": 1920, "height": 1080},
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            html_content = self._build_animated_slide_html(title, bullets, duration)
            await page.set_content(html_content)

            # Record for the exact duration of the narration audio.
            # Add 0.5s buffer to ensure all animations complete.
            await asyncio.sleep(duration + 0.5)

            # Closing the context finalizes the video file.
            video_path = await page.video.path()
            await context.close()
            await browser.close()

        # Move the recorded video to the desired output path.
        if os.path.exists(video_path):
            os.rename(video_path, output_path)
        else:
            # Fallback: find the most recent video in the temp directory.
            self._move_latest_video(temp_video_dir, output_path)

        # Clean up temp directory.
        self._cleanup_dir(temp_video_dir)

    # ──────────────────────────────────────────────────────────────────
    # 3. ILLUSTRATED SLIDE — AI image background + text overlay (video)
    # ──────────────────────────────────────────────────────────────────

    async def capture_illustrated_slide(
        self,
        title: str,
        bullets: List[str],
        background_image_path: str,
        duration: float,
        output_path: str,
    ):
        """Render a slide with an AI-generated illustration as background.

        This creates a "keynote-quality" visual by:
        1. Using the Imagen 3-generated illustration as a full-bleed background
        2. Overlaying a frosted-glass panel with the text content
        3. Animating the text reveals with staggered CSS animations
        4. Recording the whole thing as a video

        The result looks like a premium presentation, not a generic bullet list.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.is_mock:
            self._write_mock_mp4(output_path)
            return

        temp_video_dir = f"/tmp/playwright_illustrated_{id(self)}"
        os.makedirs(temp_video_dir, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                record_video_dir=temp_video_dir,
                record_video_size={"width": 1920, "height": 1080},
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            html_content = self._build_illustrated_slide_html(
                title, bullets, background_image_path, duration
            )
            await page.set_content(html_content)
            await asyncio.sleep(duration + 0.5)

            video_path = await page.video.path()
            await context.close()
            await browser.close()

        if os.path.exists(video_path):
            os.rename(video_path, output_path)
        else:
            self._move_latest_video(temp_video_dir, output_path)

        self._cleanup_dir(temp_video_dir)

    # ──────────────────────────────────────────────────────────────────
    # 4. WALKTHROUGH — Live browser screen recording
    # ──────────────────────────────────────────────────────────────────

    async def capture_walkthrough(self, url: str, duration: float, output_path: str):
        """Launch browser, navigate to a URL, and record the screen.

        This captures a real web page (e.g., a cloud dashboard, a documentation
        site) as it would appear to a user. The recording runs for exactly the
        narration duration.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.is_mock:
            self._write_mock_mp4(output_path)
            return

        temp_video_dir = "/tmp/playwright_videos"
        os.makedirs(temp_video_dir, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                record_video_dir=temp_video_dir,
                record_video_size={"width": 1920, "height": 1080},
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception as e:
                print(f"Playwright navigation timed out for {url}, recording blank page: {e}")

            # Simulate smooth human-like scrolling down the page during recording
            elapsed = 0.0
            step_time = 0.5
            scroll_y = 0
            initial_wait = min(1.5, duration)
            await asyncio.sleep(initial_wait)
            elapsed += initial_wait
            while elapsed < duration:
                scroll_y += 150
                try:
                    await page.evaluate(f"window.scrollTo({{ top: {scroll_y}, behavior: 'smooth' }});")
                except Exception:
                    pass
                sleep_time = min(step_time, duration - elapsed)
                await asyncio.sleep(sleep_time)
                elapsed += sleep_time

            # Close browser context to finalize the video file.
            await context.close()
            await browser.close()

        self._move_latest_video(temp_video_dir, output_path)
        self._cleanup_dir(temp_video_dir)

    # ──────────────────────────────────────────────────────────────────
    # 5. SCREENSHOT — Deterministic full-page screenshot capture (PNG)
    # ──────────────────────────────────────────────────────────────────

    async def capture_screenshot(
        self,
        url: str,
        output_path: str,
        wait_for_selector: str | None = None,
        full_page: bool = True,
    ) -> str:
        """Capture a deterministic screenshot of a specific URL.

        No interaction, no clicking, no scrolling — just a clean full-page screenshot.
        Returns the output path.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.is_mock:
            self._write_placeholder_screenshot(url, output_path)
            return output_path

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})

            try:
                await page.goto(url, wait_until="load", timeout=15000)
            except Exception as e:
                print(f"Playwright navigation failed for {url}: {e}")
                await browser.close()
                self._write_placeholder_screenshot(url, output_path)
                return output_path

            try:
                if wait_for_selector:
                    await page.wait_for_selector(wait_for_selector, timeout=15000)
                else:
                    await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"Playwright wait condition failed for {url}: {e}")

            try:
                await page.screenshot(path=output_path, full_page=full_page)
            except Exception as e:
                print(f"Playwright screenshot failed for {url}: {e}")
                self._write_placeholder_screenshot(url, output_path)

            await browser.close()

        return output_path

    # ══════════════════════════════════════════════════════════════════
    # HTML TEMPLATES
    # ══════════════════════════════════════════════════════════════════

    def _build_static_slide_html(self, title: str, bullets: List[str]) -> str:
        """Build the HTML for a static slide (screenshot capture).

        Design language:
        - Dark gradient background (navy → purple)
        - Glassmorphic container with blur + translucent border
        - Gradient title text (blue → purple)
        - Subtle Xertica Education branding in corner
        """
        valid_bullets = [str(b).strip() for b in bullets if b and str(b).strip()]
        bullets_html = "".join([f"<li>{b}</li>" for b in valid_bullets])
        return f"""<!DOCTYPE html>
<html>
<head>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            width: 1920px; height: 1080px;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            color: #f8fafc;
            font-family: 'Inter', system-ui, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}
        /* Decorative background orbs for visual depth */
        .orb {{
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.15;
        }}
        .orb-1 {{ width: 600px; height: 600px; background: #3b82f6; top: -200px; left: -100px; }}
        .orb-2 {{ width: 400px; height: 400px; background: #8b5cf6; bottom: -100px; right: -50px; }}
        .orb-3 {{ width: 300px; height: 300px; background: #06b6d4; bottom: 100px; left: 300px; }}
        .container {{
            position: relative;
            z-index: 1;
            max-width: 1500px;
            backdrop-filter: blur(16px);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 32px;
            padding: 70px 90px;
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.5),
                        inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }}
        h1 {{
            font-size: 64px;
            font-weight: 800;
            margin-bottom: 48px;
            background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.15;
            letter-spacing: -0.02em;
        }}
        ul {{
            font-size: 34px;
            line-height: 1.7;
            padding-left: 36px;
            color: #cbd5e1;
        }}
        li {{
            margin-bottom: 20px;
            padding-left: 12px;
        }}
        li::marker {{
            color: #60a5fa;
        }}
        .footer {{
            position: absolute;
            bottom: 40px;
            right: 60px;
            font-size: 20px;
            color: #475569;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
    </style>
</head>
<body>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="container">
        <h1>{title}</h1>
        <ul>{bullets_html}</ul>
    </div>
    <div class="footer">Xertica Education</div>
</body>
</html>"""

    def _build_animated_slide_html(
        self, title: str, bullets: List[str], duration: float
    ) -> str:
        """Build HTML with CSS animations for video recording.

        Animation timeline:
        - 0.0s → 0.8s:  Title fades in + slides down
        - 0.8s → end:   Each bullet fades in sequentially
        - Continuous:    Background orbs slowly drift (subtle motion)

        The delay between bullets is calculated by dividing the remaining time
        (after the title animation) equally among all bullets. This ensures
        the reveals feel paced to the narration speed.
        """
        num_bullets = max(len(bullets), 1)
        # Time allocated for bullet animations (leave 0.8s for title + 1s buffer at end)
        bullet_window = max(duration - 1.8, num_bullets * 0.5)
        delay_per_bullet = bullet_window / num_bullets

        valid_bullets = [str(b).strip() for b in bullets if b and str(b).strip()]
        bullets_html = ""
        for i, bullet in enumerate(valid_bullets):
            delay = 0.8 + (i * delay_per_bullet)
            bullets_html += f'<li style="animation-delay: {delay:.2f}s">{bullet}</li>\n'

        return f"""<!DOCTYPE html>
<html>
<head>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            width: 1920px; height: 1080px;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            color: #f8fafc;
            font-family: 'Inter', system-ui, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}

        /* ─── Animated background orbs ─── */
        .orb {{
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0;
            animation: orb-appear 2s ease-out forwards, orb-drift {duration}s ease-in-out infinite;
        }}
        .orb-1 {{
            width: 600px; height: 600px;
            background: radial-gradient(circle, #3b82f6, transparent 70%);
            top: -200px; left: -100px;
            animation-delay: 0s;
        }}
        .orb-2 {{
            width: 450px; height: 450px;
            background: radial-gradient(circle, #8b5cf6, transparent 70%);
            bottom: -100px; right: -50px;
            animation-delay: 0.3s;
        }}
        .orb-3 {{
            width: 350px; height: 350px;
            background: radial-gradient(circle, #06b6d4, transparent 70%);
            bottom: 100px; left: 300px;
            animation-delay: 0.6s;
        }}

        @keyframes orb-appear {{
            from {{ opacity: 0; transform: scale(0.8); }}
            to   {{ opacity: 0.2; transform: scale(1); }}
        }}
        @keyframes orb-drift {{
            0%, 100% {{ transform: translate(0, 0); }}
            33%      {{ transform: translate(30px, -20px); }}
            66%      {{ transform: translate(-20px, 15px); }}
        }}

        /* ─── Content container ─── */
        .container {{
            position: relative;
            z-index: 1;
            max-width: 1500px;
            backdrop-filter: blur(16px);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 32px;
            padding: 70px 90px;
            box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.5),
                        inset 0 1px 0 rgba(255, 255, 255, 0.05);
            opacity: 0;
            animation: container-appear 0.6s ease-out 0.1s forwards;
        }}
        @keyframes container-appear {{
            from {{ opacity: 0; transform: translateY(30px) scale(0.98); }}
            to   {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}

        /* ─── Title ─── */
        h1 {{
            font-size: 64px;
            font-weight: 800;
            margin-bottom: 48px;
            background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-size: 200% 200%;
            line-height: 1.15;
            letter-spacing: -0.02em;
            opacity: 0;
            animation: title-appear 0.8s ease-out 0.3s forwards,
                       gradient-shift {duration}s ease-in-out infinite;
        }}
        @keyframes title-appear {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes gradient-shift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50%      {{ background-position: 100% 50%; }}
        }}

        /* ─── Bullet list ─── */
        ul {{
            font-size: 34px;
            line-height: 1.7;
            padding-left: 36px;
            color: #cbd5e1;
            list-style: none;
        }}
        li {{
            margin-bottom: 24px;
            padding-left: 20px;
            position: relative;
            opacity: 0;
            transform: translateX(-20px);
            animation: bullet-appear 0.6s ease-out forwards;
        }}
        li::before {{
            content: "→";
            position: absolute;
            left: -20px;
            color: #60a5fa;
            font-weight: 600;
        }}
        @keyframes bullet-appear {{
            from {{ opacity: 0; transform: translateX(-20px); }}
            to   {{ opacity: 1; transform: translateX(0); }}
        }}

        /* ─── Bottom bar ─── */
        .progress-bar {{
            position: absolute;
            bottom: 0; left: 0;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6, #c084fc);
            width: 0%;
            animation: progress {duration}s linear forwards;
            border-radius: 0 2px 0 0;
        }}
        @keyframes progress {{
            from {{ width: 0%; }}
            to   {{ width: 100%; }}
        }}

        .footer {{
            position: absolute;
            bottom: 24px; right: 60px;
            font-size: 18px;
            color: #475569;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            opacity: 0;
            animation: fade-in 0.5s ease-out 1s forwards;
        }}
        @keyframes fade-in {{
            from {{ opacity: 0; }}
            to   {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <div class="container">
        <h1>{title}</h1>
        <ul>
            {bullets_html}
        </ul>
    </div>
    <div class="progress-bar"></div>
    <div class="footer">Xertica Education</div>
</body>
</html>"""

    def _build_illustrated_slide_html(
        self,
        title: str,
        bullets: List[str],
        background_image_path: str,
        duration: float,
    ) -> str:
        """Build HTML that composites text over an AI-generated illustration.

        Design approach:
        - Full-bleed background image (the Imagen 3 illustration)
        - Subtle Ken Burns zoom effect via CSS animation on the image
        - Frosted-glass overlay panel with text content
        - Staggered text reveal animations

        This creates the "premium keynote" feel where the AI illustration
        serves as rich visual context while the narration explains the concept.
        """
        num_bullets = max(len(bullets), 1)
        bullet_window = max(duration - 1.8, num_bullets * 0.5)
        delay_per_bullet = bullet_window / num_bullets

        bullets_html = ""
        for i, bullet in enumerate(bullets):
            delay = 1.0 + (i * delay_per_bullet)
            bullets_html += f'<li style="animation-delay: {delay:.2f}s">{bullet}</li>\n'

        # Convert local file path to a file:// URL for the browser.
        bg_url = f"file://{background_image_path}"

        return f"""<!DOCTYPE html>
<html>
<head>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            width: 1920px; height: 1080px;
            overflow: hidden;
            font-family: 'Inter', system-ui, sans-serif;
            color: #f8fafc;
        }}

        /* ─── Background image with Ken Burns zoom ─── */
        .bg-image {{
            position: absolute;
            top: -5%; left: -5%;
            width: 110%; height: 110%;
            background-image: url('{bg_url}');
            background-size: cover;
            background-position: center;
            animation: ken-burns {duration}s ease-in-out forwards;
            z-index: 0;
        }}
        @keyframes ken-burns {{
            from {{ transform: scale(1.0) translate(0, 0); }}
            to   {{ transform: scale(1.08) translate(-1%, -1%); }}
        }}

        /* Dark overlay to ensure text readability */
        .overlay {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: linear-gradient(
                135deg,
                rgba(15, 23, 42, 0.85) 0%,
                rgba(30, 27, 75, 0.7) 50%,
                rgba(15, 23, 42, 0.85) 100%
            );
            z-index: 1;
        }}

        /* ─── Content panel ─── */
        .panel {{
            position: absolute;
            z-index: 2;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            max-width: 1400px;
            width: 85%;
            backdrop-filter: blur(20px);
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 32px;
            padding: 64px 80px;
            box-shadow: 0 30px 70px -15px rgba(0, 0, 0, 0.6);
            opacity: 0;
            animation: panel-appear 0.8s ease-out 0.2s forwards;
        }}
        @keyframes panel-appear {{
            from {{ opacity: 0; transform: translate(-50%, -48%) scale(0.96); }}
            to   {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
        }}

        h1 {{
            font-size: 58px;
            font-weight: 800;
            margin-bottom: 40px;
            background: linear-gradient(135deg, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.15;
            opacity: 0;
            animation: title-in 0.6s ease-out 0.5s forwards;
        }}
        @keyframes title-in {{
            from {{ opacity: 0; transform: translateY(-15px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        ul {{
            font-size: 32px;
            line-height: 1.7;
            padding-left: 0;
            list-style: none;
        }}
        li {{
            margin-bottom: 20px;
            padding-left: 30px;
            position: relative;
            color: #e2e8f0;
            opacity: 0;
            animation: bullet-in 0.5s ease-out forwards;
        }}
        li::before {{
            content: "◆";
            position: absolute;
            left: 0;
            color: #818cf8;
            font-size: 16px;
            top: 8px;
        }}
        @keyframes bullet-in {{
            from {{ opacity: 0; transform: translateX(-15px); }}
            to   {{ opacity: 1; transform: translateX(0); }}
        }}

        .footer {{
            position: absolute;
            bottom: 24px; right: 60px;
            font-size: 18px;
            color: rgba(255, 255, 255, 0.3);
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            z-index: 3;
        }}
    </style>
</head>
<body>
    <div class="bg-image"></div>
    <div class="overlay"></div>
    <div class="panel">
        <h1>{title}</h1>
        <ul>
            {bullets_html}
        </ul>
    </div>
    <div class="footer">Xertica Education</div>
</body>
</html>"""

    # ══════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _move_latest_video(self, source_dir: str, output_path: str):
        """Find and move the most recently recorded video from a directory."""
        try:
            video_files = [
                os.path.join(source_dir, f)
                for f in os.listdir(source_dir)
                if f.endswith((".webm", ".mp4"))
            ]
            if video_files:
                latest = max(video_files, key=os.path.getmtime)
                os.rename(latest, output_path)
            else:
                # No video file was created — write a placeholder.
                self._write_mock_mp4(output_path)
        except Exception as e:
            print(f"Error moving video file: {e}")
            self._write_mock_mp4(output_path)

    def _cleanup_dir(self, dir_path: str):
        """Remove leftover files from a temp directory."""
        try:
            for f in os.listdir(dir_path):
                try:
                    os.remove(os.path.join(dir_path, f))
                except Exception:
                    pass
            os.rmdir(dir_path)
        except Exception:
            pass

    def _write_mock_png(self, output_path: str):
        """Write a minimal valid PNG file (1×1 pixel, RGBA)."""
        dummy_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
            b'\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        with open(output_path, "wb") as f:
            f.write(dummy_png)

    def _write_placeholder_screenshot(self, url: str, output_path: str):
        """Generate a dark navy placeholder image with the URL text overlaid.

        Uses PIL if available, otherwise falls back to a minimal valid PNG.
        """
        if not PIL_AVAILABLE:
            self._write_mock_png(output_path)
            return

        img = Image.new("RGB", (1920, 1080), "#0f172a")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        except Exception:
            font = ImageFont.load_default()

        display_url = url if len(url) <= 100 else url[:97] + "..."
        text_bbox = draw.textbbox((0, 0), display_url, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        x = (1920 - text_w) // 2
        y = (1080 - text_h) // 2

        draw.text((x, y), display_url, fill="#475569", font=font)
        img.save(output_path, format="PNG")

    def _write_mock_mp4(self, output_path: str):
        """Write a minimal valid MP4 header."""
        dummy_mp4 = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom'
        with open(output_path, "wb") as f:
            f.write(dummy_mp4)

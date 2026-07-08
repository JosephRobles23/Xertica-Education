"""Google Imagen 3 adapter for generating educational illustrations and diagrams.

How it works fundamentally:
    Imagen 3 is Google's image generation model. You send it a text description
    (prompt) and it returns raw image bytes — like asking an artist to paint
    exactly what you describe.

    The API call is synchronous (unlike Veo which is async/long-running) because
    generating a single image takes only a few seconds. We use the google-genai
    SDK which talks to Vertex AI under the hood.

    In mock mode (no credentials), we use Pillow to generate a gradient
    placeholder image so the pipeline doesn't break.
"""

import os
from typing import Optional

from config.settings import settings

# Try to import the Google GenAI SDK. If missing, adapter runs in mock mode.
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Try to import Pillow for mock image generation.
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


class GoogleImagenAdapter:
    """Generates educational illustrations using Google Imagen 3 via Vertex AI.

    The adapter has two modes:
      - REAL: Calls the Imagen 3 API to generate a 1920×1080 PNG from a prompt.
      - MOCK: Creates a gradient placeholder PNG with the prompt text overlaid,
              so the pipeline can run end-to-end without API credentials.
    """

    def __init__(self):
        # Determine if we can make real API calls.
        # We need: (1) the SDK installed, (2) a real GCP project configured,
        # and (3) valid application credentials in the environment.
        self.is_mock = (
            not GENAI_AVAILABLE
            or "placeholder" in settings.google_cloud_project
            or not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )

        self._client = None
        if not self.is_mock:
            try:
                # Initialize the GenAI client pointed at Vertex AI.
                # vertexai=True tells the SDK to route through Vertex AI
                # (Google Cloud's ML platform) rather than the consumer
                # Gemini API endpoint.
                self._client = genai.Client(
                    vertexai=True,
                    project=settings.google_cloud_project,
                    location=settings.google_cloud_location,
                )
            except Exception as e:
                print(f"Failed to initialize GenAI client for Imagen: {e}")
                self.is_mock = True

        if self.is_mock:
            print("Google Imagen 3 credentials not found. GoogleImagenAdapter running in MOCK mode.")

    async def generate_illustration(
        self,
        prompt: str,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Generate an educational illustration and save it as a PNG file.

        Args:
            prompt: A detailed text description of the image to generate.
                    For best results with educational content, include:
                    - The subject matter (e.g., "client-server architecture")
                    - The visual style (e.g., "clean technical diagram")
                    - Color scheme (e.g., "dark background, blue and purple")
                    - Aspect ratio context (e.g., "16:9, wide format")
            output_path: Where to save the resulting PNG file.
            width: Image width in pixels (default 1920 for 1080p video).
            height: Image height in pixels (default 1080 for 1080p video).

        Returns:
            The output_path where the image was saved.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self.is_mock:
            return self._generate_mock_image(prompt, output_path, width, height)

        try:
            if "gemini-" in settings.imagen_model:
                # Call Gemini-based native image generation model (e.g. gemini-2.5-flash-image)
                response = self._client.models.generate_content(
                    model=settings.imagen_model,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    )
                )
                image_bytes = None
                if response.candidates:
                    for candidate in response.candidates:
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, "inline_data") and part.inline_data:
                                    image_bytes = part.inline_data.data
                                    break
                if image_bytes:
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    return output_path
                else:
                    print("Gemini image generation returned no image data. Falling back to mock.")
                    return self._generate_mock_image(prompt, output_path, width, height)
            else:
                # Call the legacy Imagen 3 API.
                response = self._client.models.generate_images(
                    model=settings.imagen_model,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/png",
                    ),
                )

                if response.generated_images:
                    image_bytes = response.generated_images[0].image.image_bytes
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    return output_path
                else:
                    print("Imagen 3 returned no images. Falling back to mock.")
                    return self._generate_mock_image(prompt, output_path, width, height)

        except Exception as e:
            print(f"Imagen 3 API error: {e}. Falling back to mock.")
            return self._generate_mock_image(prompt, output_path, width, height)

    def _generate_mock_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Create a gradient placeholder PNG with the prompt text overlaid.

        This exists so the entire video pipeline can run end-to-end without
        real API credentials. The gradient makes it visually distinguishable
        from a broken/blank frame.
        """
        if PILLOW_AVAILABLE:
            # Create a gradient image (dark blue → purple, matching the slide
            # design language from playwright_capture.py).
            img = Image.new("RGB", (width, height))
            draw = ImageDraw.Draw(img)

            for y in range(height):
                # Linear interpolation between two colors across the height.
                # Start color: #0f172a (dark navy)  → End color: #1e1b4b (dark purple)
                ratio = y / height
                r = int(15 + (30 - 15) * ratio)    # 0f → 1e
                g = int(23 + (27 - 23) * ratio)    # 17 → 1b
                b = int(42 + (75 - 42) * ratio)    # 2a → 4b
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Overlay the prompt text so developers can see what would be generated.
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
            except Exception:
                font = ImageFont.load_default()

            # Word-wrap the prompt to fit on screen.
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

            # Draw text centered vertically with a translucent background.
            y_start = height // 2 - len(lines) * 20
            for i, line in enumerate(lines):
                text_y = y_start + i * 40
                # Semi-transparent background strip.
                draw.rectangle(
                    [60, text_y - 5, width - 60, text_y + 35],
                    fill=(0, 0, 0, 128) if img.mode == "RGBA" else (20, 20, 40),
                )
                draw.text((80, text_y), line, fill=(200, 200, 255), font=font)

            # "MOCK" watermark in the corner.
            draw.text((width - 200, height - 50), "[MOCK IMAGE]", fill=(100, 100, 150), font=font)

            img.save(output_path, "PNG")
        else:
            # If even Pillow isn't available, write a minimal valid PNG.
            # This is the tiniest valid 1×1 PNG file (67 bytes).
            dummy_png = (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
                b'\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
                b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            with open(output_path, "wb") as f:
                f.write(dummy_png)

        return output_path

import os
import io
import base64
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Dict, Any, Literal

# Mapping of user-friendly aspect ratio names to OpenAI image sizes for gpt-image-2.
# gpt-image-2 supports flexible aspect ratios; these are the standard API sizes.
ASPECT_RATIO_SIZES: Dict[str, str] = {
    "vertical": "1024x1792",
    "horizontal": "1792x1024",
    "square": "1024x1024",
    "auto": "1024x1792",  # Default: vertical (best for infographics/print)
}

AspectRatio = Literal["vertical", "horizontal", "square", "auto"]
import httpx
from PIL import Image
from config.settings import settings
from .interface import InfographicServiceInterface
from supabase import create_client

def extract_grounded_points(sources: List[Dict[str, Any]], word_budget: int) -> List[str]:
    """
    Extracts text points from sources or modules up to a maximum word budget for prompt styling.
    """
    points = []
    current_word_count = 0
    if not sources:
        return ["Conceptos clave y fundamentos de la materia."]
        
    for src in sources:
        text_blocks = []
        if isinstance(src, dict):
            # Check if it's a module
            name = src.get("name") or src.get("title") or src.get("titulo")
            desc = src.get("description") or src.get("descripcion") or src.get("desc")
            if not desc and src.get("contents"):
                contents = src.get("contents")
                if isinstance(contents, list) and len(contents) > 0 and isinstance(contents[0], dict):
                    desc = contents[0].get("summary")
            
            # If it's a module structure, combine them as a single syllabus point
            if name and (desc or src.get("num")):
                if not desc:
                    desc = "Módulo de aprendizaje."
                combined = f"{name}: {desc}"
                text_blocks.append(combined)
            else:
                title = src.get("title") or src.get("titulo")
                quote = src.get("quote") or src.get("contenido") or src.get("summary")
                if title:
                    text_blocks.append(title)
                if quote:
                    text_blocks.append(quote)
        elif isinstance(src, str):
            text_blocks.append(src)
            
        for block in text_blocks:
            words = block.split()
            block_words_count = len(words)
            if current_word_count + block_words_count <= word_budget:
                points.append(block)
                current_word_count += block_words_count
            else:
                remaining = word_budget - current_word_count
                if remaining > 3:
                    points.append(" ".join(words[:remaining]) + "...")
                    current_word_count += remaining
                break
        if current_word_count >= word_budget:
            break
            
    if not points:
        points = ["Fundamentos y mejores prácticas del tema del curso."]
    return points

# Companies whose brand colors and logo gpt-image-2 can reliably infer
# (globally recognized brands). For anything not in this set, we use
# generic colors and explicitly forbid logo generation to avoid hallucination.
WELL_KNOWN_BRANDS = {
    "google", "microsoft", "amazon", "apple", "meta", "facebook",
    "netflix", "spotify", "uber", "airbnb", "tesla", "nvidia",
    "ibm", "oracle", "salesforce", "adobe", "samsung", "sony",
    "coca-cola", "coca cola", "pepsi", "nike", "adidas",
    "bancolombia", "bbva", "santander", "itaú", "itau",
    "mercado libre", "mercadolibre", "rappi", "nubank",
    "aws", "azure", "gcp", "google cloud",
    "xertica", "globant", "endava", "openai"
}

def _is_well_known(company_name: str) -> bool:
    """Returns True if the company is globally recognizable enough for the
    model to infer brand colors and logo without hallucinating."""
    return company_name.strip().lower() in WELL_KNOWN_BRANDS


def build_image_prompt(points: List[str], company_name: str, user_prompt: str | None = None) -> str:
    """
    Builds the target prompt for image generation.
    - Well-known companies: use their real brand colors + logo.
    - Unknown companies: use elegant generic colors and NO logo at all.
    """
    points_text = "\n".join([f"- {p}" for p in points])

    if _is_well_known(company_name):
        branding_block = (
            f"- Identidad Visual y Branding: Aplica la paleta de colores corporativos oficiales "
            f"y la estética visual de '{company_name}'. Integra su logotipo oficial en la cabecera o esquina.\n"
        )
    else:
        branding_block = (
            f"- Identidad Visual y Branding: El curso es para la empresa '{company_name}'. "
            f"NO inventes ni incluyas ningún logotipo ni texto de marcador de posición para logo. "
            f"Simplemente no pongas nada donde iría un logo. "
            f"Usa una paleta de colores profesional y genérica (violetas, azules oscuros o turquesas) "
            f"que se vea premium y corporativa.\n"
        )

    prompt = (
        f"Diseña una infografía educativa y corporativa limpia, profesional y moderna en español, "
        f"que sirva como el syllabus del curso.\n"
        f"El tema principal debe estar alineado con el siguiente contenido:\n"
        f"{points_text}\n\n"
        f"Requisitos de Estilo y Visualización:\n"
        f"{branding_block}"
        f"- Estilo visual: Fondo oscuro premium (dark mode con tonos negro o gris muy oscuro), "
        f"con acentos de color vibrantes y degradados elegantes.\n"
        f"- Estructura: Diseño estructurado en secciones/tarjetas limpias y ordenadas. "
        f"Cada sección o módulo del curso debe estar representado en una tarjeta con un número "
        f"grande (01, 02, 03, etc.) y un icono simple estilizado de estilo cristalino o neón 3D "
        f"(3D glassmorphism/neon icon).\n"
        f"- El estilo debe ser de diseño gráfico editorial vectorizado y moderno, "
        f"NO una fotografía, NO renders 3D realistas ni texturas complejas.\n"
        f"- Relación de aspecto vertical apta para impresión en una página.\n"
        f"- Asegúrate de que el texto en español sea nítido y legible.\n"
        f"- REGLA ESTRICTA: NO inventes logotipos. Si no conoces con certeza el logo real "
        f"de la empresa, NO incluyas ninguno. Es preferible dejar el espacio vacío."
    )

    if user_prompt:
        prompt += f"\n\nInstrucción adicional del usuario (prioridad alta): {user_prompt}"

    return prompt


def build_fallback_prompt(points: List[str], company_name: str, user_prompt: str | None = None) -> str:
    """
    Fallback prompt: never includes logo (for safety filter bypass), always
    uses generic colors for unknown brands and brand colors for known ones.
    """
    points_text = "\n".join([f"- {p}" for p in points])

    if _is_well_known(company_name):
        branding_block = (
            f"- Identidad Visual y Branding: Aplica la paleta de colores corporativos oficiales "
            f"de '{company_name}'. NO incluyas el logotipo para evitar filtros de propiedad de terceros.\n"
        )
    else:
        branding_block = (
            f"- Identidad Visual y Branding: El curso es para la empresa '{company_name}'. "
            f"NO inventes ni incluyas ningún logotipo, marca gráfica, ni texto como 'tu logo aquí'. "
            f"Usa una paleta de colores profesional y genérica (violetas, azules oscuros o turquesas).\n"
        )

    prompt = (
        f"Diseña una infografía educativa y corporativa limpia, profesional y moderna en español, "
        f"que sirva como el syllabus del curso.\n"
        f"El tema principal debe estar alineado con el siguiente contenido:\n"
        f"{points_text}\n\n"
        f"Requisitos de Estilo y Visualización:\n"
        f"{branding_block}"
        f"- Estilo visual: Fondo oscuro premium (dark mode con tonos negro o gris muy oscuro), "
        f"con acentos de color vibrantes y degradados elegantes.\n"
        f"- Estructura: Diseño estructurado en secciones/tarjetas limpias y ordenadas. "
        f"Cada sección o módulo del curso debe estar representado en una tarjeta con un número "
        f"grande (01, 02, 03, etc.) y un icono simple estilizado de estilo cristalino o neón 3D "
        f"(3D glassmorphism/neon icon).\n"
        f"- El estilo debe ser de diseño gráfico editorial vectorizado y moderno, "
        f"NO una fotografía, NO renders 3D realistas ni texturas complejas.\n"
        f"- Relación de aspecto vertical apta para impresión en una página.\n"
        f"- Asegúrate de que el texto en español sea nítido y legible.\n"
        f"- REGLA ESTRICTA: NO inventes logotipos de ninguna empresa."
    )

    if user_prompt:
        prompt += f"\n\nInstrucción adicional del usuario (prioridad alta): {user_prompt}"

    return prompt

class InfographicService(InfographicServiceInterface):
    def __init__(self):
        self._supabase = None
        self._fallback_assets: Dict[UUID, Dict[str, Any]] = {}
        
        url = settings.supabase_url
        key = settings.supabase_key
        if url and "placeholder" not in url and key and "placeholder" not in key:
            try:
                self._supabase = create_client(url, key)
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client in InfographicService: {e}")

    async def generate_infographic(
        self,
        component_id: UUID,
        sources: List[Dict[str, Any]],
        company_name: str,
        word_budget: int,
        user_prompt: str | None = None,
        aspect_ratio: AspectRatio = "auto"
    ) -> Dict[str, Any]:
        """
        Main infographic generation method. Calls OpenAI Images API (gpt-image-2),
        compiles PDF wrapper using Pillow, uploads to storage, and registers assets in DB.
        """
        # Step 1: Extract key content
        points = extract_grounded_points(sources, word_budget)
        
        # Step 2: Build main prompt
        prompt = build_image_prompt(points, company_name, user_prompt)
        
        png_bytes = None
        prompt_used = prompt
        requires_manual_review = False
        
        # Step 3: API Call with Fallback and Retry
        openai_key = settings.openai_api_key
        
        if not openai_key or "placeholder" in openai_key:
            raise ValueError("La clave de API de OpenAI (OPENAI_API_KEY) no está configurada o es inválida.")
            
        # Resolve the image size from the aspect ratio parameter
        image_size = ASPECT_RATIO_SIZES.get(aspect_ratio, ASPECT_RATIO_SIZES["auto"])
        
        # Real API call — timeout raised to 300s because gpt-image-2 can take 2+ min
        # for high-resolution images.
        async def attempt_call(target_prompt: str) -> bytes:
            async with httpx.AsyncClient(timeout=300.0) as client:
                headers = {
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "gpt-image-2",
                    "prompt": target_prompt,
                    "n": 1,
                    "size": image_size
                }
                # Making request to OpenAI Images endpoint
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    image_data = data["data"][0]
                    if "b64_json" in image_data:
                        return base64.b64decode(image_data["b64_json"])
                    elif "url" in image_data:
                        img_url = image_data["url"]
                        img_response = await client.get(img_url)
                        if img_response.status_code == 200:
                            return img_response.content
                        else:
                            raise httpx.HTTPStatusError(
                                message=f"Failed to download image from OpenAI URL: {img_url}",
                                request=img_response.request,
                                response=img_response
                            )
                    else:
                        raise ValueError("No b64_json or url found in OpenAI Image API response.")
                else:
                    # Log error details
                    err_text = response.text
                    print(f"OpenAI Image API returned status {response.status_code}: {err_text}")
                    # Raise specific exception to trigger fallback/retry logic
                    raise httpx.HTTPStatusError(
                        message=err_text,
                        request=response.request,
                        response=response
                    )

        try:
            png_bytes = await attempt_call(prompt)
        except Exception as e:
            # Check if it was a safety/policy violation error
            error_msg = str(e).lower()
            is_policy_violation = (
                "safety" in error_msg or 
                "policy" in error_msg or 
                "violation" in error_msg or 
                "content_policy" in error_msg or
                (isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 400)
            )
            
            if is_policy_violation:
                print("OpenAI Image generation blocked by safety filters (likely due to brand logo). Trying fallback prompt...")
                fallback_prompt = build_fallback_prompt(points, company_name, user_prompt)
                prompt_used = fallback_prompt
                try:
                    png_bytes = await attempt_call(fallback_prompt)
                    requires_manual_review = True # Flag indicating logo was skipped
                except Exception as fallback_err:
                    print(f"Fallback generation also failed: {fallback_err}")
                    raise fallback_err
            else:
                raise e

        # Step 4: Wrap PNG in PDF using Pillow
        pdf_bytes = None
        try:
            image = Image.open(io.BytesIO(png_bytes))
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            pdf_io = io.BytesIO()
            image.save(pdf_io, "PDF", resolution=100.0)
            pdf_bytes = pdf_io.getvalue()
        except Exception as e:
            print(f"Error compiling PDF from PNG: {e}")
            raise e

        # Step 5: Save locally and to Supabase if available
        png_path = f"infographics/{component_id}_infographic.png"
        pdf_path = f"infographics/{component_id}_infographic.pdf"
        
        # Always write locally first so we have them served locally by FastAPI
        local_dir = os.path.join(os.getcwd(), "static", "infographics")
        os.makedirs(local_dir, exist_ok=True)
        local_png_filepath = os.path.join(local_dir, f"{component_id}_infographic.png")
        local_pdf_filepath = os.path.join(local_dir, f"{component_id}_infographic.pdf")
        
        with open(local_png_filepath, "wb") as f:
            f.write(png_bytes)
        with open(local_pdf_filepath, "wb") as f:
            f.write(pdf_bytes)

        # Storage & Database uploads
        png_asset_id = uuid4()
        pdf_asset_id = uuid4()
        
        generated_at = datetime.now(timezone.utc)
        
        provenance = {
            "prompt_used": prompt_used,
            "model": "gpt-image-2",
            "company_name": company_name,
            "word_budget": word_budget,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "generated_at": generated_at.isoformat(),
            "requires_manual_review": requires_manual_review
        }

        if self._supabase and "placeholder" not in settings.supabase_url:
            try:
                # Upload PNG
                self._supabase.storage.from_(settings.storage_bucket).upload(
                    path=png_path,
                    file=png_bytes,
                    file_options={"content-type": "image/png", "x-upsert": "true"}
                )
                # Upload PDF
                self._supabase.storage.from_(settings.storage_bucket).upload(
                    path=pdf_path,
                    file=pdf_bytes,
                    file_options={"content-type": "application/pdf", "x-upsert": "true"}
                )
                
                # Insert asset entries
                self._supabase.table("assets").insert({
                    "id": str(png_asset_id),
                    "componente_id": str(component_id),
                    "tipo": "infografia",
                    "estado": "generado",
                    "storage_path": png_path,
                    "word_budget": word_budget,
                    "provenance": provenance
                }).execute()
                
                self._supabase.table("assets").insert({
                    "id": str(pdf_asset_id),
                    "componente_id": str(component_id),
                    "tipo": "infografia",
                    "estado": "generado",
                    "storage_path": pdf_path,
                    "word_budget": word_budget,
                    "provenance": provenance
                }).execute()
                
            except Exception as e:
                print(f"Error persisting assets in Supabase (falling back to memory): {e}")

        # Track in fallback memory store
        result = {
            "png_asset_id": png_asset_id,
            "pdf_asset_id": pdf_asset_id,
            "prompt_used": prompt_used,
            "model": "gpt-image-2",
            "company_name": company_name,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "generated_at": generated_at,
            "local_png_url": f"http://localhost:8000/static/infographics/{component_id}_infographic.png",
            "local_pdf_url": f"http://localhost:8000/static/infographics/{component_id}_infographic.pdf",
            "requires_manual_review": requires_manual_review
        }
        self._fallback_assets[component_id] = result
        
        return result

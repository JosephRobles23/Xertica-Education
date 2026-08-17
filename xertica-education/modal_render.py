"""Función Modal del pipeline de render (Opción B / staging).

Corre TODO el trabajo pesado (TTS, Veo/Imagen, screenshots, Remotion, ffmpeg)
en un contenedor serverless con N cores. El API en Cloud Run lo dispara con
``Function.spawn(job_id, ...)`` (fire-and-forget); el estado y el video final
van a Supabase, así que el cliente sigue haciendo polling a ``GET /jobs/{id}``.

Layout esperado dentro de la imagen (para que ``config/settings.py`` calcule
bien ``remotion_composer_path``, que sube 4 niveles desde el archivo):

    /app/apps/api/...              <- código del backend (PYTHONPATH)
    /app/openmontage/remotion-composer/...  <- proyecto Remotion (con npm install)

Deploy:  cd xertica-education && modal deploy modal_render.py
"""

import os
import modal

# Nombre de la app y recursos son parametrizables por entorno para que el mismo
# archivo sirva en staging y (más adelante) en prod, y para subir a cpu=8 sin
# tocar código. El workflow los inyecta.
RENDER_APP = os.environ.get("MODAL_RENDER_APP", "xertica-render-staging")
RENDER_CPU = float(os.environ.get("MODAL_RENDER_CPU", "4"))
RENDER_MEMORY = int(os.environ.get("MODAL_RENDER_MEMORY", "8192"))

app = modal.App(RENDER_APP)

# Imagen pesada: Python + Node 20 (Remotion) + ffmpeg + Chromium (Playwright).
# Se construye una sola vez y Modal la cachea; el cold start posterior es de
# segundos, despreciable frente a un render de ~10 min.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "curl", "ca-certificates", "gnupg")
    # Node 20 vía NodeSource (Remotion necesita Node moderno).
    .run_commands(
        "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
        "apt-get install -y nodejs",
    )
    # Deps de Python del backend (solo [project.dependencies]).
    .pip_install_from_pyproject("apps/api/pyproject.toml")
    # Chromium headless para los screenshot_scene (Playwright). Remotion trae su
    # propio Chromium aparte.
    .run_commands("python -m playwright install --with-deps chromium")
    # Código de la app y del composer, en el layout que espera settings.py.
    .add_local_dir(
        "apps/api",
        "/app/apps/api",
        copy=True,
        ignore=["**/__pycache__", "**/*.pyc", "**/.env", "**/.venv", "**/tests"],
    )
    .add_local_dir(
        "openmontage",
        "/app/openmontage",
        copy=True,
        ignore=["**/node_modules", "**/out", "**/public"],
    )
    # Instala las deps del composer Remotion dentro de la imagen.
    .run_commands("cd /app/openmontage/remotion-composer && npm install")
    .env(
        {
            "PYTHONPATH": "/app/apps/api",
            "REMOTION_COMPOSER_PATH": "/app/openmontage/remotion-composer",
        }
    )
)

# Todos los secretos de runtime (Supabase, OpenRouter, Vertex/Veo/Imagen,
# Pixabay, etc.) viajan en un único Modal Secret. Ver SETUP.md.
secrets = [modal.Secret.from_name("xertica-secrets-staging")]


@app.function(
    image=image,
    cpu=RENDER_CPU,
    memory=RENDER_MEMORY,
    timeout=1800,  # 30 min de margen para un render de ~10 min
    secrets=secrets,
)
def render_video(
    job_id: str,
    component_id: str | None = None,
    render_target: dict | None = None,
    custom_storyboard: dict | None = None,
) -> None:
    """Punto de entrada del render en Modal.

    Reconstruye el ``VideoService`` y corre el mismo
    ``_prepare_and_run_render_job`` que se usaba in-process, leyendo/escribiendo
    todo en Supabase por ``job_id``.
    """
    import os
    import sys
    import asyncio
    import tempfile
    from uuid import UUID

    sys.path.insert(0, "/app/apps/api")
    os.chdir("/app/apps/api")

    # Vertex AI (Veo/Imagen) necesita un archivo de credenciales. Si el secret
    # trae el JSON inline en GOOGLE_APPLICATION_CREDENTIALS_JSON, lo
    # materializamos a un archivo y apuntamos GOOGLE_APPLICATION_CREDENTIALS.
    creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if creds_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        creds_path = os.path.join(tempfile.gettempdir(), "gcp-sa.json")
        with open(creds_path, "w", encoding="utf-8") as fh:
            fh.write(creds_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    from services.video.service import VideoService
    from models.dto.requests import StoryboardRequest

    service = VideoService()
    storyboard = StoryboardRequest(**custom_storyboard) if custom_storyboard else None

    asyncio.run(
        service._prepare_and_run_render_job(
            job_id=UUID(job_id),
            component_id=UUID(component_id) if component_id else None,
            render_target=render_target,
            custom_storyboard=storyboard,
        )
    )

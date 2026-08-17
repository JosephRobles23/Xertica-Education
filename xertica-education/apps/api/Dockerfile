# Imagen liviana del API para Cloud Run (Opción B).
#
# El trabajo pesado de render (Node/Remotion/Chromium/ffmpeg) NO vive aquí:
# corre en Modal. Esta imagen solo trae Python + las deps de FastAPI, así que
# es pequeña y arranca rápido (mejor cold start). El API únicamente crea el job
# y dispara la función de Modal con .spawn().
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# 1) Deps primero, para aprovechar la cache de capas de Docker.
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# 2) Código de la app.
COPY . .

# Cloud Run inyecta $PORT (8080 por defecto). El healthcheck pega a "/".
ENV PORT=8080
EXPOSE 8080

# NOTA: a propósito NO instalamos node, ffmpeg, chromium ni "playwright install".
# El API nunca renderiza; delega todo eso a Modal.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

# main.py
#
# Entry point for the Xertica Education FastAPI application.
# It initializes the FastAPI instance, configures CORS middleware,
# and registers routers to expose backend endpoints for learning paths and background jobs.
#
# Related files:
# - routers/jobs.py: Handles background tasks and content generation queues.
# - routers/learning_paths.py: Core logic for curating, building, and serving learning paths.

import os
from dotenv import load_dotenv

# Load environment variables from .env file into os.environ
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers.jobs import router as jobs_router
from routers.learning_paths import router as learning_paths_router
from routers.kb import router as kb_router
from routers.documents import router as documents_router
from routers.google_drive import router as google_drive_router
from routers.video import router as video_router

# Initialize the main FastAPI application instance.
# This object acts as the central router and coordinator for all incoming HTTP requests.
app = FastAPI(
    title="Xertica Education API",
    description="Backend API for managing learning routes and content orchestration",
    version="0.1.0",
)

# Configure Cross-Origin Resource Sharing (CORS).
# This middleware enables web browsers to securely make requests to this backend API
# from a different origin (specifically, the React/Vite frontend).
#
# Production Note: Currently configured to allow all origins ("*"). Before production deployment,
# restrict this to specific domain lists to prevent unauthorized cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register feature-specific API routers.
# This groups related endpoints together and prevents main.py from bloating.
app.include_router(jobs_router)
app.include_router(learning_paths_router)
app.include_router(kb_router)
app.include_router(documents_router)
app.include_router(google_drive_router)
app.include_router(video_router)

# Mount static files directory to serve local fallback assets
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")



@app.get("/")
async def root():
    """
    Returns a simple health check message to verify the API is running and reachable.
    
    Used by load balancers, monitoring tools, or developers to check basic status.
    """
    return {"message": "Xertica Education API is active."}


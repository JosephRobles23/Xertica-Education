from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.jobs import router as jobs_router
from routers.learning_paths import router as learning_paths_router

app = FastAPI(
    title="Xertica Education API",
    description="Backend API for managing learning routes and content orchestration",
    version="0.1.0",
)

# Enable CORS for the local React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(learning_paths_router)

@app.get("/")
async def root():
    return {"message": "Xertica Education API is active."}


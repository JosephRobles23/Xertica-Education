from fastapi import APIRouter

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])

@router.get("/")
async def list_learning_paths():
    return []

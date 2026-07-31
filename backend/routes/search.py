from fastapi import APIRouter

router = APIRouter()

@router.post("/search")
def search():
    return {
        "status": "success",
        "message": "Search API Working"
    }
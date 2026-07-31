from fastapi import APIRouter

router = APIRouter()

@router.post("/upload-event")
def upload_event():
    return {
        "status": "success",
        "message": "Upload API Working"
    }
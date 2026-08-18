import os
import shutil

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.face_service import (
    process_event_photos,
    generate_selfie_embedding
)

from services.faiss_service import (
    create_faiss_index,
    search_faces
)

# ==========================================
# FastAPI App
# ==========================================

app = FastAPI(
    title="AI Event Photo Sharing POC"
)

# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Folder Paths
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EVENT_FOLDER = os.path.join(UPLOAD_FOLDER, "event_photos")
SELFIE_FOLDER = os.path.join(UPLOAD_FOLDER, "selfie")

EMBEDDING_FOLDER = os.path.join(BASE_DIR, "embeddings")
FAISS_FOLDER = os.path.join(BASE_DIR, "faiss_index")

# ==========================================
# Create Required Folders
# ==========================================

os.makedirs(EVENT_FOLDER, exist_ok=True)
os.makedirs(SELFIE_FOLDER, exist_ok=True)
os.makedirs(EMBEDDING_FOLDER, exist_ok=True)
os.makedirs(FAISS_FOLDER, exist_ok=True)

# ==========================================
# Static Files
# ==========================================

app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_FOLDER),
    name="uploads"
)

# ==========================================
# Home API
# ==========================================

@app.get("/")
def home():
    return {
        "status": "success",
        "message": "AI Event Photo Sharing Backend Running"
    }

# ==========================================
# Upload Event Photos
# ==========================================

@app.post("/upload-event")
async def upload_event(files: list[UploadFile] = File(...)):

    # Clear previous event photos
    if os.path.exists(EVENT_FOLDER):
        for filename in os.listdir(EVENT_FOLDER):
            file_path = os.path.join(EVENT_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    # Save uploaded photos
    for file in files:
        destination = os.path.join(EVENT_FOLDER, file.filename)

        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    print("=" * 50)
    print("Event Photos Uploaded")
    print("=" * 50)

    # Generate embeddings
    process_event_photos()

    # Create FAISS Index
    create_faiss_index()

    return {
        "status": "success",
        "message": "Photos Indexed Successfully"
    }

# ==========================================
# Search Matching Photos
# ==========================================

@app.post("/search")
async def search(file: UploadFile = File(...)):

    # Clear previous selfie
    if os.path.exists(SELFIE_FOLDER):
        for filename in os.listdir(SELFIE_FOLDER):
            file_path = os.path.join(SELFIE_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    # Save selfie
    selfie_path = os.path.join(SELFIE_FOLDER, file.filename)

    with open(selfie_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("=" * 50)
    print("Selfie Uploaded")
    print("=" * 50)

    # Generate embedding
    embedding = generate_selfie_embedding(selfie_path)

    if embedding is None:
        return {
            "status": "failed",
            "message": "No Face Detected"
        }

    # Search similar faces
    matched_photos = search_faces(
        embedding,
        threshold=0.60,
        top_k=50
    )

    return {
        "status": "success",
        "matched_photos": matched_photos
    }

# ==========================================
# Run Locally
# ==========================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
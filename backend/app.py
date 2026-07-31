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



app = FastAPI(
    title="AI Event Photo Sharing POC"
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EVENT_FOLDER = os.path.join(UPLOAD_FOLDER, "event_photos")
SELFIE_FOLDER = os.path.join(UPLOAD_FOLDER, "selfie")

EMBEDDING_FOLDER = os.path.join(BASE_DIR, "embeddings")
FAISS_FOLDER = os.path.join(BASE_DIR, "faiss_index")



os.makedirs(EVENT_FOLDER, exist_ok=True)
os.makedirs(SELFIE_FOLDER, exist_ok=True)
os.makedirs(EMBEDDING_FOLDER, exist_ok=True)
os.makedirs(FAISS_FOLDER, exist_ok=True)



app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_FOLDER),
    name="uploads"
)



@app.get("/")
def home():

    return {
        "status": "success",
        "message": "AI Event Photo Sharing Backend Running"
    }



@app.post("/upload-event")
async def upload_event(
    files: list[UploadFile] = File(...)
):

   

    for filename in os.listdir(EVENT_FOLDER):

        file_path = os.path.join(
            EVENT_FOLDER,
            filename
        )

        if os.path.isfile(file_path):
            os.remove(file_path)

    

    for file in files:

        destination = os.path.join(
            EVENT_FOLDER,
            file.filename
        )

        with open(destination, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    print("=" * 50)
    print("Event Photos Uploaded")
    print("=" * 50)

    

    process_event_photos()

    

    create_faiss_index()

    return {

        "status": "success",

        "message": "Photos Indexed Successfully"

    }



@app.post("/search")
async def search(
    file: UploadFile = File(...)
):

    

    for filename in os.listdir(SELFIE_FOLDER):

        file_path = os.path.join(
            SELFIE_FOLDER,
            filename
        )

        if os.path.isfile(file_path):
            os.remove(file_path)

    

    selfie_path = os.path.join(
        SELFIE_FOLDER,
        file.filename
    )

    with open(selfie_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    print("=" * 50)
    print("Selfie Uploaded")
    print("=" * 50)

    

    embedding = generate_selfie_embedding(
        selfie_path
    )

    if embedding is None:

        return {

            "status": "failed",

            "message": "No Face Detected"

        }

    

    matched_photos = search_faces(

        embedding,

        threshold=0.60,

        top_k=50

    )

    return {

        "status": "success",

        "matched_photos": matched_photos

    }
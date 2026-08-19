

import os
from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(DOTENV_PATH)
# from services.cloud_face_service import generate_selfie_embedding_from_cloud, process_cloud_event_photos, search_faces
from services.face_service import (
    generate_selfie_embedding_from_cloud,
    process_cloud_event_photos,
    search_faces,
)
from services.database import setup_database
from routes.auth import router as auth_router
from routes.gallery import router as gallery_router
from routes.upload import router as upload_router
from routes.auth import current_user
from services.cloudinary_service import upload_event_photo, upload_selfie




# FastAPI App


app = FastAPI(
    title="AI Event Photo Sharing POC"
)
setup_database()
app.include_router(auth_router)
app.include_router(gallery_router)
app.include_router(upload_router)




# CORS


frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(

    CORSMiddleware,

    allow_origins=[origin.strip() for origin in frontend_origins.split(",") if origin.strip()],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)




# Home


@app.get("/")
def home():

    return {

        "status":"success",

        "message":
        "AI Event Photo Sharing Backend Running"

    }







# Upload Event Photos


@app.post("/upload-event")
async def upload_event(
        files: list[UploadFile] = File(...),
        user=Depends(current_user),
):


    
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if not files:
        raise HTTPException(400, "Select at least one event photo")

    cloud_urls = []
    uploaded_photos = []
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(400, f"{file.filename}: unsupported image type")
        try:
            result = upload_event_photo(file.file, file.filename, user_id=user["id"])
        except Exception as exc:
            raise HTTPException(502, f"Failed to upload {file.filename} to Cloudinary") from exc
        cloud_urls.append(result["secure_url"])
        uploaded_photos.append({"filename": file.filename, "cloud_url": result["secure_url"], "public_id": result["public_id"]})

    process_cloud_event_photos(cloud_urls, owner_user_id=user["id"])

    return {"status": "success", "message": "Photos uploaded to Cloudinary and indexed successfully", "photos": uploaded_photos}








# Search Face


@app.post("/search")
async def search(
        file: UploadFile = File(...),
        user=Depends(current_user),
):


   
    if file.content_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise HTTPException(400, "Unsupported selfie image type")
    try:
        upload_result = upload_selfie(file.file, file.filename, user_id=user["id"])
    except Exception as exc:
        raise HTTPException(502, "Failed to upload selfie to Cloudinary") from exc

    embedding = generate_selfie_embedding_from_cloud(upload_result["secure_url"])
    if embedding is None:
        return {"status": "failed", "message": "No Face Detected", "selfie_url": upload_result["secure_url"]}

    return {
        "status": "success",
        "selfie_url": upload_result["secure_url"],
        "matched_photos": search_faces(embedding, threshold=0.60, top_k=50),
    }

    # Legacy local-storage flow removed: photos and face vectors are cloud-backed.
    """
    # Clear old selfie
    

    if os.path.exists(SELFIE_FOLDER):

        for filename in os.listdir(
            SELFIE_FOLDER
        ):

            path = os.path.join(
                SELFIE_FOLDER,
                filename
            )


            if os.path.isfile(path):

                os.remove(path)




    
    # Save selfie
    

    selfie_path = os.path.join(

        SELFIE_FOLDER,

        file.filename

    )



    with open(
        selfie_path,
        "wb"
    ) as buffer:


        shutil.copyfileobj(
            file.file,
            buffer
        )



    print("="*50)
    print("Selfie Uploaded")
    print("="*50)




    
    # Generate selfie embedding
    
    embedding = generate_selfie_embedding(
        selfie_path
    )



    if embedding is None:

        return {

            "status":"failed",

            "message":
            "No Face Detected"

        }





    
    # Search FAISS
    

    matched_photos = search_faces(

        embedding,

        threshold=0.60,

        top_k=50

    )




    return {

        "status":"success",

        "matched_photos":
        matched_photos

    }
    """







# Run


if __name__ == "__main__":

    import uvicorn


    uvicorn.run(

        "app:app",

        host="0.0.0.0",

        port=8000,

        reload=False

    )

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from pathlib import Path
from services.cloudinary_service import upload_event_photo, upload_selfie
from routes.auth import current_user

router = APIRouter(prefix="/upload", tags=["Upload Photos"])


@router.post("/event-photos")
async def upload_event_photos(
    files: list[UploadFile] = File(...),
    user=Depends(current_user)
):
    """
    Upload event photos to Cloudinary cloud storage
    
    Args:
        files: List of image files to upload
        user: Current authenticated user
    
    Returns:
        dict: Upload status and list of uploaded photos with cloud URLs
    """
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    uploaded_photos = []
    
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(400, f"{file.filename}: unsupported image type. Allowed: JPEG, PNG, WebP, GIF")
        
        try:
            result = upload_event_photo(file.file, file.filename, user_id=user["id"])
            uploaded_photos.append({
                "filename": file.filename,
                "public_id": result["public_id"],
                "cloud_url": result["secure_url"],
                "file_size": result["file_size"],
                "format": result["format"]
            })
        except HTTPException:
            # Keep meaningful configuration and validation errors intact.
            raise
        except Exception as exc:
            raise HTTPException(502, f"Failed to upload {file.filename} to Cloudinary") from exc
    
    return {
        "status": "success",
        "message": f"Uploaded {len(uploaded_photos)} event photo(s) to cloud",
        "photos": uploaded_photos
    }


@router.post("/selfie")
async def upload_selfie_photo(
    file: UploadFile = File(...),
    user=Depends(current_user)
):
    """
    Upload selfie photo to Cloudinary cloud storage
    
    Args:
        file: Selfie image file to upload
        user: Current authenticated user
    
    Returns:
        dict: Upload status and selfie photo details with cloud URL
    """
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported image type. Allowed: JPEG, PNG, WebP, GIF")
    
    try:
        result = upload_selfie(file.file, file.filename, user_id=user["id"])
        return {
            "status": "success",
            "message": "Selfie uploaded to cloud successfully",
            "selfie": {
                "filename": file.filename,
                "public_id": result["public_id"],
                "cloud_url": result["secure_url"],
                "file_size": result["file_size"],
                "format": result["format"]
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Failed to upload selfie to Cloudinary") from exc

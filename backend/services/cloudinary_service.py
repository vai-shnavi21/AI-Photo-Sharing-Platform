"""
Cloudinary service for handling image uploads to cloud storage
"""
import os
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException


def get_cloudinary_uploader():
    """Initialize and return Cloudinary uploader"""
    if not all(os.getenv(k) for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")):
        raise HTTPException(503, "Cloudinary is not configured. Add backend/.env credentials.")
    
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True
    )
    return cloudinary.uploader


def upload_event_photo(file_obj, filename: str, user_id: int = None):
    """
    Upload event photo to Cloudinary
    
    Args:
        file_obj: File-like object to upload
        filename: Original filename
        user_id: Optional user ID for folder organization
    
    Returns:
        dict: Upload result with 'public_id', 'secure_url', 'url'
    """
    uploader = get_cloudinary_uploader()
    
    folder = "ai-event-gallery/event-photos"
    if user_id:
        folder = f"ai-event-gallery/user-{user_id}/event-photos"
    
    result = uploader.upload(
        file_obj,
        folder=folder,
        resource_type="auto",
        overwrite=False
    )
    if not result.get("public_id") or not result.get("secure_url"):
        raise HTTPException(502, "Cloudinary did not return an uploaded image URL")
    
    return {
        "public_id": result.get("public_id"),
        "secure_url": result.get("secure_url"),
        "url": result.get("url"),
        "file_size": result.get("bytes"),
        "format": result.get("format")
    }


def upload_selfie(file_obj, filename: str, user_id: int = None):
    """
    Upload selfie photo to Cloudinary
    
    Args:
        file_obj: File-like object to upload
        filename: Original filename
        user_id: Optional user ID for folder organization
    
    Returns:
        dict: Upload result with 'public_id', 'secure_url', 'url'
    """
    uploader = get_cloudinary_uploader()
    
    folder = "ai-event-gallery/selfies"
    if user_id:
        folder = f"ai-event-gallery/user-{user_id}/selfies"
    
    result = uploader.upload(
        file_obj,
        folder=folder,
        resource_type="auto",
        overwrite=False
    )
    if not result.get("public_id") or not result.get("secure_url"):
        raise HTTPException(502, "Cloudinary did not return an uploaded image URL")
    
    return {
        "public_id": result.get("public_id"),
        "secure_url": result.get("secure_url"),
        "url": result.get("url"),
        "file_size": result.get("bytes"),
        "format": result.get("format")
    }


def delete_cloud_image(public_id: str):
    """
    Delete image from Cloudinary
    
    Args:
        public_id: Cloudinary public_id of the image
    
    Returns:
        dict: Deletion result
    """
    uploader = get_cloudinary_uploader()
    try:
        return uploader.destroy(public_id, resource_type="image", invalidate=True)
    except Exception as e:
        raise HTTPException(500, f"Failed to delete image: {str(e)}")

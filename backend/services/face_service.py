

import os
import cv2
import json
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from insightface.app import FaceAnalysis
import requests
from io import BytesIO


# Project Paths


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv("APP_DATA_DIR", BASE_DIR)

UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
EVENT_FOLDER = os.path.join(UPLOAD_FOLDER, "event_photos")
SELFIE_FOLDER = os.path.join(UPLOAD_FOLDER, "selfie")

EMBEDDING_FOLDER = os.path.join(DATA_DIR, "embeddings")

EMBEDDING_PATH = os.path.join(EMBEDDING_FOLDER, "embeddings.npy")
MAPPING_PATH = os.path.join(EMBEDDING_FOLDER, "photo_mapping.json")

os.makedirs(EVENT_FOLDER, exist_ok=True)
os.makedirs(SELFIE_FOLDER, exist_ok=True)
os.makedirs(EMBEDDING_FOLDER, exist_ok=True)


DETECTION_MAX_DIM = 1280


# Load InsightFace Model


def get_ctx_id():
    """Use GPU if a CUDA execution provider is actually available, else CPU."""
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if "CUDAExecutionProvider" in providers:
            return 0
    except Exception:
        pass
    return -1


CTX_ID = get_ctx_id()

app = FaceAnalysis(name="buffalo_l")

#LARGE DATAsET

app.prepare(
    ctx_id=CTX_ID,
    det_size=(320, 320)
)

# SINGLE PHOTO
selfie_app = FaceAnalysis(name="buffalo_l")
selfie_app.prepare(
    ctx_id=CTX_ID,
    det_size=(640, 640)
)

print("InsightFace Models Loaded Successfully")
print("Using:", "GPU" if CTX_ID == 0 else "CPU")


# Helpers


def resize_for_detection(image, max_dim=DETECTION_MAX_DIM):
    h, w = image.shape[:2]
    scale = max_dim / max(h, w)
    if scale < 1:
        image = cv2.resize(image, (int(w * scale), int(h * scale)))
    return image


def download_image_from_url(url: str):
    """
    Download image from cloud URL and return as numpy array
    
    Args:
        url: Cloud URL of the image
    
    Returns:
        tuple: (filename, image_array) or (filename, None) if failed
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Convert bytes to image
        nparr = np.frombuffer(response.content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Extract filename from URL
        filename = url.split("/")[-1].split("?")[0] or "cloud_image"
        
        return filename, image
    except Exception as e:
        print(f"Error downloading image from {url}: {str(e)}")
        return url.split("/")[-1], None


def read_image(photo):
    """
    Read image from local file
    
    Args:
        photo: Filename of local photo
    
    Returns:
        tuple: (filename, image_array)
    """
    path = os.path.join(EVENT_FOLDER, photo)
    image = cv2.imread(path)
    return photo, image


def read_image_from_cloud(cloud_url: str):
    """
    Read image from cloud URL
    
    Args:
        cloud_url: Cloud URL of the photo
    
    Returns:
        tuple: (url, image_array)
    """
    _, image = download_image_from_url(cloud_url)
    # Persist the Cloudinary URL in the face mapping for matching results.
    return cloud_url, image


def load_existing_mapping():
    if not os.path.exists(MAPPING_PATH):
        return []
    with open(MAPPING_PATH, "r") as f:
        return json.load(f)


def load_existing_embeddings():
    if not os.path.exists(EMBEDDING_PATH):
        return None
    return np.load(EMBEDDING_PATH).astype("float32")


# Process Event Photos


def process_event_photos(force_reprocess=False):
    """
    Generates face embeddings for all event photos.
    By default, skips photos already present in photo_mapping.json,
    so re-running after new uploads only processes new photos.
    """

    existing_mapping = [] if force_reprocess else load_existing_mapping()
    existing_embeddings = None if force_reprocess else load_existing_embeddings()

    already_processed = {m["photo"] for m in existing_mapping}

    all_photos = os.listdir(EVENT_FOLDER)
    photos = [p for p in all_photos if p not in already_processed]

    print(f"Total Photos Found : {len(all_photos)}")
    print(f"Already Processed  : {len(already_processed)}")
    print(f"New Photos To Process : {len(photos)}")

    if len(photos) == 0:
        print("Nothing new to process.")
        return False

    new_embeddings = []
    new_photo_names = []
    new_bounding_boxes = []

   
    with ThreadPoolExecutor(max_workers=8) as executor:
        loaded = list(tqdm(
            executor.map(read_image, photos),
            total=len(photos),
            desc="Reading images"
        ))

    for photo, image in tqdm(loaded, desc="Detecting faces"):

        if image is None:
            print(f"Skipping (unreadable) {photo}")
            continue

        image = resize_for_detection(image)

        faces = app.get(image)

        if len(faces) == 0:
            print(f"{photo} -> 0 face(s)")
            continue

        for face in faces:
            new_embeddings.append(face.embedding)
            new_photo_names.append(photo)
            new_bounding_boxes.append(face.bbox.tolist())

    if len(new_embeddings) == 0:
        print("No new faces found.")
        return False

    new_embedding_array = np.array(new_embeddings).astype("float32")

    
    if existing_embeddings is not None and existing_embeddings.shape[0] > 0:
        embedding_array = np.vstack([existing_embeddings, new_embedding_array])
    else:
        embedding_array = new_embedding_array

    np.save(EMBEDDING_PATH, embedding_array)

    mapping = list(existing_mapping)
    for i in range(len(new_photo_names)):
        mapping.append({
            "photo": new_photo_names[i],
            "bbox": new_bounding_boxes[i]
        })

    with open(MAPPING_PATH, "w") as f:
        json.dump(mapping, f, indent=4)

    print("=" * 50)
    print("Embedding Generation Completed")
    print("=" * 50)
    print("New Faces Indexed :", len(new_embeddings))
    print("Total Faces Indexed :", len(mapping))

    return True


def process_cloud_event_photos(cloud_urls: list, force_reprocess=False):
    """
    Generates face embeddings for event photos from cloud URLs.
    
    Args:
        cloud_urls: List of cloud URLs to process
        force_reprocess: Force reprocessing even if already processed
    
    Returns:
        bool: True if new embeddings were processed
    """
    existing_mapping = [] if force_reprocess else load_existing_mapping()
    existing_embeddings = None if force_reprocess else load_existing_embeddings()

    already_processed = {m["photo"] for m in existing_mapping}
    urls_to_process = [url for url in cloud_urls if url not in already_processed]

    print(f"Total Cloud Photos Found : {len(cloud_urls)}")
    print(f"Already Processed  : {len(already_processed)}")
    print(f"New Photos To Process : {len(urls_to_process)}")

    if len(urls_to_process) == 0:
        print("Nothing new to process.")
        return False

    new_embeddings = []
    new_photo_names = []
    new_bounding_boxes = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        loaded = list(tqdm(
            executor.map(read_image_from_cloud, urls_to_process),
            total=len(urls_to_process),
            desc="Downloading cloud images"
        ))

    for photo_name, image in tqdm(loaded, desc="Detecting faces"):
        if image is None:
            print(f"Skipping (unreadable) {photo_name}")
            continue

        image = resize_for_detection(image)
        faces = app.get(image)

        if len(faces) == 0:
            print(f"{photo_name} -> 0 face(s)")
            continue

        for face in faces:
            new_embeddings.append(face.embedding)
            new_photo_names.append(photo_name)
            new_bounding_boxes.append(face.bbox.tolist())

    if len(new_embeddings) == 0:
        print("No new faces found.")
        return False

    new_embedding_array = np.array(new_embeddings).astype("float32")

    if existing_embeddings is not None and existing_embeddings.shape[0] > 0:
        embedding_array = np.vstack([existing_embeddings, new_embedding_array])
    else:
        embedding_array = new_embedding_array

    np.save(EMBEDDING_PATH, embedding_array)

    mapping = list(existing_mapping)
    for i in range(len(new_photo_names)):
        mapping.append({
            "photo": new_photo_names[i],
            "bbox": new_bounding_boxes[i]
        })

    with open(MAPPING_PATH, "w") as f:
        json.dump(mapping, f, indent=4)

    print("=" * 50)
    print("Embedding Generation Completed")
    print("=" * 50)
    print("New Faces Indexed :", len(new_embeddings))
    print("Total Faces Indexed :", len(mapping))

    return True



# Generate Embedding for Selfie


def generate_selfie_embedding(selfie_path):
    """
    Generate face embedding from local selfie file
    
    Args:
        selfie_path: Path to local selfie file
    
    Returns:
        numpy array: Face embedding or None if no face detected
    """
    image = cv2.imread(selfie_path)

    if image is None:
        return None

    faces = selfie_app.get(image)

    if len(faces) == 0:
        return None

    
    face = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    )

    embedding = face.embedding.astype("float32")

    return embedding


def generate_selfie_embedding_from_cloud(cloud_url: str):
    """
    Generate face embedding from cloud selfie URL
    
    Args:
        cloud_url: Cloud URL of selfie image
    
    Returns:
        numpy array: Face embedding or None if no face detected
    """
    _, image = download_image_from_url(cloud_url)

    if image is None:
        return None

    faces = selfie_app.get(image)

    if len(faces) == 0:
        return None

    # Get the largest face (assumed to be the person's face)
    face = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    )

    embedding = face.embedding.astype("float32")

    return embedding


if __name__ == "__main__":
    process_event_photos()

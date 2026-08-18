"""Face processing backed only by Cloudinary URLs and PostgreSQL."""
import json
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import requests
from insightface.app import FaceAnalysis

from services.database import connection

DETECTION_MAX_DIM = 1280


def _context_id():
    try:
        import onnxruntime as ort
        return 0 if "CUDAExecutionProvider" in ort.get_available_providers() else -1
    except Exception:
        return -1


_ctx_id = _context_id()
_event_model = FaceAnalysis(name="buffalo_l")
_event_model.prepare(ctx_id=_ctx_id, det_size=(320, 320))
_selfie_model = FaceAnalysis(name="buffalo_l")
_selfie_model.prepare(ctx_id=_ctx_id, det_size=(640, 640))


def _image_from_url(url: str):
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
    except requests.RequestException:
        return None


def _resize_for_detection(image):
    height, width = image.shape[:2]
    scale = DETECTION_MAX_DIM / max(height, width)
    if scale < 1:
        return cv2.resize(image, (int(width * scale), int(height * scale)))
    return image


def process_cloud_event_photos(cloud_urls: list[str], owner_user_id: int) -> bool:
    """Extract event faces from Cloudinary and persist vectors in PostgreSQL."""
    if not cloud_urls:
        return False

    with ThreadPoolExecutor(max_workers=4) as executor:
        images = list(executor.map(_image_from_url, cloud_urls))

    records = []
    for url, image in zip(cloud_urls, images):
        if image is None:
            continue
        for face_index, face in enumerate(_event_model.get(_resize_for_detection(image))):
            records.append((
                owner_user_id,
                url,
                face_index,
                json.dumps(face.embedding.astype("float32").tolist()),
                json.dumps(face.bbox.tolist()),
            ))

    if not records:
        return False

    with connection() as db:
        for record in records:
            db.execute(
                """INSERT INTO face_embeddings(owner_user_id, source_url, face_index, embedding, bounding_box)
                   VALUES (?, ?, ?, ?::jsonb, ?::jsonb)
                   ON CONFLICT (owner_user_id, source_url, face_index)
                   DO UPDATE SET embedding=EXCLUDED.embedding, bounding_box=EXCLUDED.bounding_box""",
                record,
            )
    return True


def generate_selfie_embedding_from_cloud(cloud_url: str):
    image = _image_from_url(cloud_url)
    if image is None:
        return None
    faces = _selfie_model.get(image)
    if not faces:
        return None
    largest_face = max(faces, key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]))
    return largest_face.embedding.astype("float32")


def search_faces(query_embedding, threshold: float = 0.60, top_k: int = 50):
    """Compare against PostgreSQL-stored embeddings without a local FAISS index."""
    query = np.asarray(query_embedding, dtype="float32")
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return []

    with connection() as db:
        rows = db.execute("SELECT source_url, embedding FROM face_embeddings").fetchall()

    best_by_photo = {}
    for row in rows:
        raw_embedding = row["embedding"]
        vector = np.asarray(json.loads(raw_embedding) if isinstance(raw_embedding, str) else raw_embedding, dtype="float32")
        denominator = query_norm * np.linalg.norm(vector)
        if denominator == 0:
            continue
        score = float(np.dot(query, vector) / denominator)
        if score >= threshold:
            best_by_photo[row["source_url"]] = max(score, best_by_photo.get(row["source_url"], -1.0))

    return [
        {"photo": photo, "similarity": round(score, 3)}
        for photo, score in sorted(best_by_photo.items(), key=lambda item: item[1], reverse=True)[:top_k]
    ]

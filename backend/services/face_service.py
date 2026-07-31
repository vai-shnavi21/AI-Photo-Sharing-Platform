import os
import cv2
import json
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from insightface.app import FaceAnalysis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EVENT_FOLDER = os.path.join(UPLOAD_FOLDER, "event_photos")
SELFIE_FOLDER = os.path.join(UPLOAD_FOLDER, "selfie")

EMBEDDING_FOLDER = os.path.join(BASE_DIR, "embeddings")

EMBEDDING_PATH = os.path.join(EMBEDDING_FOLDER, "embeddings.npy")
MAPPING_PATH = os.path.join(EMBEDDING_FOLDER, "photo_mapping.json")

os.makedirs(EVENT_FOLDER, exist_ok=True)
os.makedirs(SELFIE_FOLDER, exist_ok=True)
os.makedirs(EMBEDDING_FOLDER, exist_ok=True)

DETECTION_MAX_DIM = 1280


def get_ctx_id():
    try:
        import onnxruntime as ort

        if "CUDAExecutionProvider" in ort.get_available_providers():
            return 0
    except Exception:
        pass

    return -1


CTX_ID = get_ctx_id()

app = None
selfie_app = None


def get_event_model():
    global app

    if app is None:
        app = FaceAnalysis(name="buffalo_s")
        app.prepare(ctx_id=CTX_ID, det_size=(320, 320))

    return app


def get_selfie_model():
    global selfie_app

    if selfie_app is None:
        selfie_app = FaceAnalysis(name="buffalo_s")
        selfie_app.prepare(ctx_id=CTX_ID, det_size=(640, 640))

    return selfie_app


def resize_for_detection(image, max_dim=DETECTION_MAX_DIM):
    h, w = image.shape[:2]

    scale = max_dim / max(h, w)

    if scale < 1:
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    return image


def read_image(photo):
    path = os.path.join(EVENT_FOLDER, photo)
    image = cv2.imread(path)
    return photo, image


def load_existing_mapping():
    if not os.path.exists(MAPPING_PATH):
        return []

    with open(MAPPING_PATH, "r") as f:
        return json.load(f)


def load_existing_embeddings():
    if not os.path.exists(EMBEDDING_PATH):
        return None

    return np.load(EMBEDDING_PATH).astype("float32")


def process_event_photos(force_reprocess=False):

    existing_mapping = [] if force_reprocess else load_existing_mapping()
    existing_embeddings = None if force_reprocess else load_existing_embeddings()

    already_processed = {m["photo"] for m in existing_mapping}

    all_photos = os.listdir(EVENT_FOLDER)
    photos = [p for p in all_photos if p not in already_processed]

    if len(photos) == 0:
        return False

    model = get_event_model()

    new_embeddings = []
    new_photo_names = []
    new_boxes = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        loaded = list(executor.map(read_image, photos))

    for photo, image in tqdm(loaded):

        if image is None:
            continue

        image = resize_for_detection(image)

        faces = model.get(image)

        for face in faces:
            new_embeddings.append(face.embedding)
            new_photo_names.append(photo)
            new_boxes.append(face.bbox.tolist())

    if len(new_embeddings) == 0:
        return False

    new_embeddings = np.array(new_embeddings).astype("float32")

    if existing_embeddings is not None:
        embeddings = np.vstack([existing_embeddings, new_embeddings])
    else:
        embeddings = new_embeddings

    np.save(EMBEDDING_PATH, embeddings)

    mapping = existing_mapping

    for i in range(len(new_photo_names)):
        mapping.append({
            "photo": new_photo_names[i],
            "bbox": new_boxes[i]
        })

    with open(MAPPING_PATH, "w") as f:
        json.dump(mapping, f, indent=4)

    return True


def generate_selfie_embedding(selfie_path):

    image = cv2.imread(selfie_path)

    if image is None:
        return None

    model = get_selfie_model()

    faces = model.get(image)

    if len(faces) == 0:
        return None

    face = max(
        faces,
        key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1])
    )

    return face.embedding.astype("float32")
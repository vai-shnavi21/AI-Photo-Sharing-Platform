import os
import json
import faiss
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EMBEDDING_FOLDER = os.path.join(BASE_DIR, "embeddings")
FAISS_FOLDER = os.path.join(BASE_DIR, "faiss_index")

os.makedirs(FAISS_FOLDER, exist_ok=True)

INDEX_PATH = os.path.join(FAISS_FOLDER, "index.faiss")

EMBEDDING_PATH = os.path.join(EMBEDDING_FOLDER, "embeddings.npy")
MAPPING_PATH = os.path.join(EMBEDDING_FOLDER, "photo_mapping.json")

_index = None
_mapping = None


def load_mapping():
    global _mapping

    if _mapping is None:
        with open(MAPPING_PATH, "r") as f:
            _mapping = json.load(f)

    return _mapping


def load_index():
    global _index

    if _index is None:
        _index = faiss.read_index(INDEX_PATH)

    return _index


def create_faiss_index():

    embeddings = np.load(EMBEDDING_PATH).astype("float32")

    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatIP(embeddings.shape[1])

    ids = np.arange(len(embeddings)).astype(np.int64)

    index = faiss.IndexIDMap(index)

    index.add_with_ids(embeddings, ids)

    faiss.write_index(index, INDEX_PATH)

    global _index
    _index = index

    return True


def search_faces(query_embedding, threshold=0.60, top_k=50):

    index = load_index()

    mapping = load_mapping()

    query = query_embedding.reshape(1, -1).astype("float32")

    faiss.normalize_L2(query)

    distances, indices = index.search(query, top_k)

    results = []

    used = set()

    for score, idx in zip(distances[0], indices[0]):

        if idx == -1:
            continue

        if score < threshold:
            continue

        photo = mapping[idx]["photo"]

        if photo in used:
            continue

        used.add(photo)

        results.append({
            "photo": photo,
            "similarity": round(float(score), 3)
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)

    return results
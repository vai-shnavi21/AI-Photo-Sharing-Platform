
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



_index_cache = None
_mapping_cache = None


def get_mapping(force_reload=False):
    global _mapping_cache

    if _mapping_cache is None or force_reload:
        if not os.path.exists(MAPPING_PATH):
            raise FileNotFoundError(
                f"Mapping file not found at {MAPPING_PATH}. "
                "Run process_event_photos() first."
            )
        with open(MAPPING_PATH, "r") as f:
            _mapping_cache = json.load(f)

    return _mapping_cache


def get_index(force_reload=False):
    global _index_cache

    if _index_cache is None or force_reload:
        _index_cache = load_index()

    return _index_cache




def create_faiss_index():

    if not os.path.exists(EMBEDDING_PATH):
        raise FileNotFoundError(
            f"Embeddings not found at {EMBEDDING_PATH}. "
            "Run process_event_photos() first."
        )

    embeddings = np.load(EMBEDDING_PATH).astype("float32")

    if embeddings.shape[0] == 0:
        print("No embeddings to index.")
        return False

    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]


    photo_ids = np.arange(embeddings.shape[0], dtype=np.int64)

    base_index = faiss.IndexFlatIP(dimension)
    index = faiss.IndexIDMap(base_index)
    index.add_with_ids(embeddings, photo_ids)

    faiss.write_index(index, INDEX_PATH)

    print("=" * 50)
    print("FAISS Index Created Successfully")
    print("Total Faces :", index.ntotal)
    print("=" * 50)

    
    global _index_cache, _mapping_cache
    _index_cache = index
    _mapping_cache = None  

    return True




def load_index():

    if not os.path.exists(INDEX_PATH):
        return None

    return faiss.read_index(INDEX_PATH)




def search_faces(query_embedding, threshold=0.60, top_k=50):

    index = get_index()

    if index is None:
        return []

    query_embedding = query_embedding.reshape(1, -1).astype("float32")

    faiss.normalize_L2(query_embedding)

    distances, indices = index.search(query_embedding, top_k)

    mapping = get_mapping()

    matched = []
    used = set()

    for score, idx in zip(distances[0], indices[0]):

        if idx == -1:
            continue

        if score < threshold:
            continue

        if idx >= len(mapping):
           
            continue

        photo = mapping[idx]["photo"]

        if photo in used:
            continue

        used.add(photo)

        matched.append({
            "photo": photo,
            "similarity": round(float(score), 3)
        })

    matched.sort(key=lambda x: x["similarity"], reverse=True)

    return matched


def reload_index():
    """Call after re-running create_faiss_index() so a running service
    picks up the new index/mapping without a restart."""
    get_index(force_reload=True)
    get_mapping(force_reload=True)
# backend/ml/embeddings.py

import numpy as np
import pickle
import os
import faiss
from sentence_transformers import SentenceTransformer

EMBEDDINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'embeddings.npy')
FAISS_PATH = os.path.join(os.path.dirname(__file__), '..', 'faiss_index.pkl')
IDS_PATH = os.path.join(os.path.dirname(__file__), '..', 'post_ids.pkl')

MODEL_NAME = 'all-MiniLM-L6-v2'

# Global cache — loaded once, reused forever
_model = None
_index = None
_ids = None

def get_model():
    global _model
    if _model is None:
        print("Loading sentence-transformers model...")
        _model = SentenceTransformer(MODEL_NAME)
        print("Model loaded.")
    return _model

def get_index_and_ids():
    global _index, _ids
    if _index is None or _ids is None:
        print("Loading FAISS index...")
        with open(FAISS_PATH, 'rb') as f:
            _index = pickle.load(f)
        with open(IDS_PATH, 'rb') as f:
            _ids = pickle.load(f)
        print(f"FAISS index loaded: {_index.ntotal} vectors")
    return _index, _ids

def embeddings_exist():
    return (os.path.exists(EMBEDDINGS_PATH) and
            os.path.exists(FAISS_PATH) and
            os.path.exists(IDS_PATH))

def load_embeddings():
    embeddings = np.load(EMBEDDINGS_PATH, allow_pickle=True)
    index, ids = get_index_and_ids()
    return embeddings, index, ids

def search_similar(query: str, top_k: int = 10):
    if not embeddings_exist():
        raise RuntimeError("Embeddings not built yet.")

    model = get_model()
    index, ids = get_index_and_ids()

    query_vec = model.encode([query]).astype('float32')
    distances, indices = index.search(query_vec, top_k)

    result_ids = [ids[i] for i in indices[0]]
    scores = distances[0].tolist()
    return result_ids, scores

def build_embeddings():
    from data.database import get_connection
    print("Loading posts from DuckDB...")
    con = get_connection()
    df = con.execute("SELECT id, text FROM posts ORDER BY rowid").fetchdf()
    texts = df['text'].tolist()
    ids = df['id'].tolist()

    print(f"Embedding {len(texts)} posts...")
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings = embeddings.astype('float32')

    np.save(EMBEDDINGS_PATH, embeddings)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    with open(FAISS_PATH, 'wb') as f:
        pickle.dump(index, f)
    with open(IDS_PATH, 'wb') as f:
        pickle.dump(ids, f)

    print("Done.")
    return embeddings, index, ids

if __name__ == '__main__':
    build_embeddings()
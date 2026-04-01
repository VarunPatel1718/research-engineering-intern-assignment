# backend/ml/embeddings.py

import numpy as np
import pickle
import os
import faiss
from sentence_transformers import SentenceTransformer
from data.database import get_connection

EMBEDDINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'embeddings.npy')
FAISS_PATH = os.path.join(os.path.dirname(__file__), '..', 'faiss_index.pkl')
IDS_PATH = os.path.join(os.path.dirname(__file__), '..', 'post_ids.pkl')

MODEL_NAME = 'all-MiniLM-L6-v2'

def build_embeddings():
    """Build and save embeddings + FAISS index. Run once."""
    print("Loading posts from DuckDB...")
    con = get_connection()
    df = con.execute("SELECT id, text FROM posts ORDER BY rowid").fetchdf()
    
    texts = df['text'].tolist()
    ids = df['id'].tolist()

    print(f"Embedding {len(texts)} posts with {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings = embeddings.astype('float32')

    # Save raw embeddings
    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"Saved embeddings to {EMBEDDINGS_PATH}")

    # Build FAISS index
    dim = embeddings.shape[1]  # 384
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    print(f"FAISS index built with {index.ntotal} vectors")

    # Save FAISS index + post IDs
    with open(FAISS_PATH, 'wb') as f:
        pickle.dump(index, f)
    with open(IDS_PATH, 'wb') as f:
        pickle.dump(ids, f)

    print("Done! FAISS index and IDs saved.")
    return embeddings, index, ids

def load_embeddings():
    """Load saved embeddings + FAISS index from disk."""
    embeddings = np.load(EMBEDDINGS_PATH)
    with open(FAISS_PATH, 'rb') as f:
        index = pickle.load(f)
    with open(IDS_PATH, 'rb') as f:
        ids = pickle.load(f)
    return embeddings, index, ids

def embeddings_exist():
    return (os.path.exists(EMBEDDINGS_PATH) and 
            os.path.exists(FAISS_PATH) and 
            os.path.exists(IDS_PATH))

def search_similar(query: str, top_k: int = 10):
    """Search for posts semantically similar to query."""
    if not embeddings_exist():
        raise RuntimeError("Embeddings not built yet. Run build_embeddings() first.")
    
    _, index, ids = load_embeddings()
    
    model = SentenceTransformer(MODEL_NAME)
    query_vec = model.encode([query]).astype('float32')
    
    distances, indices = index.search(query_vec, top_k)
    
    result_ids = [ids[i] for i in indices[0]]
    scores = distances[0].tolist()
    
    return result_ids, scores

if __name__ == '__main__':
    build_embeddings()
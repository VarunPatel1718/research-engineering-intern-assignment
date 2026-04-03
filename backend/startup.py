# backend/startup.py
import os
import sys

DATA_PATH = "data.jsonl"
DB_PATH = "narrativetrail.db"
FAISS_PATH = "faiss_index.pkl"
CLUSTERS_PATH = "clusters.json"

def download_data():
    if os.path.exists(DATA_PATH):
        print("data.jsonl already exists, skipping download")
        return True
    print("Downloading data.jsonl from Google Drive...")
    try:
        import gdown
        # Direct download link for the file
        url = "https://drive.google.com/uc?id=1XHtTnUpTjUIIREKGF8ETaZ_hEtxtPJWY"
        gdown.download(url, DATA_PATH, quiet=False)
        return os.path.exists(DATA_PATH)
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def build_database():
    if os.path.exists(DB_PATH):
        print("Database already exists, skipping")
        return True
    print("Building DuckDB database...")
    try:
        from data.loader import load_data
        load_data(DATA_PATH)
        return True
    except Exception as e:
        print(f"Database build failed: {e}")
        return False

def build_embeddings():
    if os.path.exists(FAISS_PATH):
        print("FAISS index already exists, skipping")
        return True
    print("Building embeddings and FAISS index...")
    try:
        from ml.embeddings import build_embeddings
        build_embeddings()
        return True
    except Exception as e:
        print(f"Embeddings build failed: {e}")
        return False

def build_clusters_cache():
    if os.path.exists(CLUSTERS_PATH):
        print("Clusters cache already exists, skipping")
        return True
    print("Building topic clusters...")
    try:
        from ml.clustering import build_clusters
        build_clusters(nr_topics=10)
        return True
    except Exception as e:
        print(f"Clusters build failed: {e}")
        return False

if __name__ == "__main__":
    print("=== NarrativeTrail Startup ===")
    if not download_data():
        print("ERROR: Could not get data. Exiting.")
        sys.exit(1)
    build_database()
    build_embeddings()
    build_clusters_cache()
    print("=== Startup complete ===")
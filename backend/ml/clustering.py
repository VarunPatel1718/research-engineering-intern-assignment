# backend/ml/clustering.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pickle
import os
import json
from bertopic import BERTopic
from umap import UMAP
from ml.embeddings import load_embeddings, embeddings_exist
from data.database import get_connection

CLUSTERS_PATH = os.path.join(os.path.dirname(__file__), '..', 'clusters.json')

def build_clusters(nr_topics: int = 10):
    """Run BERTopic on saved embeddings. Saves cluster results to disk."""
    if not embeddings_exist():
        raise RuntimeError("Build embeddings first.")

    print("Loading embeddings and posts...")
    embeddings, _, ids = load_embeddings()

    con = get_connection()
    df = con.execute("SELECT id, text FROM posts ORDER BY rowid").fetchdf()
    texts = df['text'].tolist()

    print(f"Running BERTopic with nr_topics={nr_topics}...")
    
    umap_model = UMAP(
        n_neighbors=15,
        n_components=5,
        min_dist=0.0,
        metric='cosine',
        random_state=42
    )
    
    topic_model = BERTopic(
        umap_model=umap_model,
        nr_topics=nr_topics,
        verbose=True
    )
    
    topics, probs = topic_model.fit_transform(texts, embeddings)

    # Get topic info
    topic_info = topic_model.get_topic_info()
    
    # Build UMAP 2D projection for visualization
    print("Building 2D UMAP projection for visualization...")
    umap_2d = UMAP(
        n_neighbors=15,
        n_components=2,
        min_dist=0.1,
        metric='cosine',
        random_state=42
    )
    coords_2d = umap_2d.fit_transform(embeddings)

    # Assemble result
    result = {
        'nr_topics': nr_topics,
        'topic_info': topic_info[['Topic', 'Count', 'Name']].to_dict(orient='records'),
        'points': [
            {
                'id': ids[i],
                'x': float(coords_2d[i][0]),
                'y': float(coords_2d[i][1]),
                'topic': int(topics[i]),
            }
            for i in range(len(ids))
        ]
    }

    with open(CLUSTERS_PATH, 'w') as f:
        json.dump(result, f)

    print(f"Saved clusters to {CLUSTERS_PATH}")
    return result

def load_clusters():
    if not os.path.exists(CLUSTERS_PATH):
        return None
    with open(CLUSTERS_PATH, 'r') as f:
        return json.load(f)

if __name__ == '__main__':
    build_clusters(nr_topics=10)
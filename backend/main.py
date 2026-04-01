# backend/main.py

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="NarrativeTrail API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "NarrativeTrail backend running"}

# ── Stats ─────────────────────────────────────────────────
@app.get("/api/stats")
def stats():
    from data.database import get_stats
    return get_stats()

# ── Subreddits ────────────────────────────────────────────
@app.get("/api/subreddits")
def subreddits():
    from data.database import get_subreddits
    return get_subreddits()

# ── Timeline ──────────────────────────────────────────────
@app.get("/api/timeline")
def timeline(
    query: Optional[str] = Query(default=''),
    subreddits: Optional[str] = Query(default='')
):
    from data.database import get_timeline
    subreddit_list = [s.strip() for s in subreddits.split(',') if s.strip()] if subreddits else []
    data = get_timeline(query=query, subreddits=subreddit_list)
    return {"data": data, "query": query}

# ── Network ───────────────────────────────────────────────
@app.get("/api/network")
def network():
    from data.database import get_network_data
    nodes, edges = get_network_data()
    return {"nodes": nodes, "edges": edges}

# ── Semantic Search (FAISS) ───────────────────────────────
@app.get("/api/search")
def search(q: Optional[str] = Query(default=''), top_k: int = 10):
    if not q or not q.strip():
        return {"results": [], "query": q, "suggestions": []}

    from ml.embeddings import search_similar, embeddings_exist
    from data.database import get_posts_by_ids

    if not embeddings_exist():
        return {"error": "Embeddings not built yet. Run ml/embeddings.py first."}

    result_ids, distances = search_similar(q, top_k=top_k)
    posts = get_posts_by_ids(result_ids)

    # Add distance score to each post
    id_to_dist = dict(zip(result_ids, distances))
    for post in posts:
        post['similarity_score'] = round(float(id_to_dist.get(post['id'], 0)), 4)

    # Suggest follow-up queries based on top result titles
    suggestions = []
    if posts:
        top_titles = [p['title'] for p in posts[:3]]
        suggestions = generate_suggestions(q, top_titles)

    return {"results": posts, "query": q, "suggestions": suggestions}

def generate_suggestions(query: str, top_titles: list):
    """Simple rule-based follow-up suggestions."""
    suggestions = [
        f"{query} Conservative vs Liberal framing",
        f"{query} election impact 2024",
        f"{query} reddit community response"
    ]
    return suggestions[:3]

# ── Clusters (BERTopic) ───────────────────────────────────
@app.get("/api/clusters")
def clusters(nr_topics: int = Query(default=10)):
    from ml.clustering import load_clusters, build_clusters

    cached = load_clusters()

    # Rebuild if different nr_topics requested
    if cached is None or cached.get('nr_topics') != nr_topics:
        cached = build_clusters(nr_topics=nr_topics)

    return cached

# ── Run ───────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("DuckDB connected")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
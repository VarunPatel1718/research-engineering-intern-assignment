# backend/main.py

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()
# Run startup checks
import startup
startup.download_data()
startup.build_database()
startup.build_embeddings()
startup.build_clusters_cache()

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
    from ml.summarizer import summarize_timeline
    subreddit_list = [s.strip() for s in subreddits.split(',') if s.strip()] if subreddits else []
    data = get_timeline(query=query, subreddits=subreddit_list)
    summary = summarize_timeline(query, data)
    return {"data": data, "query": query, "summary": summary}

# ── Network with PageRank ─────────────────────────────────
@app.get("/api/network")
def network():
    from ml.network import build_network
    from ml.summarizer import summarize_network
    result = build_network()
    result['summary'] = summarize_network(result['stats'])
    return result

# ── Semantic Search ───────────────────────────────────────
@app.get("/api/search")
def search(q: Optional[str] = Query(default=''), top_k: int = 10):
    if not q or not q.strip():
        return {"results": [], "query": q, "suggestions": [], "summary": ""}

    from ml.embeddings import search_similar, embeddings_exist
    from data.database import get_posts_by_ids
    from ml.summarizer import summarize_search

    if not embeddings_exist():
        return {"error": "Embeddings not built yet."}

    result_ids, distances = search_similar(q, top_k=top_k)
    posts = get_posts_by_ids(result_ids)

    id_to_dist = dict(zip(result_ids, distances))
    for post in posts:
        post['similarity_score'] = round(float(id_to_dist.get(post['id'], 0)), 4)

    summary = summarize_search(q, posts)

    suggestions = [
        f"{q} Conservative vs Liberal framing",
        f"{q} election impact 2024",
        f"{q} reddit community response"
    ]

    return {"results": posts, "query": q, "suggestions": suggestions, "summary": summary}
# ── Clusters ──────────────────────────────────────────────
@app.get("/api/clusters")
def clusters(nr_topics: int = Query(default=10)):
    from ml.clustering import load_clusters, build_clusters
    from ml.summarizer import summarize_clusters
    from data.database import get_connection

    cached = load_clusters()
    if cached is None or cached.get('nr_topics') != nr_topics:
        cached = build_clusters(nr_topics=nr_topics)

    try:
        summary = summarize_clusters(cached.get('topic_info', []), nr_topics)
        cached['summary'] = summary
    except Exception as e:
        cached['summary'] = f"Analysis of {nr_topics} topic clusters across political communities."

    con = get_connection()
    total = con.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    cached['total_posts'] = total

    return cached

# ── Run ───────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("DuckDB connected")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
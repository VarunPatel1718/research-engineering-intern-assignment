# backend/main.py

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
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
        return {
            "results": [],
            "query": q,
            "suggestions": [
                "immigration border policy",
                "election integrity 2024",
                "economic inequality capitalism"
            ],
            "summary": "Enter a search query to find semantically similar posts across all 10 political communities."
        }

    if len(q.strip()) < 3:
        return {
            "results": [],
            "query": q,
            "suggestions": [f"{q} policy", f"{q} debate 2024", f"{q} political impact"],
            "summary": f"Query '{q}' is too short. Try a more descriptive phrase."
        }

    from ml.embeddings import search_similar, embeddings_exist
    from data.database import get_posts_by_ids
    from ml.summarizer import summarize_search

    if not embeddings_exist():
        return {"error": "Embeddings not built yet."}

    try:
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

    except Exception as e:
        return {
            "results": [],
            "query": q,
            "suggestions": [],
            "summary": "Search encountered an error. Please try a different query."
        }

# ── Clusters ──────────────────────────────────────────────
@app.get("/api/clusters")
def clusters(nr_topics: int = Query(default=10)):
    from ml.clustering import load_clusters, build_clusters
    from ml.summarizer import summarize_clusters, generate_topic_labels

    cached = load_clusters()
    if cached is None or cached.get('nr_topics') != nr_topics:
        cached = build_clusters(nr_topics=nr_topics)

    labels = generate_topic_labels(cached.get('topic_info', []))

    for topic in cached.get('topic_info', []):
        topic_id = str(topic['Topic'])
        if topic_id in labels:
            topic['Label'] = labels[topic_id]
        else:
            topic['Label'] = topic['Name']

    summary = summarize_clusters(cached.get('topic_info', []), nr_topics)
    cached['summary'] = summary
    return cached

# ── Chatbot ───────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    message: str

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    try:
        from api.chatbot import chat
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        result = chat(messages, req.message)
        return result
    except Exception as e:
        print(f"Chat error: {e}")
        return {
            "reply": f"I encountered an error: {str(e)}. Please try again.",
            "suggestions": []
        }

# ── Run ───────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("DuckDB connected")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd, numpy as np, faiss, json, os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://localhost:3000", "*.vercel.app"])

DATA = "../data"

# ── LOAD ALL DATA AT STARTUP ─────────────────────────────────────────────────
print("Loading data files...")
df = pd.read_parquet(f"{DATA}/processed.parquet")
meta = pd.read_parquet(f"{DATA}/search_meta.parquet")
index = faiss.read_index(f"{DATA}/faiss.index")

with open(f"{DATA}/network_subreddit.json") as f: net_sub = json.load(f)
with open(f"{DATA}/network_author.json") as f: net_auth = json.load(f)
with open(f"{DATA}/network_source.json") as f: net_src = json.load(f)
with open(f"{DATA}/events.json") as f: evts = json.load(f)
with open(f"{DATA}/clusters.json") as f: clust_data = json.load(f)

from sentence_transformers import SentenceTransformer
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

try:
    import anthropic
    ai = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    AI_OK = True
except: AI_OK = False

print(f"Ready. {len(df)} posts loaded. AI={AI_OK}")


def claude(prompt, max_tokens=200):
    """Call Claude API with fallback — never crashes."""
    if not AI_OK: return "AI summary unavailable — API key not configured."
    try:
        r = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            messages=[{"role":"user","content":prompt}]
        )
        return r.content[0].text
    except Exception as e:
        return f"AI summary temporarily unavailable: {str(e)[:50]}"


# ── ENDPOINT 1: HEALTH ────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status":"ok","total_posts":len(df),
                    "date_start":str(df["created_utc"].min()),
                    "date_end":str(df["created_utc"].max())})

# ── ENDPOINT 2: STATS ─────────────────────────────────────────────────────────
@app.route("/api/stats")
def stats():
    clean = df[~df["is_spam"]]
    top = clean.nlargest(1,"score").iloc[0]
    return jsonify({
        "total_posts": len(clean),
        "total_authors": clean["author"].nunique(),
        "total_subreddits": clean["subreddit"].nunique(),
        "date_start": str(clean["created_utc"].min()),
        "date_end": str(clean["created_utc"].max()),
        "spam_flagged": int(df["is_spam"].sum()),
        "crosspost_count": int(clean["crosspost_parent"].notna().sum()),
        "avg_score": round(float(clean["score"].mean()),1),
        "top_post": {"title":top["title"],"score":int(top["score"]),
                     "subreddit":top["subreddit"]}
    })

# ── ENDPOINT 3: SUBREDDITS ────────────────────────────────────────────────────
@app.route("/api/subreddits")
def subreddits():
    counts = df.groupby("subreddit").agg(
        count=("id","count"), avg_score=("score","mean"),
        subscribers=("subreddit_subscribers","max"),
        bloc=("ideological_bloc","first")
    ).reset_index()
    counts["avg_score"] = counts["avg_score"].round(1)
    return jsonify(counts.to_dict(orient="records"))

# ── ENDPOINT 4: TIMESERIES ────────────────────────────────────────────────────
@app.route("/api/timeseries")
def timeseries():
    sub = request.args.get("subreddit","all")
    gran = request.args.get("granularity","week")
    inc_spam = request.args.get("include_spam","false")=="true"
    data = df.copy()
    if not inc_spam: data = data[~data["is_spam"]]
    if sub != "all": data = data[data["subreddit"]==sub]
    if not len(data): return jsonify([])
    freq = "W" if gran=="week" else "D" if gran=="day" else "ME"
    ts = (data.set_index("created_utc").sort_index()
          .resample(freq)
          .agg(count=("id","count"),avg_score=("score","mean"),
               avg_comments=("num_comments","mean"))
          .reset_index())
    ts["created_utc"] = ts["created_utc"].astype(str)
    return jsonify(ts.fillna(0).round(2).to_dict(orient="records"))

# ── ENDPOINT 5: TIMESERIES BY BLOC ───────────────────────────────────────────
@app.route("/api/timeseries/blocs")
def timeseries_blocs():
    gran = request.args.get("granularity","week")
    freq = "W" if gran=="week" else "D"
    data = df[~df["is_spam"]].set_index("created_utc").sort_index()
    result = {}
    for bloc in data["ideological_bloc"].unique():
        ts = (data[data["ideological_bloc"]==bloc]
              .resample(freq).agg(count=("id","count")).reset_index())
        ts["created_utc"] = ts["created_utc"].astype(str)
        result[bloc] = ts.to_dict(orient="records")
    return jsonify(result)

# ── ENDPOINT 6: EVENTS ────────────────────────────────────────────────────────
@app.route("/api/events")
def events(): return jsonify(evts)

# ── ENDPOINT 7: TOP DOMAINS ───────────────────────────────────────────────────
@app.route("/api/topdomain")
def topdomain():
    sub = request.args.get("subreddit","all")
    data = df[~df["is_self_post"] & (df["domain"]!="") & ~df["is_spam"]].copy()
    if sub != "all": data = data[data["subreddit"]==sub]
    counts = data["domain"].value_counts().head(15).reset_index()
    counts.columns = ["domain","count"]
    L={"theguardian.com","nytimes.com","huffpost.com"}
    R={"foxnews.com","breitbart.com","nypost.com","townhall.com"}
    counts["bias"] = counts["domain"].apply(
        lambda d: "left" if d in L else "right" if d in R else "center")
    return jsonify(counts.to_dict(orient="records"))

# ── ENDPOINT 8: NETWORK ───────────────────────────────────────────────────────
@app.route("/api/network")
def network():
    ntype = request.args.get("type","subreddit")
    remove = request.args.get("remove_node",None)
    if ntype=="subreddit": base = net_sub
    elif ntype=="author": base = net_auth
    else: base = net_src
    if remove:
        data = {
            "nodes": [n for n in base["nodes"] if n["id"]!=remove],
            "edges": [e for e in base["edges"]
                      if e["source"]!=remove and e["target"]!=remove]
        }
    else:
        data = base
    return jsonify(data)

# ── ENDPOINT 9: SEMANTIC SEARCH ───────────────────────────────────────────────
@app.route("/api/search")
def search():
    q = request.args.get("q","").strip()
    lim = min(int(request.args.get("limit",20)),50)
    sub = request.args.get("subreddit","all")
    bloc = request.args.get("bloc","all")

    if not q or len(q) < 2:
        return jsonify({"results":[],"total":0,"query":q,
                        "suggested_queries":[],"warning":"Query too short — enter at least 2 characters"})

    q_emb = embed_model.encode([q]).astype("float32")
    faiss.normalize_L2(q_emb)
    D, I = index.search(q_emb, lim * 4)

    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.2]
    if sub != "all": results = results[results["subreddit"]==sub]
    if bloc != "all": results = results[results["ideological_bloc"]==bloc]
    results = results.head(lim)
    results["created_utc"] = results["created_utc"].astype(str)

    return jsonify({"results":results.to_dict(orient="records"),
                    "total":len(results),"query":q,"suggested_queries":[]})

# ── ENDPOINT 10: CLUSTERS ─────────────────────────────────────────────────────
@app.route("/api/clusters")
def clusters():
    k = int(request.args.get("k",8))
    available = [5,8,12,20]
    k_actual = min(available, key=lambda x: abs(x-k))
    d = clust_data[str(k_actual)]
    return jsonify({
        "k_requested": k,
        "k_actual": k_actual,
        "cluster_count": d["cluster_count"],
        "noise_count": d["noise_count"],
        "cluster_labels": d["cluster_labels"],
        "points": [{"x":d["coords"][i][0],"y":d["coords"][i][1],
                    "cluster":d["labels"][i],"title":d["titles"][i],
                    "subreddit":d["subreddits"][i]}
                   for i in range(len(d["labels"]))]
    })

# ── ENDPOINT 11: NARRATIVE DIVERGENCE ─────────────────────────────────────────
@app.route("/api/narrative_divergence")
def narrative_divergence():
    q = request.args.get("q","").strip()
    if not q or len(q) < 2:
        return jsonify({"error":"Query too short","divergence":{},"total_relevant":0})

    q_emb = embed_model.encode([q]).astype("float32")
    faiss.normalize_L2(q_emb)
    D, I = index.search(q_emb, 300)

    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.25]
    results["created_utc"] = results["created_utc"].astype(str)

    divergence = {}
    for bloc in ["left_radical","center_left","right","mixed"]:
        bp = results[results["ideological_bloc"]==bloc]
        divergence[bloc] = (bp.nlargest(3,"similarity").to_dict(orient="records")
                            if len(bp) > 0 else [])

    return jsonify({"query":q,"divergence":divergence,"total_relevant":len(results)})

# ── ENDPOINT 12: INFORMATION VELOCITY ────────────────────────────────────────
@app.route("/api/velocity")
def velocity():
    q = request.args.get("q","").strip()
    if not q or len(q) < 2:
        return jsonify({"error":"Query too short","first_mover":None,"first_posts":[],"timeline":[]})

    q_emb = embed_model.encode([q]).astype("float32")
    faiss.normalize_L2(q_emb)
    D, I = index.search(q_emb, 300)

    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.3]

    if not len(results):
        return jsonify({"query":q,"first_mover":None,"first_posts":[],"timeline":[],"total":0})

    results["created_utc"] = pd.to_datetime(results["created_utc"])
    results = results.sort_values("created_utc")

    first_per_sub = (results.groupby("subreddit").first()
                     .reset_index().sort_values("created_utc"))
    first_per_sub["created_utc"] = first_per_sub["created_utc"].astype(str)

    results["date"] = results["created_utc"].dt.date.astype(str)
    timeline = (results.groupby(["date","subreddit"])
                .size().reset_index(name="count"))

    return jsonify({
        "query": q,
        "first_mover": first_per_sub.iloc[0]["subreddit"],
        "first_posts": first_per_sub[["subreddit","title","created_utc","similarity"]]
                       .to_dict(orient="records"),
        "timeline": timeline.to_dict(orient="records"),
        "total": len(results)
    })

# ── ENDPOINT 13: SUMMARIZE (Claude) ──────────────────────────────────────────
@app.route("/api/summarize", methods=["POST"])
def summarize():
    d = request.json
    ctype = d.get("type","timeseries")
    data = d.get("data",[])
    ctx = d.get("context","")
    if not data: return jsonify({"summary":"No data available to summarize."})
    prompt = (
        f"You are analyzing NarrativeTracker Reddit political data.\n"
        f"Chart type: {ctype}. Context: {ctx}.\n"
        f"Data (up to 30 points): {json.dumps(data[:30])}\n"
        f"Write 2-3 sentences in plain English for a non-technical audience.\n"
        f"Be specific: mention actual dates, subreddits, and numbers.\n"
        f"Do not start with 'This chart shows'."
    )
    return jsonify({"summary": claude(prompt, 200)})

# ── ENDPOINT 14: SUGGEST QUERIES (Claude) ────────────────────────────────────
@app.route("/api/suggest_queries", methods=["POST"])
def suggest_queries():
    d = request.json
    query = d.get("query","")
    titles = [r.get("title","") for r in d.get("results",[])[:5]]
    if not titles: return jsonify({"suggestions":[]})
    prompt = (
        f'User searched NarrativeTracker for: "{query}"\n'
        f"Top results were about: {titles}\n"
        f"Suggest exactly 3 related search queries they might explore next.\n"
        f"Return ONLY a JSON array of 3 short strings. No other text.\n"
        f'Example: ["query one", "query two", "query three"]'
    )
    try:
        text = claude(prompt, 100)
        suggestions = json.loads(text)
        return jsonify({"suggestions": suggestions[:3]})
    except:
        return jsonify({"suggestions":[]})

# ── ENDPOINT 15: NARRATIVE ANALYSIS (Claude) ─────────────────────────────────
@app.route("/api/narrative_analysis", methods=["POST"])
def narrative_analysis():
    blocs = request.json.get("blocs",{})
    query = request.json.get("query","")
    parts = {b:[p.get("title","") for p in posts]
             for b,posts in blocs.items() if posts}
    if not parts: return jsonify({"analysis":"No posts found to analyze."})
    prompt = (
        f"You are a political narrative analyst for NarrativeTracker.\n"
        f'Topic: "{query}"\n'
        f"Posts by community:\n{json.dumps(parts, indent=2)}\n"
        f"In 3-4 sentences, explain how the FRAMING of this topic differs\n"
        f"across these communities. Be specific about language, emphasis, and\n"
        f"implied blame or causation. Write for a research audience."
    )
    return jsonify({"analysis": claude(prompt, 300)})

# ── ENDPOINT 16: SOURCE BIAS NETWORK ─────────────────────────────────────────
@app.route("/api/source_network")
def source_network():
    min_w = int(request.args.get("min_weight",3))
    data = dict(net_src)
    data["edges"] = [e for e in data["edges"] if e.get("weight",0)>=min_w]
    return jsonify(data)

# ── ENDPOINT 17: NARRATIVE PROPAGATION ───────────────────────────────────────
@app.route("/api/propagation")
def propagation():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({"error": "Query too short", "posts": [], "subreddits": []})

    q_emb = embed_model.encode([q]).astype("float32")
    faiss.normalize_L2(q_emb)
    D, I = index.search(q_emb, 500)

    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.25]

    if not len(results):
        return jsonify({"query": q, "posts": [], "subreddits": []})

    results["created_utc"] = pd.to_datetime(results["created_utc"])
    results = results.sort_values("created_utc")
    results["created_utc"] = results["created_utc"].astype(str)

    posts = results[["subreddit","title","created_utc","similarity","ideological_bloc"]].to_dict(orient="records")
    subreddits = results.groupby("subreddit").agg(
        first_post=("created_utc","first"),
        count=("title","count"),
        bloc=("ideological_bloc","first")
    ).reset_index().sort_values("first_post").to_dict(orient="records")

    return jsonify({"query": q, "posts": posts, "subreddits": subreddits})


# ── ENDPOINT 18: COORDINATED AMPLIFICATION ────────────────────────────────────
@app.route("/api/coordinated")
def coordinated():
    q = request.args.get("q", "").strip()
    window_hours = int(request.args.get("window_hours", 6))
    min_authors = int(request.args.get("min_authors", 3))

    if not q or len(q) < 2:
        return jsonify({"error": "Query too short", "events": []})

    q_emb = embed_model.encode([q]).astype("float32")
    faiss.normalize_L2(q_emb)
    D, I = index.search(q_emb, 500)

    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.3]

    if not len(results):
        return jsonify({"query": q, "events": [], "total_posts": 0})

    results["created_utc"] = pd.to_datetime(results["created_utc"])
    results = results.sort_values("created_utc").reset_index(drop=True)

    window = pd.Timedelta(hours=window_hours)
    events = []

    for sub in results["subreddit"].unique():
        sub_posts = results[results["subreddit"] == sub].reset_index(drop=True)
        if len(sub_posts) < min_authors:
            continue
        i = 0
        while i < len(sub_posts):
            window_end = sub_posts.iloc[i]["created_utc"] + window
            cluster = sub_posts[
                (sub_posts["created_utc"] >= sub_posts.iloc[i]["created_utc"]) &
                (sub_posts["created_utc"] <= window_end)
            ]
            unique_authors = cluster["author"].nunique() if "author" in cluster.columns else len(cluster)
            if len(cluster) >= min_authors:
                cluster_copy = cluster.copy()
                cluster_copy["created_utc"] = cluster_copy["created_utc"].astype(str)
                events.append({
                    "subreddit": sub,
                    "bloc": sub_posts.iloc[0]["ideological_bloc"],
                    "window_start": str(sub_posts.iloc[i]["created_utc"]),
                    "window_end": str(window_end),
                    "post_count": len(cluster),
                    "unique_authors": int(unique_authors),
                    "posts": cluster_copy[["title","created_utc","similarity"]].head(5).to_dict(orient="records"),
                    "intensity": round(len(cluster) / window_hours, 2)
                })
                i += len(cluster)
            else:
                i += 1

    events.sort(key=lambda x: x["post_count"], reverse=True)
    return jsonify({
        "query": q,
        "window_hours": window_hours,
        "events": events[:20],
        "total_posts": len(results)
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)

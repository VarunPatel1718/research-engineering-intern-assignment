from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_compress import Compress
import pandas as pd, numpy as np, faiss, json, os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    "http://localhost:5173",
    "http://localhost:3000",
    "https://*.vercel.app",
])
Compress(app)

DATA = os.path.join(os.path.dirname(__file__), "../data")

# ── LOAD ALL DATA AT STARTUP ──────────────────────────────────────────────────
print("Loading data files...")
df    = pd.read_parquet(f"{DATA}/processed.parquet")
meta  = pd.read_parquet(f"{DATA}/search_meta.parquet")
index = faiss.read_index(f"{DATA}/faiss.index")

with open(f"{DATA}/network_subreddit.json") as f: net_sub  = json.load(f)
with open(f"{DATA}/network_author.json")    as f: net_auth = json.load(f)
with open(f"{DATA}/network_source.json")    as f: net_src  = json.load(f)
with open(f"{DATA}/events.json")            as f: evts     = json.load(f)
with open(f"{DATA}/clusters.json")          as f: clust    = json.load(f)

from sentence_transformers import SentenceTransformer
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

try:
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    AI_OK = True
    print("✓ Groq AI ready")
except Exception as e:
    AI_OK = False
    print(f"Groq not available: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PRECOMPUTE EVERYTHING AT STARTUP — all endpoints return in <50ms
# ══════════════════════════════════════════════════════════════════════════════
print("Pre-computing caches...")
_clean = df[~df["is_spam"]].copy()

# 1. Stats
_top = _clean.nlargest(1, "score").iloc[0]
_stats_json = json.dumps({
    "total_posts":      len(_clean),
    "total_authors":    int(_clean["author"].nunique()),
    "total_subreddits": int(_clean["subreddit"].nunique()),
    "date_start":       str(_clean["created_utc"].min()),
    "date_end":         str(_clean["created_utc"].max()),
    "spam_flagged":     int(df["is_spam"].sum()),
    "crosspost_count":  int(_clean["crosspost_parent"].notna().sum()),
    "avg_score":        round(float(_clean["score"].mean()), 1),
    "top_post": {
        "title":     _top["title"],
        "score":     int(_top["score"]),
        "subreddit": _top["subreddit"],
    }
})

# 2. Subreddits
_sc = df.groupby("subreddit").agg(
    count=("id", "count"),
    avg_score=("score", "mean"),
    subscribers=("subreddit_subscribers", "max"),
    bloc=("ideological_bloc", "first")
).reset_index()
_sc["avg_score"] = _sc["avg_score"].round(1)
_subreddits_json = json.dumps(_sc.to_dict(orient="records"))

# 3. Events
_events_json = json.dumps(evts)

# 4. Networks
_net_json = {
    "subreddit": json.dumps(net_sub),
    "author":    json.dumps(net_auth),
    "source":    json.dumps(net_src),
}

# 5. Clusters
_clusters_cache = {}
for _k in ["5", "8", "12", "20"]:
    _d = clust[_k]
    _clusters_cache[_k] = json.dumps({
        "k_requested":    int(_k),
        "k_actual":       int(_k),
        "cluster_count":  _d["cluster_count"],
        "noise_count":    _d["noise_count"],
        "cluster_labels": _d["cluster_labels"],
        "points": [
            {
                "x":         _d["coords"][i][0],
                "y":         _d["coords"][i][1],
                "cluster":   _d["labels"][i],
                "subreddit": _d["subreddits"][i],
                "title":     _d["titles"][i][:80],
            }
            for i in range(len(_d["labels"]))
        ],
    })

# 6. Timeseries — all subreddits × all granularities
print("Pre-computing timeseries cache...")
_ts_cache = {}

def _build_ts(sub, gran):
    data = _clean.copy()
    if sub != "all":
        data = data[data["subreddit"] == sub]
    if not len(data):
        return "[]"
    freq = "W" if gran == "week" else "D" if gran == "day" else "ME"
    ts = (
        data.set_index("created_utc").sort_index()
        .resample(freq)
        .agg(count=("id","count"), avg_score=("score","mean"),
             avg_comments=("num_comments","mean"))
        .reset_index()
    )
    ts["created_utc"] = ts["created_utc"].astype(str)
    return json.dumps(ts.fillna(0).round(2).to_dict(orient="records"))

for _sub in list(df["subreddit"].unique()) + ["all"]:
    for _gran in ["week", "day", "month"]:
        _ts_cache[f"{_sub}|{_gran}"] = _build_ts(_sub, _gran)
print(f"✓ Timeseries: {len(_ts_cache)} entries")

# 7. Timeseries by bloc
_blocs_cache = {}
for _gran, _freq in [("week","W"), ("day","D"), ("month","ME")]:
    _data = _clean.set_index("created_utc").sort_index()
    _res  = {}
    for _bloc in _data["ideological_bloc"].unique():
        _ts = (
            _data[_data["ideological_bloc"] == _bloc]
            .resample(_freq).agg(count=("id","count")).reset_index()
        )
        _ts["created_utc"] = _ts["created_utc"].astype(str)
        _res[_bloc] = _ts.to_dict(orient="records")
    _blocs_cache[_gran] = json.dumps(_res)
print("✓ Blocs timeseries: 3 granularities")

# 8. Source network default
_source_net_json = json.dumps({
    "nodes": net_src["nodes"],
    "edges": [e for e in net_src["edges"] if e.get("weight", 0) >= 3],
})

# 9. Embedding cache — same query never re-embeds
_embed_cache = {}
def get_embedding(q):
    if q not in _embed_cache:
        emb = embed_model.encode([q]).astype("float32")
        faiss.normalize_L2(emb)
        _embed_cache[q] = emb
    return _embed_cache[q]

# ── WOW 1: PROPAGATION — node positions precomputed ──────────────────────────
NODE_POS = {
    "Anarchism":           {"x": 0.1, "y": 0.3},
    "socialism":           {"x": 0.1, "y": 0.7},
    "Liberal":             {"x": 0.3, "y": 0.2},
    "democrats":           {"x": 0.3, "y": 0.5},
    "politics":            {"x": 0.3, "y": 0.8},
    "neoliberal":          {"x": 0.5, "y": 0.3},
    "PoliticalDiscussion": {"x": 0.5, "y": 0.7},
    "Conservative":        {"x": 0.7, "y": 0.2},
    "Republican":          {"x": 0.7, "y": 0.6},
    "worldpolitics":       {"x": 0.9, "y": 0.4},
}
print("✓ Propagation node positions ready")

# ── WOW 2: COORDINATION DETECTOR — fully precomputed ─────────────────────────
print("Pre-computing coordination events...")
_clean_coord = _clean.copy()
_clean_coord["created_utc"] = pd.to_datetime(_clean_coord["created_utc"])
_clean_coord = _clean_coord.sort_values("created_utc")
_clean_coord["window"] = _clean_coord["created_utc"].dt.floor("6H")

_coord_events = []
_heatmap      = []

for (_window, _sub), _group in _clean_coord.groupby(["window", "subreddit"]):
    if len(_group) < 4:
        continue
    _sub_total = len(_clean_coord[_clean_coord["subreddit"] == _sub])
    _total_windows = max(1, (
        _clean_coord["created_utc"].max() -
        _clean_coord["created_utc"].min()
    ).total_seconds() / 3600 / 6)
    _avg   = _sub_total / _total_windows
    _burst = min(99, round((len(_group) / max(_avg, 0.1)) * 10, 1))
    if _burst < 15:
        continue

    _unique   = _group["author"].nunique()
    _top_auth = _group["author"].value_counts().head(3).to_dict()
    _samples  = _group.nlargest(3, "score")["title"].tolist()

    if _unique == 1:
        _pat = "SINGLE_ACTOR_FLOOD"
        _lbl = "Single actor flood ⚠️"
    elif _unique <= 3:
        _pat = "SMALL_GROUP_BURST"
        _lbl = "Small group burst"
    elif _burst > 50:
        _pat = "MASS_SYNCHRONIZED_BURST"
        _lbl = "Mass synchronized burst 🔴"
    else:
        _pat = "ORGANIC_NEWS_RESPONSE"
        _lbl = "Organic news response ✓"

    _coord_events.append({
        "window":           str(_window),
        "subreddit":        _sub,
        "ideological_bloc": _group["ideological_bloc"].iloc[0],
        "post_count":       len(_group),
        "unique_authors":   int(_unique),
        "burst_score":      _burst,
        "pattern":          _pat,
        "label":            _lbl,
        "top_authors":      _top_auth,
        "sample_titles":    _samples,
        "permalink_sample": _group.iloc[0]["permalink"],
    })
    _heatmap.append({
        "window":      str(_window),
        "subreddit":   _sub,
        "burst_score": _burst,
        "post_count":  len(_group),
        "pattern":     _pat,
    })

_cross_bursts = defaultdict(list)
for _e in _coord_events:
    _cross_bursts[_e["window"]].append(_e)

_synchronized = sorted([
    {
        "window":      w,
        "communities": [e["subreddit"] for e in ev],
        "total_posts": sum(e["post_count"] for e in ev),
        "avg_burst":   round(sum(e["burst_score"] for e in ev) / len(ev), 1),
        "blocs":       list(set(e["ideological_bloc"] for e in ev)),
        "pattern":     "CROSS_COMMUNITY_SYNCHRONIZED",
    }
    for w, ev in _cross_bursts.items() if len(ev) >= 3
], key=lambda x: x["avg_burst"], reverse=True)[:10]

_coordination_json = json.dumps({
    "top_events":   sorted(_coord_events,
                           key=lambda x: x["burst_score"],
                           reverse=True)[:20],
    "heatmap":      _heatmap,
    "synchronized": _synchronized,
    "total_events": len(_coord_events),
    "window_hours": 6,
})
print(f"✓ Coordination: {len(_coord_events)} burst events detected")
print(f"✓ Ready — {len(df)} posts loaded. AI={AI_OK}")


# ── AI HELPER ─────────────────────────────────────────────────────────────────
def ai(prompt, max_tokens=200):
    if not AI_OK:
        return "AI summary unavailable — configure GROQ_API_KEY in .env"
    try:
        r = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return r.choices[0].message.content
    except Exception as e:
        return f"AI temporarily unavailable: {str(e)[:80]}"


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/health")
def health():
    return jsonify({
        "status":      "ok",
        "total_posts": len(df),
        "date_start":  str(df["created_utc"].min()),
        "date_end":    str(df["created_utc"].max()),
    })

@app.route("/api/stats")
def stats():
    return Response(_stats_json, mimetype="application/json")

@app.route("/api/subreddits")
def subreddits():
    return Response(_subreddits_json, mimetype="application/json")

@app.route("/api/timeseries")
def timeseries():
    sub  = request.args.get("subreddit", "all")
    gran = request.args.get("granularity", "week")
    key  = f"{sub}|{gran}"
    return Response(
        _ts_cache.get(key, _ts_cache.get(f"all|{gran}", "[]")),
        mimetype="application/json"
    )

@app.route("/api/timeseries/blocs")
def timeseries_blocs():
    gran = request.args.get("granularity", "week")
    return Response(
        _blocs_cache.get(gran, _blocs_cache["week"]),
        mimetype="application/json"
    )

@app.route("/api/events")
def events():
    return Response(_events_json, mimetype="application/json")

@app.route("/api/topdomain")
def topdomain():
    sub  = request.args.get("subreddit", "all")
    data = df[~df["is_self_post"] & (df["domain"] != "") & ~df["is_spam"]].copy()
    if sub != "all":
        data = data[data["subreddit"] == sub]
    counts = data["domain"].value_counts().head(15).reset_index()
    counts.columns = ["domain", "count"]
    L = {"theguardian.com", "nytimes.com", "huffpost.com"}
    R = {"foxnews.com", "breitbart.com", "nypost.com", "townhall.com"}
    counts["bias"] = counts["domain"].apply(
        lambda d: "left" if d in L else "right" if d in R else "center"
    )
    return jsonify(counts.to_dict(orient="records"))

@app.route("/api/network")
def network():
    ntype  = request.args.get("type", "subreddit")
    remove = request.args.get("remove_node", None)
    if ntype == "subreddit": base = net_sub
    elif ntype == "author":  base = net_auth
    else:                    base = net_src
    if remove:
        return jsonify({
            "nodes": [n for n in base["nodes"] if n["id"] != remove],
            "edges": [e for e in base["edges"]
                      if e["source"] != remove and e["target"] != remove],
        })
    return Response(_net_json[ntype], mimetype="application/json")

@app.route("/api/search")
def search():
    q    = request.args.get("q", "").strip()
    lim  = min(int(request.args.get("limit", 20)), 50)
    sub  = request.args.get("subreddit", "all")
    bloc = request.args.get("bloc", "all")

    if not q or len(q) < 2:
        return jsonify({
            "results": [], "total": 0, "query": q,
            "suggested_queries": [],
            "warning": "Query too short — enter at least 2 characters",
        })

    q_emb   = get_embedding(q)
    D, I    = index.search(q_emb, lim * 4)
    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.2]
    if sub  != "all": results = results[results["subreddit"] == sub]
    if bloc != "all": results = results[results["ideological_bloc"] == bloc]
    results = results.head(lim)
    results["created_utc"] = results["created_utc"].astype(str)

    return jsonify({
        "results": results.to_dict(orient="records"),
        "total":   len(results),
        "query":   q,
        "suggested_queries": [],
    })

@app.route("/api/clusters")
def clusters():
    k        = int(request.args.get("k", 8))
    k_actual = min([5, 8, 12, 20], key=lambda x: abs(x - k))
    data     = json.loads(_clusters_cache[str(k_actual)])
    data["k_requested"] = k
    return jsonify(data)

@app.route("/api/narrative_divergence")
def narrative_divergence():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({
            "error": "Query too short",
            "divergence": {},
            "total_relevant": 0,
        })
    q_emb   = get_embedding(q)
    D, I    = index.search(q_emb, 300)
    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.25]
    results["created_utc"] = results["created_utc"].astype(str)
    divergence = {}
    for bloc in ["left_radical", "center_left", "right", "mixed"]:
        bp = results[results["ideological_bloc"] == bloc]
        divergence[bloc] = (
            bp.nlargest(3, "similarity").to_dict(orient="records")
            if len(bp) > 0 else []
        )
    return jsonify({
        "query":          q,
        "divergence":     divergence,
        "total_relevant": len(results),
    })

@app.route("/api/summarize", methods=["POST"])
def summarize():
    d     = request.json
    data  = d.get("data", [])
    ctx   = d.get("context", "")
    ctype = d.get("type", "timeseries")
    if not data:
        return jsonify({"summary": "No data available to summarize."})
    prompt = (
        f"Analyzing NarrativeTrail Reddit political data.\n"
        f"Chart: {ctype}. Context: {ctx}.\n"
        f"Data: {json.dumps(data[:30])}\n"
        f"Write 2-3 plain-English sentences for a non-technical audience. "
        f"Mention actual dates, subreddits, and numbers. "
        f"Do not start with 'This chart shows'."
    )
    return jsonify({"summary": ai(prompt, 200)})

@app.route("/api/suggest_queries", methods=["POST"])
def suggest_queries():
    d      = request.json
    query  = d.get("query", "")
    titles = [r.get("title", "") for r in d.get("results", [])[:5]]
    if not titles:
        return jsonify({"suggestions": []})
    prompt = (
        f'User searched NarrativeTrail for: "{query}"\n'
        f"Top results: {titles}\n"
        f"Suggest exactly 3 related queries. "
        f"Return ONLY a JSON array of 3 short strings. No other text."
    )
    try:
        text = ai(prompt, 100).strip()
        if not text.startswith("["):
            text = text[text.find("["):text.rfind("]") + 1]
        return jsonify({"suggestions": json.loads(text)[:3]})
    except Exception:
        return jsonify({"suggestions": []})

@app.route("/api/narrative_analysis", methods=["POST"])
def narrative_analysis():
    blocs = request.json.get("blocs", {})
    query = request.json.get("query", "")
    parts = {
        b: [p.get("title", "") for p in posts]
        for b, posts in blocs.items() if posts
    }
    if not parts:
        return jsonify({"analysis": "No posts found to analyze."})
    prompt = (
        f"Political narrative analyst for NarrativeTrail.\n"
        f'Topic: "{query}"\n'
        f"Posts by community:\n{json.dumps(parts, indent=2)}\n"
        f"In 3-4 sentences explain how FRAMING differs across communities. "
        f"Be specific about language, emphasis, and implied causation."
    )
    return jsonify({"analysis": ai(prompt, 300)})

@app.route("/api/source_network")
def source_network():
    min_w = int(request.args.get("min_weight", 3))
    if min_w == 3:
        return Response(_source_net_json, mimetype="application/json")
    return jsonify({
        "nodes": net_src["nodes"],
        "edges": [e for e in net_src["edges"] if e.get("weight", 0) >= min_w],
    })

# ── WOW 1: NARRATIVE PROPAGATION ANIMATOR ────────────────────────────────────
@app.route("/api/propagation")
def propagation():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({
            "error": "Query too short",
            "sequence": [], "nodes": [], "total": 0,
        })

    q_emb   = get_embedding(q)
    D, I    = index.search(q_emb, 500)
    results = meta.iloc[I[0]].copy()
    results["similarity"] = D[0]
    results = results[results["similarity"] > 0.25].copy()

    if not len(results):
        return jsonify({
            "query": q, "sequence": [], "nodes": [],
            "timeline": [], "total": 0,
        })

    results["created_utc"] = pd.to_datetime(results["created_utc"])
    results = results.sort_values("created_utc")

    first = (
        results.groupby("subreddit").first()
        .reset_index()
        .sort_values("created_utc")
    )
    t0 = first.iloc[0]["created_utc"]

    sequence = []
    for _, row in first.iterrows():
        hours = round((row["created_utc"] - t0).total_seconds() / 3600, 1)
        pos   = NODE_POS.get(row["subreddit"], {"x": 0.5, "y": 0.5})
        sequence.append({
            "subreddit":        row["subreddit"],
            "title":            row["title"][:100],
            "created_utc":      str(row["created_utc"]),
            "hours_after":      hours,
            "similarity":       round(float(row["similarity"]), 3),
            "permalink":        row.get("permalink", ""),
            "ideological_bloc": row.get("ideological_bloc", "other"),
            "x":                pos["x"],
            "y":                pos["y"],
        })

    results["date"] = results["created_utc"].dt.date.astype(str)
    timeline = (
        results.groupby(["date", "subreddit"])
        .size().reset_index(name="count")
        .to_dict(orient="records")
    )

    return jsonify({
        "query":       q,
        "first_mover": sequence[0]["subreddit"],
        "sequence":    sequence,
        "timeline":    timeline,
        "total":       len(results),
    })

# ── WOW 2: COORDINATED AMPLIFICATION DETECTOR ────────────────────────────────
@app.route("/api/coordination")
def coordination():
    pattern = request.args.get("pattern", "all")
    data    = json.loads(_coordination_json)
    if pattern != "all":
        data["top_events"] = [
            e for e in data["top_events"]
            if e["pattern"] == pattern
        ]
    return Response(json.dumps(data), mimetype="application/json")


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)
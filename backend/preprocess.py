"""
preprocess.py
Run FIRST. Reads data.jsonl, cleans, adds derived fields, saves processed.parquet + meta.parquet.
"""
import json, pandas as pd, os, sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
INPUT    = os.path.join(DATA_DIR, "data.jsonl")
OUT      = DATA_DIR

if not os.path.exists(INPUT):
    sys.exit(f"ERROR: {INPUT} not found. Place data.jsonl in the data/ folder.")

# ── Constants ─────────────────────────────────────────────────────────────────
SPAM_FLAIRS = {
    "( Y )❤️ Tifa Lockhart ❤️( o )( o )",
    "tf2", "🍄Princess🍑", "plant gang🌱", "UPAM🌐"
}
LEFT_SRC   = {"theguardian.com","nytimes.com","msnbc.com","huffpost.com",
              "jacobin.com","motherjones.com","theintercept.com"}
RIGHT_SRC  = {"foxnews.com","breitbart.com","nypost.com","townhall.com",
              "dailywire.com","washingtonexaminer.com","oann.com"}
CENTER_SRC = {"apnews.com","reuters.com","politico.com","nbcnews.com",
              "thehill.com","cnn.com","newsweek.com","axios.com","bbc.com"}

LEFT_S  = {"Anarchism","socialism"}
CLEFT_S = {"Liberal","democrats","politics","neoliberal","PoliticalDiscussion"}
RIGHT_S = {"Conservative","Republican"}

# ── Parse ─────────────────────────────────────────────────────────────────────
records = []
skipped = 0

with open(INPUT, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            d   = obj.get("data", {})

            cpl    = d.get("crosspost_parent_list") or []
            cp_sub = cpl[0].get("subreddit") if cpl else None

            title    = (d.get("title")    or "").strip()
            selftext = (d.get("selftext") or "").strip()
            if selftext in ["[removed]","[deleted]"]:
                selftext = ""
            text   = f"{title} {selftext}".strip()
            domain = (d.get("domain") or "").strip()
            sub    = d.get("subreddit", "")
            flair  = (d.get("author_flair_text") or "").strip()

            records.append({
                "id":                          d.get("id"),
                "subreddit":                   sub,
                "author":                      d.get("author"),
                "title":                       title,
                "selftext":                    selftext,
                "text":                        text,
                "score":                       int(d.get("score")        or 0),
                "num_comments":                int(d.get("num_comments") or 0),
                "upvote_ratio":                float(d.get("upvote_ratio") or 0),
                "created_utc":                 d.get("created_utc"),
                "domain":                      domain,
                "url":                         (d.get("url_overridden_by_dest") or d.get("url") or "").strip(),
                "num_crossposts":              int(d.get("num_crossposts") or 0),
                "crosspost_parent":            d.get("crosspost_parent"),
                "crosspost_parent_subreddit":  cp_sub,
                "author_flair":                flair,
                "permalink":                   (d.get("permalink") or "").strip(),
                "is_self":                     bool(d.get("is_self", True)),
                "subreddit_subscribers":       int(d.get("subreddit_subscribers") or 0),
                "is_spam":                     flair in SPAM_FLAIRS,
                "is_self_post":                (domain.startswith("self.") or bool(d.get("is_self"))),
                "source_bias": (
                    "left"   if domain in LEFT_SRC  else
                    "right"  if domain in RIGHT_SRC else
                    "center" if domain in CENTER_SRC else
                    "self"   if domain.startswith("self.") else "other"
                ),
                "ideological_bloc": (
                    "left_radical" if sub in LEFT_S  else
                    "center_left"  if sub in CLEFT_S else
                    "right"        if sub in RIGHT_S else "mixed"
                ),
            })
        except Exception as e:
            skipped += 1
            continue

print(f"Parsed {len(records)} records, skipped {skipped}")

# ── Clean ─────────────────────────────────────────────────────────────────────
df = pd.DataFrame(records)
df["created_utc"] = pd.to_datetime(df["created_utc"], unit="s", errors="coerce")
df = df[~df["author"].isin(["AutoModerator","[deleted]",None])]
df = df.dropna(subset=["created_utc","id","subreddit"])
df = df.drop_duplicates(subset=["id"])
df = df[df["text"].str.len() >= 5]
df["year_week"]  = df["created_utc"].dt.to_period("W").astype(str)
df["year_month"] = df["created_utc"].dt.to_period("M").astype(str)
df["date"]       = df["created_utc"].dt.date.astype(str)

os.makedirs(OUT, exist_ok=True)
df.to_parquet(f"{OUT}/processed.parquet", index=False)

df[[
    "id","title","subreddit","author","created_utc","score","num_comments",
    "permalink","domain","url","ideological_bloc","source_bias","author_flair","is_spam"
]].to_parquet(f"{OUT}/meta.parquet", index=False)

print(f"✓ Total clean records : {len(df)}")
print(df["subreddit"].value_counts().to_string())
print(f"✓ Spam flagged        : {df['is_spam'].sum()}")
print(f"✓ Saved processed.parquet and meta.parquet → {OUT}/")
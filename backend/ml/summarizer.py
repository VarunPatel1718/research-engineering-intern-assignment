# backend/ml/summarizer.py

import os
from dotenv import load_dotenv
load_dotenv()

def get_client():
    try:
        from groq import Groq
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            print("GROQ_API_KEY not found in .env")
            return None
        return Groq(api_key=api_key)
    except Exception as e:
        print(f"Groq client error: {e}")
        return None

def generate_text(prompt: str, max_tokens: int = 150) -> str:
    """Generate text using Groq. Falls back to rule-based if unavailable."""
    client = get_client()
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return None

def summarize_timeline(query: str, data: list) -> str:
    if not data:
        return "No data found for this query."

    total = sum(r['post_count'] for r in data)
    peak  = max(data, key=lambda x: x['post_count'])

    sub_totals: dict = {}
    for r in data:
        sub_totals[r['subreddit']] = sub_totals.get(r['subreddit'], 0) + r['post_count']
    top_sub = max(sub_totals, key=lambda x: sub_totals[x])

    prompt = f"""You are analyzing Reddit political data for a research dashboard called NarrativeTrail.

Query topic: "{query or 'all posts'}"
Total posts found: {total}
Date range: {data[0]['week']} to {data[-1]['week']}
Peak activity: week of {peak['week']} on r/{peak['subreddit']} with {peak['post_count']} posts
Most active community: r/{top_sub} with {sub_totals[top_sub]} posts
All communities in results: {list(sub_totals.keys())}

Write exactly 2 sentences of analytical insight about what this timeline data reveals
about how this topic traveled across the political spectrum. Be specific about which
communities engaged most and what the timing suggests about narrative spread.
Do not use bullet points. Just 2 sentences."""

    result = generate_text(prompt, 150)
    if result:
        return result
    return fallback_timeline_summary(query, data)

def summarize_search(query: str, results: list) -> str:
    if not results:
        return "No results found for this query."

    subreddits = [r['subreddit'] for r in results[:10]]
    sub_counts: dict = {}
    for s in subreddits:
        sub_counts[s] = sub_counts.get(s, 0) + 1
    top_result = results[0]

    prompt = f"""You are analyzing Reddit political data for a research dashboard.

Semantic search query: "{query}"
Top result title: "{top_result['title']}"
Top result from: r/{top_result['subreddit']} (score: {top_result['score']})
Subreddits appearing in results: {dict(sorted(sub_counts.items(), key=lambda x: x[1], reverse=True))}

Write exactly 2 sentences analyzing what these search results reveal about how
different political communities discuss this topic. Note any ideological framing
differences between left-leaning and right-leaning subreddits.
Just 2 sentences, no bullet points."""

    result = generate_text(prompt, 150)
    if result:
        return result
    return fallback_search_summary(query, results)

def summarize_network(stats: dict) -> str:
    top = stats.get('top_influencers', [])
    if not top:
        return "Network data unavailable."

    prompt = f"""You are analyzing a Reddit political influence network.

Network statistics:
- Total authors tracked: {stats['total_nodes']}
- Crosspost connections: {stats['total_edges']}
- Ideological communities detected: {stats['num_communities']}
- Top 3 influencers by PageRank: {[f"u/{n['author']} from r/{n['subreddit']}" for n in top[:3]]}

Write exactly 2 sentences about what this network structure reveals about
how political narratives spread across ideological communities on Reddit.
Focus on which accounts bridge different political groups.
Just 2 sentences, no bullet points."""

    result = generate_text(prompt, 150)
    if result:
        return result
    return fallback_network_summary(stats)

def summarize_clusters(topic_info: list, nr_topics: int) -> str:
    valid = [t for t in topic_info if t['Topic'] != -1][:5]
    if not valid:
        return "No clusters found."

    prompt = f"""You are analyzing BERTopic clusters from Reddit political posts
spanning far-left to far-right during the US 2024 election period.

Number of clusters: {nr_topics}
Top topic themes found:
{chr(10).join([f"- {t.get('Label', t['Name'])}: {t['Count']} posts" for t in valid])}

Write exactly 2 sentences about what these topic clusters reveal about
the dominant political narratives in this dataset during the 2024 election period.
Just 2 sentences, no bullet points."""

    result = generate_text(prompt, 150)
    if result:
        return result
    return fallback_cluster_summary(topic_info, nr_topics)

def generate_topic_labels(topic_info: list) -> dict:
    """Use Groq to generate human-readable topic labels."""
    topics = [t for t in topic_info if t['Topic'] != -1][:10]
    if not topics:
        return {}

    topic_text = '\n'.join([
        f"Topic {t['Topic']}: keywords = {t['Name']} ({t['Count']} posts)"
        for t in topics
    ])

    prompt = f"""You are analyzing Reddit political posts from 10 subreddits spanning
far-left to far-right during the US 2024 election period.

These are BERTopic clusters with raw keyword representations:
{topic_text}

For each topic number, generate a short human-readable label (3-5 words)
describing the political theme.

Good label examples: "Immigration & Deportation", "Election Integrity",
"Economic Policy", "Gun Control", "Healthcare Reform"

Respond ONLY with valid JSON like this exact format:
{{"0": "Immigration Policy", "1": "Election Results", "2": "Economic Debate"}}

No explanation. No markdown. No code blocks. Just the JSON object."""

    result = generate_text(prompt, 300)
    if not result:
        return {}

    try:
        import json
        clean = result.strip()
        if '```' in clean:
            clean = clean.split('```')[1]
            if clean.startswith('json'):
                clean = clean[4:]
        if '{' in clean:
            start = clean.index('{')
            end = clean.rindex('}') + 1
            clean = clean[start:end]
        return json.loads(clean.strip())
    except Exception as e:
        print(f"Label parsing failed: {e}, raw: {result}")
        return {}

# ── Fallbacks ─────────────────────────────────────────────

def fallback_timeline_summary(query, data):
    if not data:
        return "No data found."
    total = sum(r['post_count'] for r in data)
    peak = max(data, key=lambda x: x['post_count'])
    sub_totals: dict = {}
    for r in data:
        sub_totals[r['subreddit']] = sub_totals.get(r['subreddit'], 0) + r['post_count']
    top_sub = max(sub_totals, key=lambda x: sub_totals[x])
    return (f"Found {total} posts about '{query or 'all topics'}' across "
            f"{len(sub_totals)} communities. Peak activity was week of "
            f"{peak['week']} on r/{peak['subreddit']} with {peak['post_count']} posts. "
            f"Most active community overall: r/{top_sub}.")

def fallback_search_summary(query, results):
    if not results:
        return "No results found."
    subs = list(set(r['subreddit'] for r in results[:5]))
    return (f"Found {len(results)} semantically similar posts about '{query}' "
            f"across r/{', r/'.join(subs[:3])} and more communities.")

def fallback_network_summary(stats):
    top = stats.get('top_influencers', [])
    if not top:
        return "Network built from crosspost relationships between authors."
    return (f"Influence network of {stats['total_nodes']} authors with "
            f"{stats['total_edges']} crosspost connections across "
            f"{stats['num_communities']} detected communities. "
            f"Top influencer: u/{top[0]['author']} from r/{top[0]['subreddit']}.")

def fallback_cluster_summary(topic_info, nr_topics):
    valid = [t for t in topic_info if t['Topic'] != -1]
    if not valid:
        return "Clustering complete."
    return (f"BERTopic identified {len(valid)} narrative clusters from 8,567 posts. "
            f"Largest cluster: '{valid[0].get('Label', valid[0]['Name'])}' "
            f"with {valid[0]['Count']} posts ({(valid[0]['Count']/8567*100):.1f}% of dataset).")
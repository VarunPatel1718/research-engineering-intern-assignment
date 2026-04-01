# backend/ml/summarizer.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from dotenv import load_dotenv
load_dotenv()

def get_client():
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

def summarize_timeline(query: str, data: list) -> str:
    """Generate dynamic insight for timeline chart."""
    client = get_client()
    if not client:
        return fallback_timeline_summary(query, data)

    if not data:
        return "No data found for this query."

    total = sum(r['post_count'] for r in data)
    peak = max(data, key=lambda x: x['post_count'])

    # Find subreddit with most posts
    sub_totals: dict = {}
    for r in data:
        sub_totals[r['subreddit']] = sub_totals.get(r['subreddit'], 0) + r['post_count']
    top_sub = max(sub_totals, key=lambda x: sub_totals[x])

    prompt = f"""You are analyzing Reddit political data for a research dashboard.

Query: "{query or 'all posts'}"
Total posts found: {total}
Date range: {data[0]['week']} to {data[-1]['week']}
Peak activity: week of {peak['week']} on r/{peak['subreddit']} with {peak['post_count']} posts
Most active community: r/{top_sub} with {sub_totals[top_sub]} posts

Write a 2-sentence analytical insight about what this timeline data reveals about how 
this topic traveled across the political spectrum. Be specific about the communities 
and timing. Focus on narrative framing differences between left and right subreddits."""

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return fallback_timeline_summary(query, data)

def summarize_search(query: str, results: list) -> str:
    """Generate dynamic insight for search results."""
    client = get_client()
    if not client:
        return fallback_search_summary(query, results)

    if not results:
        return "No results found for this query."

    subreddits = [r['subreddit'] for r in results[:10]]
    sub_counts: dict = {}
    for s in subreddits:
        sub_counts[s] = sub_counts.get(s, 0) + 1

    top_result = results[0]

    prompt = f"""You are analyzing Reddit political data for a research dashboard.

Semantic search query: "{query}"
Top result: "{top_result['title']}" from r/{top_result['subreddit']} (score: {top_result['score']})
Subreddits in results: {dict(sorted(sub_counts.items(), key=lambda x: x[1], reverse=True))}

Write 2 sentences analyzing what these search results reveal about how different 
political communities discuss this topic. Note any ideological framing differences."""

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return fallback_search_summary(query, results)

def summarize_network(stats: dict) -> str:
    """Generate dynamic insight for network graph."""
    client = get_client()
    if not client:
        return fallback_network_summary(stats)

    top = stats.get('top_influencers', [])
    if not top:
        return "Network data unavailable."

    prompt = f"""You are analyzing a Reddit political influence network.

Network stats:
- Total authors: {stats['total_nodes']}
- Crosspost edges: {stats['total_edges']}  
- Communities detected: {stats['num_communities']}
- Top influencers by PageRank: {[f"{n['author']} (r/{n['subreddit']})" for n in top[:3]]}

Write 2 sentences about what this network reveals about how narratives spread 
across political communities. Which accounts act as bridges between ideological groups?"""

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return fallback_network_summary(stats)

def summarize_clusters(topic_info: list, nr_topics: int) -> str:
    """Generate dynamic insight for topic clusters."""
    client = get_client()
    if not client:
        return fallback_cluster_summary(topic_info, nr_topics)

    topics = [t for t in topic_info if t['Topic'] != -1][:5]

    prompt = f"""You are analyzing BERTopic clusters from Reddit political posts.

Number of clusters requested: {nr_topics}
Top topics found:
{chr(10).join([f"- Topic {t['Topic']}: {t['Name']} ({t['Count']} posts)" for t in topics])}

Write 2 sentences about what these topic clusters reveal about the dominant 
political narratives in this dataset. What themes emerge across the spectrum?"""

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return fallback_cluster_summary(topic_info, nr_topics)

# Fallbacks when no API key
def fallback_timeline_summary(query, data):
    if not data:
        return "No data found."
    total = sum(r['post_count'] for r in data)
    peak = max(data, key=lambda x: x['post_count'])
    return f"Found {total} posts matching '{query or 'all posts'}'. Peak activity was in week of {peak['week']} on r/{peak['subreddit']} with {peak['post_count']} posts."

def fallback_search_summary(query, results):
    if not results:
        return "No results found."
    subs = list(set(r['subreddit'] for r in results[:5]))
    return f"Found {len(results)} semantically similar posts about '{query}' across {', '.join(subs[:3])} and more."

def fallback_network_summary(stats):
    top = stats.get('top_influencers', [])
    if not top:
        return "Network built from crosspost relationships."
    return f"Network of {stats['total_nodes']} authors with {stats['total_edges']} crosspost edges. Top influencer: u/{top[0]['author']} from r/{top[0]['subreddit']}."

def fallback_cluster_summary(topic_info, nr_topics):
    valid = [t for t in topic_info if t['Topic'] != -1]
    return f"BERTopic identified {len(valid)} topic clusters from 8,567 posts. Largest cluster: '{valid[0]['Name'] if valid else 'N/A'}' with {valid[0]['Count'] if valid else 0} posts."

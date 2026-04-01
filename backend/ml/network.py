# backend/ml/network.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import networkx as nx
import community as community_louvain
import json
from data.database import get_connection

def build_network():
    """Build author network with PageRank + Louvain community detection."""
    con = get_connection()

    # Get top authors
    authors_df = con.execute("""
        SELECT 
            author,
            subreddit,
            COUNT(*) as post_count,
            SUM(score) as total_score
        FROM posts
        WHERE author != '' 
          AND author != '[deleted]' 
          AND author != 'AutoModerator'
        GROUP BY author, subreddit
        ORDER BY post_count DESC
        LIMIT 200
    """).fetchdf()

    # Get crosspost edges
    edges_df = con.execute("""
        SELECT 
            p1.author as source,
            p2.author as target,
            p1.subreddit as source_subreddit,
            p2.subreddit as target_subreddit,
            p1.score as weight
        FROM posts p1
        JOIN posts p2 ON p1.crosspost_parent = 't3_' || p2.id
        WHERE p1.crosspost_parent != ''
          AND p1.author != ''
          AND p2.author != ''
          AND p1.author != '[deleted]'
          AND p2.author != '[deleted]'
    """).fetchdf()

    # Build directed graph
    G = nx.DiGraph()

    # Add nodes
    for _, row in authors_df.iterrows():
        G.add_node(row['author'], 
                   subreddit=row['subreddit'],
                   post_count=int(row['post_count']),
                   total_score=int(row['total_score']))

    # Add edges
    for _, row in edges_df.iterrows():
        if G.has_node(row['source']) and G.has_node(row['target']):
            G.add_edge(row['source'], row['target'], 
                      weight=max(1, int(row['weight'])))

    # PageRank
    pagerank = nx.pagerank(G, alpha=0.85, max_iter=100)

    # Louvain community detection (on undirected version)
    G_undirected = G.to_undirected()
    if len(G_undirected.edges()) > 0:
        partition = community_louvain.best_partition(G_undirected)
    else:
        partition = {node: 0 for node in G.nodes()}

    # Betweenness centrality (top bridge nodes)
    if len(G.nodes()) > 0:
        betweenness = nx.betweenness_centrality(G, normalized=True)
    else:
        betweenness = {node: 0 for node in G.nodes()}

    # Assemble nodes
    nodes = []
    for node in G.nodes():
        data = G.nodes[node]
        nodes.append({
            'author': node,
            'subreddit': data.get('subreddit', ''),
            'post_count': data.get('post_count', 0),
            'total_score': data.get('total_score', 0),
            'pagerank': round(pagerank.get(node, 0), 6),
            'community': partition.get(node, 0),
            'betweenness': round(betweenness.get(node, 0), 6),
        })

    # Sort by pagerank
    nodes.sort(key=lambda x: x['pagerank'], reverse=True)

    # Assemble edges
    edges = []
    for source, target, data in G.edges(data=True):
        edges.append({
            'source': source,
            'target': target,
            'weight': data.get('weight', 1),
        })

    # Summary stats
    top_nodes = nodes[:5]
    num_communities = len(set(partition.values()))

    result = {
        'nodes': nodes,
        'edges': edges,
        'stats': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'num_communities': num_communities,
            'top_influencers': [
                {'author': n['author'], 'subreddit': n['subreddit'], 
                 'pagerank': n['pagerank'], 'post_count': n['post_count']}
                for n in top_nodes
            ]
        }
    }

    return result

if __name__ == '__main__':
    result = build_network()
    print(f"Nodes: {result['stats']['total_nodes']}")
    print(f"Edges: {result['stats']['total_edges']}")
    print(f"Communities: {result['stats']['num_communities']}")
    print("Top influencers by PageRank:")
    for n in result['stats']['top_influencers']:
        print(f"  {n['author']} ({n['subreddit']}) — PageRank: {n['pagerank']}")
import pandas as pd, networkx as nx, json, os
from community import best_partition
from collections import defaultdict

DATA = os.path.join(os.path.dirname(__file__), "../data")
df   = pd.read_parquet(f"{DATA}/processed.parquet")
print(f"Building networks from {len(df)} posts...")

BLOC = {
    "Anarchism":"left_radical","socialism":"left_radical",
    "Liberal":"center_left","democrats":"center_left","politics":"center_left",
    "neoliberal":"center_left","PoliticalDiscussion":"center_left",
    "Conservative":"right","Republican":"right","worldpolitics":"mixed"
}

# ── 1. SUBREDDIT CROSSPOST NETWORK ──────────────────────────────────────────
cross = df[df["crosspost_parent_subreddit"].notna()].copy()
G = nx.DiGraph()
for _, row in cross.iterrows():
    s, t = row["crosspost_parent_subreddit"], row["subreddit"]
    if G.has_edge(s, t): G[s][t]["weight"] += 1
    else: G.add_edge(s, t, weight=1)
for sub in df["subreddit"].unique():
    if sub not in G: G.add_node(sub)
pr = nx.pagerank(G, weight="weight")
nx.set_node_attributes(G, pr, "pagerank")
pc = df["subreddit"].value_counts().to_dict()
nx.set_node_attributes(G, pc, "post_count")
Gu   = G.to_undirected()
part = best_partition(Gu) if len(Gu.edges()) > 0 else {n:i for i,n in enumerate(Gu.nodes())}
nx.set_node_attributes(G, part, "community")
nx.set_node_attributes(G, BLOC, "bloc")
sub_net = {
    "nodes": [{"id":n,"pagerank":round(pr.get(n,0),6),"post_count":pc.get(n,0),
               "community":part.get(n,0),"bloc":BLOC.get(n,"other")}
              for n in G.nodes()],
    "edges": [{"source":u,"target":v,"weight":d["weight"]}
              for u,v,d in G.edges(data=True)]
}
print(f"Subreddit network: {len(sub_net['nodes'])} nodes, {len(sub_net['edges'])} edges")

# ── 2. AUTHOR INFLUENCE NETWORK ─────────────────────────────────────────────
asubs = defaultdict(set)
apost = defaultdict(int)
abloc = defaultdict(set)
for _, row in df.iterrows():
    a = row["author"]
    asubs[a].add(row["subreddit"])
    apost[a] += 1
    abloc[a].add(row["ideological_bloc"])
qualified = [a for a in asubs if apost[a]>=10 or len(asubs[a])>=2][:80]
Ga = nx.Graph()
for a in qualified:
    Ga.add_node(a, post_count=apost[a], num_subreddits=len(asubs[a]),
                subreddits=list(asubs[a]), is_bridge=len(abloc[a])>1)
for i in range(len(qualified)):
    for j in range(i+1, len(qualified)):
        shared = asubs[qualified[i]] & asubs[qualified[j]]
        if shared:
            Ga.add_edge(qualified[i], qualified[j],
                        weight=len(shared), shared=list(shared))
pra   = nx.pagerank(Ga, weight="weight") if Ga.edges() else {n:0 for n in qualified}
parta = best_partition(Ga) if Ga.edges() else {n:0 for n in qualified}
auth_net = {
    "nodes": [{"id":n,"post_count":Ga.nodes[n]["post_count"],
               "num_subreddits":Ga.nodes[n]["num_subreddits"],
               "subreddits":Ga.nodes[n]["subreddits"],
               "is_bridge":Ga.nodes[n]["is_bridge"],
               "pagerank":round(pra.get(n,0),6),
               "community":parta.get(n,0)} for n in Ga.nodes()],
    "edges": [{"source":u,"target":v,"weight":d["weight"],"shared":d.get("shared",[])}
              for u,v,d in Ga.edges(data=True)]
}
print(f"Author network: {len(auth_net['nodes'])} nodes, {len(auth_net['edges'])} edges")

# ── 3. SOURCE CITATION NETWORK ───────────────────────────────────────────────
lp = df[~df["is_self_post"] & (df["domain"]!="") & ~df["is_spam"]].copy()
se = lp.groupby(["subreddit","domain"]).size().reset_index(name="weight")
se = se[se["weight"] >= 3]
LEFT_D  = {"theguardian.com","nytimes.com","msnbc.com","huffpost.com"}
RIGHT_D = {"foxnews.com","breitbart.com","nypost.com","townhall.com"}
def dbias(d): return "left" if d in LEFT_D else "right" if d in RIGHT_D else "center"
src_net = {
    "nodes": ([{"id":s,"type":"subreddit","bloc":BLOC.get(s,"other")}
               for s in se["subreddit"].unique()] +
              [{"id":d,"type":"domain","bias":dbias(d)} for d in se["domain"].unique()]),
    "edges": se.rename(columns={"subreddit":"source","domain":"target"}).to_dict(orient="records")
}
print(f"Source network: {len(src_net['nodes'])} nodes, {len(src_net['edges'])} edges")

os.makedirs(DATA, exist_ok=True)
for name, data in [("network_subreddit",sub_net),
                   ("network_author",auth_net),
                   ("network_source",src_net)]:
    with open(f"{DATA}/{name}.json","w") as f: json.dump(data,f)
    print(f"✓ Saved {name}.json")
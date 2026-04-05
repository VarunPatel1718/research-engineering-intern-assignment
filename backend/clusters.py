import numpy as np, pandas as pd, json, os, hdbscan
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

DATA = os.path.join(os.path.dirname(__file__), "../data")
emb  = np.load(f"{DATA}/embeddings.npy")
meta = pd.read_parquet(f"{DATA}/search_meta.parquet")
print(f"Loaded {len(emb)} embeddings")

print("Reducing to 50D with PCA...")
pca50  = PCA(n_components=50, random_state=42)
reduced = pca50.fit_transform(emb)

print("Reducing to 2D for visualization...")
pca2   = PCA(n_components=2, random_state=42)
coords = pca2.fit_transform(reduced)

texts = meta["title"].fillna("").tolist()
vec   = TfidfVectorizer(max_features=5000, stop_words="english")
tfidf = vec.fit_transform(texts)
feat  = vec.get_feature_names_out()

results = {}
for k in [5, 8, 12, 20]:
    mcs = max(5, len(emb) // (k * 3))
    print(f"Running HDBSCAN k={k}, min_cluster_size={mcs}...")
    cl     = hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=3,
                              metric="euclidean", prediction_data=True)
    labels = cl.fit_predict(reduced)
    ulabels = [l for l in set(labels) if l != -1]
    cluster_labels = {}
    for label in ulabels:
        mask        = labels == label
        scores      = np.asarray(tfidf[mask].mean(axis=0)).flatten()
        top_indices = scores.argsort()[-5:][::-1]
        cluster_labels[int(label)] = [feat[i] for i in top_indices]
    results[str(k)] = {
        "labels":         labels.tolist(),
        "coords":         coords.tolist(),
        "cluster_labels": cluster_labels,
        "noise_count":    int((labels == -1).sum()),
        "cluster_count":  len(ulabels),
        "titles":         meta["title"].tolist(),
        "subreddits":     meta["subreddit"].tolist(),
    }
    print(f"  k={k}: {len(ulabels)} clusters, {(labels==-1).sum()} noise")

with open(f"{DATA}/clusters.json","w") as f: json.dump(results,f)
print("✓ Saved clusters.json with keys: 5, 8, 12, 20")
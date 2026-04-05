import numpy as np, pandas as pd, faiss, os
from sentence_transformers import SentenceTransformer

DATA     = os.path.join(os.path.dirname(__file__), "../data")
df_clean = pd.read_parquet(f"{DATA}/processed.parquet")
df_clean = df_clean[~df_clean["is_spam"]].reset_index(drop=True)
texts    = df_clean["text"].fillna("").tolist()

print(f"Embedding {len(texts)} posts... (~15 min on CPU)")
model = SentenceTransformer("all-MiniLM-L6-v2")
emb   = model.encode(
    texts, batch_size=64,
    show_progress_bar=True,
    convert_to_numpy=True
).astype("float32")
faiss.normalize_L2(emb)

index = faiss.IndexFlatIP(emb.shape[1])
index.add(emb)

faiss.write_index(index, f"{DATA}/faiss.index")
np.save(f"{DATA}/embeddings.npy", emb)
df_clean[["id","title","subreddit","author","created_utc","score",
          "num_comments","permalink","domain","ideological_bloc"]]\
    .to_parquet(f"{DATA}/search_meta.parquet", index=False)

print(f"✓ FAISS index: {index.ntotal} vectors, dim={emb.shape[1]}")
print("✓ Saved faiss.index, embeddings.npy, search_meta.parquet")
"""
build_duckdb.py
Run SECOND. Loads processed.parquet into DuckDB with indexes.

NOTE: DuckDB .db files are version-specific. Do NOT commit narrativetrail.db.
      startup.py rebuilds it from data.jsonl on every server boot.
"""
import duckdb, pandas as pd, os, sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
PARQUET  = f"{DATA_DIR}/processed.parquet"
DB_PATH  = f"{DATA_DIR}/narrativetrail.db"

if not os.path.exists(PARQUET):
    sys.exit("ERROR: processed.parquet not found. Run preprocess.py first.")

df  = pd.read_parquet(PARQUET)
con = duckdb.connect(DB_PATH)

con.execute("DROP TABLE IF EXISTS posts")
con.execute("CREATE TABLE posts AS SELECT * FROM df")

# Indexes for common query patterns
con.execute("CREATE INDEX IF NOT EXISTS idx_sub     ON posts(subreddit)")
con.execute("CREATE INDEX IF NOT EXISTS idx_ts      ON posts(created_utc)")
con.execute("CREATE INDEX IF NOT EXISTS idx_bloc    ON posts(ideological_bloc)")
con.execute("CREATE INDEX IF NOT EXISTS idx_author  ON posts(author)")

count = con.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
print(f"✓ DuckDB loaded: {count} rows → {DB_PATH}")
print(con.execute(
    "SELECT subreddit, COUNT(*) as n FROM posts GROUP BY subreddit ORDER BY n DESC"
).fetchdf().to_string(index=False))
con.close()
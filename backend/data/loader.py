# backend/data/loader.py

import json
import pandas as pd
import duckdb
import os

def load_data(jsonl_path: str, db_path: str = 'narrativetrail.db'):
    records = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                r = obj['data']
                records.append({
                    'id': str(r.get('id', '')),
                    'title': str(r.get('title', '')),
                    'selftext': str(r.get('selftext', '')),
                    'author': str(r.get('author', '')),
                    'subreddit': str(r.get('subreddit', '')),
                    'score': int(r.get('score', 0)),
                    'upvote_ratio': float(r.get('upvote_ratio', 0)),
                    'num_comments': int(r.get('num_comments', 0)),
                    'created_utc': float(r.get('created_utc', 0)),
                    'url': str(r.get('url_overridden_by_dest', '')),
                    'permalink': str(r.get('permalink', '')),
                    'num_crossposts': int(r.get('num_crossposts', 0)),
                    'crosspost_parent': str(r.get('crosspost_parent', '') or ''),
                    'is_self': bool(r.get('is_self', False)),
                    'domain': str(r.get('domain', '')),
                })
            except Exception as e:
                print(f'Skipping line: {e}')
                continue

    df = pd.DataFrame(records)

    # Clean selftext
    df['selftext'] = df['selftext'].replace({'[removed]': '', '[deleted]': ''}).fillna('')

    # Create combined text field for NLP
    df['text'] = (df['title'] + ' ' + df['selftext']).str.strip()

    # Filter bots
    df = df[~df['author'].isin(['AutoModerator', '[deleted]'])]

    # Force all string columns to object dtype (fixes DuckDB ArrowDtype error)
    str_cols = ['id', 'title', 'selftext', 'author', 'subreddit',
                'url', 'permalink', 'crosspost_parent', 'domain', 'text']
    for col in str_cols:
        df[col] = df[col].astype(object)

    print(f'Loaded {len(df)} records after filtering')

    # Save to DuckDB
    con = duckdb.connect(db_path)
    con.execute('DROP TABLE IF EXISTS posts')
    con.execute('CREATE TABLE posts AS SELECT * FROM df')

    # Add indexes for fast queries
    con.execute('CREATE INDEX IF NOT EXISTS idx_subreddit ON posts(subreddit)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_author ON posts(author)')
    con.execute('CREATE INDEX IF NOT EXISTS idx_created ON posts(created_utc)')

    count = con.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    print(f'DuckDB loaded: {count} rows')
    print(con.execute("""
        SELECT subreddit, COUNT(*) as cnt 
        FROM posts 
        GROUP BY subreddit 
        ORDER BY cnt DESC
    """).fetchdf())

    return con

if __name__ == '__main__':
    load_data(r'C:\Users\Varun Patel\Downloads\data.jsonl')
    
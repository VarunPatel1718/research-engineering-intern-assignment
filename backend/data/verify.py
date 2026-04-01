import duckdb
con = duckdb.connect('narrativetrail.db')

print(con.execute("SELECT COUNT(*) FROM posts").fetchone()[0])

print(con.execute("""
    SELECT subreddit, COUNT(*) as cnt 
    FROM posts 
    GROUP BY subreddit 
    ORDER BY cnt DESC
""").fetchdf())
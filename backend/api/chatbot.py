# backend/api/chatbot.py

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import get_connection

def get_data_context() -> dict:
    """Pull live stats from DuckDB to give the chatbot real context."""
    con = get_connection()
    
    # Subreddit breakdown
    sub_counts = con.execute("""
        SELECT subreddit, COUNT(*) as cnt, AVG(score) as avg_score
        FROM posts GROUP BY subreddit ORDER BY cnt DESC
    """).fetchdf().to_dict(orient='records')
    
    # Top authors
    top_authors = con.execute("""
        SELECT author, COUNT(*) as posts, SUM(score) as total_score,
               COUNT(DISTINCT subreddit) as subreddits_active
        FROM posts 
        WHERE author NOT IN ('AutoModerator','[deleted]')
        GROUP BY author ORDER BY posts DESC LIMIT 10
    """).fetchdf().to_dict(orient='records')
    
    # Peak weeks
    peak_weeks = con.execute("""
        SELECT DATE_TRUNC('week', to_timestamp(created_utc))::DATE as week,
               COUNT(*) as posts, subreddit
        FROM posts
        GROUP BY week, subreddit
        ORDER BY posts DESC LIMIT 10
    """).fetchdf().to_dict(orient='records')
    
    # Date range
    date_range = con.execute("""
        SELECT MIN(to_timestamp(created_utc))::DATE as start_date,
               MAX(to_timestamp(created_utc))::DATE as end_date,
               COUNT(*) as total_posts,
               COUNT(DISTINCT author) as unique_authors
        FROM posts
    """).fetchdf().to_dict(orient='records')[0]

    # Top domains
    top_domains = con.execute("""
        SELECT domain, COUNT(*) as cnt
        FROM posts WHERE domain != '' AND NOT domain LIKE 'self.%'
        GROUP BY domain ORDER BY cnt DESC LIMIT 10
    """).fetchdf().to_dict(orient='records')

    return {
        'subreddit_counts': sub_counts,
        'top_authors': top_authors,
        'peak_weeks': [{'week': str(r['week']), 'posts': r['posts'], 
                        'subreddit': r['subreddit']} for r in peak_weeks],
        'date_range': {k: str(v) for k, v in date_range.items()},
        'top_domains': top_domains,
    }

def query_database(user_question: str) -> str:
    """Try to answer specific data questions directly from DuckDB."""
    con = get_connection()
    q = user_question.lower()
    
    try:
        # Top author questions
        if any(w in q for w in ['top author', 'most posts', 'most active', 'who posted most']):
            df = con.execute("""
                SELECT author, COUNT(*) as posts, subreddit
                FROM posts WHERE author NOT IN ('AutoModerator','[deleted]')
                GROUP BY author, subreddit ORDER BY posts DESC LIMIT 5
            """).fetchdf()
            return f"Top authors by post count:\n" + \
                   "\n".join([f"- u/{r['author']} ({r['subreddit']}): {r['posts']} posts" 
                               for _, r in df.iterrows()])

        # Subreddit-specific questions
        for sub in ['Conservative','Liberal','politics','socialism','Anarchism',
                    'neoliberal','democrats','Republican','worldpolitics','PoliticalDiscussion']:
            if sub.lower() in q:
                df = con.execute(f"""
                    SELECT COUNT(*) as posts, AVG(score) as avg_score,
                           MAX(score) as max_score
                    FROM posts WHERE subreddit = '{sub}'
                """).fetchdf()
                row = df.iloc[0]
                return (f"r/{sub} stats: {int(row['posts'])} total posts, "
                        f"avg score {row['avg_score']:.1f}, "
                        f"max score {int(row['max_score'])}")

        # Election/spike questions
        if any(w in q for w in ['spike', 'peak', 'most activity', 'busiest']):
            df = con.execute("""
                SELECT DATE_TRUNC('week', to_timestamp(created_utc))::DATE as week,
                       COUNT(*) as posts, subreddit
                FROM posts GROUP BY week, subreddit
                ORDER BY posts DESC LIMIT 3
            """).fetchdf()
            result = "Peak activity periods:\n"
            for _, r in df.iterrows():
                result += f"- Week of {r['week']}: r/{r['subreddit']} had {r['posts']} posts\n"
            return result

        # Crosspost questions
        if any(w in q for w in ['crosspost', 'cross-post', 'shared', 'spread']):
            df = con.execute("""
                SELECT subreddit, COUNT(*) as crossposts
                FROM posts WHERE crosspost_parent != ''
                GROUP BY subreddit ORDER BY crossposts DESC
            """).fetchdf()
            return "Crosspost activity by subreddit:\n" + \
                   "\n".join([f"- r/{r['subreddit']}: {r['crossposts']} crossposts" 
                               for _, r in df.iterrows()])

    except Exception as e:
        pass
    
    return None  # Let Groq handle it

def chat(messages: list, user_message: str) -> dict:
    """Main chat function — uses Groq with real data context."""
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()
    
    # Try direct DB query first
    db_answer = query_database(user_message)
    
    # Get live data context
    context = get_data_context()
    
    system_prompt = f"""You are NarrativeTrail AI, an expert research assistant analyzing 
Reddit political data for the SimPPL research dashboard.

You have access to a dataset of {context['date_range']['total_posts']} Reddit posts 
from {context['date_range']['start_date']} to {context['date_range']['end_date']}, 
spanning 10 political subreddits from far-left to far-right during the US 2024 election.

DATASET FACTS YOU KNOW:
- Total posts: {context['date_range']['total_posts']}
- Unique authors: {context['date_range']['unique_authors']}
- Date range: {context['date_range']['start_date']} to {context['date_range']['end_date']}

Subreddit breakdown:
{chr(10).join([f"- r/{r['subreddit']}: {r['cnt']} posts (avg score: {r['avg_score']:.1f})" 
               for r in context['subreddit_counts']])}

Top 5 most active authors:
{chr(10).join([f"- u/{r['author']}: {r['posts']} posts across {r['subreddits_active']} subreddit(s)" 
               for r in context['top_authors'][:5]])}

Peak activity weeks:
{chr(10).join([f"- Week of {r['week']}: r/{r['subreddit']} had {r['posts']} posts" 
               for r in context['peak_weeks'][:5]])}

Top external domains shared:
{chr(10).join([f"- {r['domain']}: {r['cnt']} posts" for r in context['top_domains'][:5]])}

{"DIRECT DATABASE ANSWER: " + db_answer if db_answer else ""}

INSTRUCTIONS:
- Answer questions about this specific dataset with specific numbers
- Point out ideological framing differences when relevant
- Keep answers concise (2-4 sentences max)
- If asked about topics not in the data, say so clearly
- Suggest 2 follow-up questions the user might find interesting after each answer
- Format follow-ups as: "You might also ask: [question 1] | [question 2]"
"""

    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    
    # Build message history
    groq_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages[-6:]:  # Keep last 6 messages for context
        groq_messages.append({"role": msg["role"], "content": msg["content"]})
    groq_messages.append({"role": "user", "content": user_message})
    
    response = client.chat.completions.create(
        model='llama-3.1-8b-instant',
        messages=groq_messages,
        max_tokens=300,
        temperature=0.7
    )
    
    reply = response.choices[0].message.content.strip()
    
    # Extract follow-up suggestions
    suggestions = []
    if "You might also ask:" in reply:
        parts = reply.split("You might also ask:")
        reply = parts[0].strip()
        if len(parts) > 1:
            suggestions = [s.strip() for s in parts[1].split("|")][:2]
    
    return {
        "reply": reply,
        "suggestions": suggestions
    }
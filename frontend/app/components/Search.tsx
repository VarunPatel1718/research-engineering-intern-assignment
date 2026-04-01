'use client';
import { useState } from 'react';
import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL;

const SUBREDDIT_COLORS: Record<string, string> = {
  Conservative: '#fc8181', Republican: '#f56565',
  Liberal: '#68d391', democrats: '#4299e1',
  socialism: '#f6ad55', Anarchism: '#b794f4',
  neoliberal: '#76e4f7', politics: '#63b3ed',
  worldpolitics: '#fbd38d', PoliticalDiscussion: '#9ae6b4',
};

export default function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const search = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setSearched(true);
    const res = await axios.get(`${API}/api/search`, { params: { q } });
    setResults(res.data.results || []);
    setSuggestions(res.data.suggestions || []);
    setSummary(res.data.summary || '');
    setLoading(false);
  };

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-2">🔍 Semantic Search</h2>
      <p className="text-sm mb-4" style={{ color: '#718096' }}>
        Finds posts by meaning — not just keywords. Try concepts with zero word overlap.
      </p>

      <div className="flex gap-2 mb-4">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search(query)}
          placeholder="e.g. economic inequality, border security, voting rights..."
          className="flex-1 px-4 py-2 rounded-lg text-white text-sm"
          style={{ background: '#2d3748', border: '1px solid #4a5568' }}
        />
        <button
          onClick={() => search(query)}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ background: '#4f46e5' }}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* AI Summary */}
      {summary && (
        <div className="mb-4 p-4 rounded-lg text-sm"
          style={{ background: '#1a1f2e', border: '1px solid #4f46e5', color: '#a0aec0' }}>
          🤖 <strong className="text-white">AI Insight:</strong> {summary}
        </div>
      )}

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="mb-4">
          <span className="text-xs mr-2" style={{ color: '#718096' }}>Follow-up queries:</span>
          {suggestions.map(s => (
            <button key={s} onClick={() => { setQuery(s); search(s); }}
              className="mr-2 mb-1 px-3 py-1 rounded-full text-xs"
              style={{ background: '#2d3748', color: '#a0aec0', border: '1px solid #4a5568' }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {loading && <p style={{ color: '#718096' }}>Searching embeddings...</p>}
      {!loading && searched && results.length === 0 && (
        <p style={{ color: '#718096' }}>No results found.</p>
      )}

      <div className="flex flex-col gap-3">
        {results.map(post => (
          <div key={post.id} className="p-4 rounded-lg"
            style={{ background: '#1a1f2e', border: '1px solid #2d3748' }}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <a href={`https://reddit.com${post.permalink}`} target="_blank"
                  className="font-medium text-white hover:underline">
                  {post.title}
                </a>
                <div className="flex gap-2 mt-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      background: (SUBREDDIT_COLORS[post.subreddit] || '#a0aec0') + '22',
                      color: SUBREDDIT_COLORS[post.subreddit] || '#a0aec0'
                    }}>
                    r/{post.subreddit}
                  </span>
                  <span className="text-xs" style={{ color: '#718096' }}>
                    ↑ {post.score} · u/{post.author}
                  </span>
                </div>
              </div>
              <div className="text-right text-xs shrink-0" style={{ color: '#4a5568' }}>
                similarity<br />
                <span style={{ color: '#4f46e5', fontSize: 14, fontWeight: 600 }}>
                  {post.similarity_score?.toFixed(3)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
'use client';
import { useEffect, useState } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const API = process.env.NEXT_PUBLIC_API_URL;

const COLORS: Record<string, string> = {
  politics: '#63b3ed',
  Conservative: '#fc8181',
  Liberal: '#68d391',
  socialism: '#f6ad55',
  Anarchism: '#b794f4',
  neoliberal: '#76e4f7',
  democrats: '#4299e1',
  Republican: '#f56565',
  worldpolitics: '#fbd38d',
  PoliticalDiscussion: '#9ae6b4',
};

export default function Timeline() {
  const [data, setData] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [input, setInput] = useState('');
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchData = async (q: string) => {
    setLoading(true);
    const res = await axios.get(`${API}/api/timeline`, { params: { query: q } });
    const raw: any[] = res.data.data;

    const map: Record<string, any> = {};
    raw.forEach(row => {
      if (!map[row.week]) map[row.week] = { week: row.week };
      map[row.week][row.subreddit] = row.post_count;
    });
    const pivoted = Object.values(map).sort((a, b) => a.week.localeCompare(b.week));
    setData(pivoted);

    if (pivoted.length > 0) {
      const total = raw.reduce((s, r) => s + r.post_count, 0);
      const peak = raw.reduce((a, b) => a.post_count > b.post_count ? a : b);
      setSummary(res.data.summary || `Found ${total} posts matching "${q || 'all posts'}". Peak activity was in week of ${peak.week} on r/${peak.subreddit} with ${peak.post_count} posts.`);
    }
    setLoading(false);
  };

  useEffect(() => { fetchData(''); }, []);

  const subreddits = [...new Set(data.flatMap(d => Object.keys(d).filter(k => k !== 'week')))];

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-4">📈 Post Timeline</h2>

      {/* Search bar */}
      <div className="flex gap-2 mb-6">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && (setQuery(input), fetchData(input))}
          placeholder="Filter by topic (e.g. election, immigration)..."
          className="flex-1 px-4 py-2 rounded-lg text-white text-sm"
          style={{ background: '#2d3748', border: '1px solid #4a5568' }}
        />
        <button
          onClick={() => { setQuery(input); fetchData(input); }}
          className="px-4 py-2 rounded-lg text-sm font-medium text-white"
          style={{ background: '#4f46e5' }}
        >
          {loading ? 'Loading...' : 'Search'}
        </button>
        <button
          onClick={() => { setInput(''); setQuery(''); fetchData(''); }}
          className="px-4 py-2 rounded-lg text-sm"
          style={{ background: '#2d3748', color: '#a0aec0' }}
        >
          Reset
        </button>
      </div>

      {/* Chart */}
      <div style={{ background: '#1a1f2e', borderRadius: 12, padding: 24 }}>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
            <XAxis dataKey="week" stroke="#718096" tick={{ fontSize: 11 }}
              tickFormatter={v => v.slice(0, 7)} />
            <YAxis stroke="#718096" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#1a1f2e', border: '1px solid #2d3748', borderRadius: 8 }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend />
            {subreddits.map(sub => (
              <Line key={sub} type="monotone" dataKey={sub}
                stroke={COLORS[sub] || '#a0aec0'}
                dot={false} strokeWidth={2} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* AI Summary */}
      {summary && (
        <div className="mt-4 p-4 rounded-lg text-sm" style={{ background: '#1a1f2e', border: '1px solid #4f46e5', color: '#a0aec0' }}>
          🤖 <strong className="text-white">Insight:</strong> {summary}
        </div>
      )}
    </div>
  );
}
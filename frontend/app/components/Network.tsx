'use client';
import { useEffect, useState } from 'react';
import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL;

const COLORS: Record<string, string> = {
  politics: '#63b3ed', Conservative: '#fc8181', Liberal: '#68d391',
  socialism: '#f6ad55', Anarchism: '#b794f4', neoliberal: '#76e4f7',
  democrats: '#4299e1', Republican: '#f56565',
  worldpolitics: '#fbd38d', PoliticalDiscussion: '#9ae6b4',
};

export default function Network() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/api/network`).then(res => {
      setNodes(res.data.nodes.slice(0, 50));
      setEdges(res.data.edges);
      setSummary(res.data.summary || '');
      setLoading(false);
    });
  }, []);

  const WIDTH = 700, HEIGHT = 500, CX = 350, CY = 250, R = 200;
  const positioned = nodes.map((n, i) => ({
    ...n,
    x: CX + R * Math.cos((2 * Math.PI * i) / nodes.length),
    y: CY + R * Math.sin((2 * Math.PI * i) / nodes.length),
  }));
  const posMap: Record<string, any> = {};
  positioned.forEach(n => { posMap[n.author] = n; });

  if (loading) return <p style={{ color: '#718096' }}>Loading network...</p>;

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-2">🕸️ Author Network</h2>
      <p className="text-sm mb-2" style={{ color: '#718096' }}>
        Top 50 authors by post count. Edges = crosspost relationships. Click a node for details.
      </p>

      {summary && (
        <div className="mb-4 p-3 rounded-lg text-sm"
          style={{ background: '#1a1f2e', border: '1px solid #4f46e5', color: '#a0aec0' }}>
          🤖 <strong className="text-white">AI Insight:</strong> {summary}
        </div>
      )}

      <div className="flex gap-6">
        <div style={{ background: '#1a1f2e', borderRadius: 12, flex: 1 }}>
          <svg width="100%" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
            {edges.map((e, i) => {
              const s = posMap[e.source], t = posMap[e.target];
              if (!s || !t) return null;
              return <line key={i} x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke="#2d3748" strokeWidth={1} opacity={0.6} />;
            })}
            {positioned.map((n, idx) => (
              <g key={`${n.author}-${idx}`} onClick={() => setSelected(n)} style={{ cursor: 'pointer' }}>
                <circle cx={n.x} cy={n.y}
                  r={Math.min(4 + n.post_count / 10, 18)}
                  fill={COLORS[n.subreddit] || '#a0aec0'}
                  opacity={0.85}
                  stroke={selected?.author === n.author ? 'white' : 'transparent'}
                  strokeWidth={2}
                />
              </g>
            ))}
          </svg>
        </div>

        <div style={{ width: 200 }}>
          <p className="text-xs font-medium mb-2" style={{ color: '#718096' }}>SUBREDDITS</p>
          {Object.entries(COLORS).map(([sub, color]) => (
            <div key={sub} className="flex items-center gap-2 mb-1">
              <div className="w-3 h-3 rounded-full" style={{ background: color }} />
              <span className="text-xs" style={{ color: '#a0aec0' }}>r/{sub}</span>
            </div>
          ))}

          {selected && (
            <div className="mt-4 p-3 rounded-lg"
              style={{ background: '#1a1f2e', border: '1px solid #4f46e5' }}>
              <p className="font-medium text-white text-sm">u/{selected.author}</p>
              <p className="text-xs mt-1" style={{ color: '#a0aec0' }}>r/{selected.subreddit}</p>
              <p className="text-xs" style={{ color: '#a0aec0' }}>{selected.post_count} posts</p>
              <p className="text-xs" style={{ color: '#a0aec0' }}>
                PageRank: {selected.pagerank?.toFixed(5)}
              </p>
              <p className="text-xs" style={{ color: '#a0aec0' }}>
                Community: {selected.community}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
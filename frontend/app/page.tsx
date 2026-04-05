'use client';
import { useState, useEffect } from 'react';
import axios from 'axios';
import Timeline from './components/Timeline';
import Search from './components/Search';
import Network from './components/Network';
import Clusters from './components/Clusters';
import Chatbot from './components/Chatbot';
import KeyFindings from './components/KeyFindings';

const API = process.env.NEXT_PUBLIC_API_URL;

const TABS = [
  { id: 'Timeline', icon: '📈', label: 'Timeline' },
  { id: 'Search', icon: '🔍', label: 'Semantic Search' },
  { id: 'Network', icon: '🕸️', label: 'Network' },
  { id: 'Clusters', icon: '🗂️', label: 'Topic Clusters' },
  { id: 'Chat', icon: '💬', label: 'Research Assistant' },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState('Timeline');
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    // Wake up backend and get stats
    axios.get(`${API}/api/stats`).then(r => setStats(r.data)).catch(() => { });

    // Keep backend warm - ping every 10 minutes
    const interval = setInterval(() => {
      axios.get(`${API}/api/health`).catch(() => { });
    }, 10 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <main className="min-h-screen" style={{ background: '#080c14' }}>

      {/* Hero Header */}
      <div style={{
        background: 'linear-gradient(180deg, #0d1421 0%, #080c14 100%)',
        borderBottom: '1px solid #1e2d3d'
      }}>
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Top bar */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-3xl">🧭</span>
                <h1 className="text-3xl font-bold" style={{
                  background: 'linear-gradient(135deg, #a78bfa, #60a5fa)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}>
                  NarrativeTrail
                </h1>
                <span className="px-2 py-0.5 text-xs rounded-full" style={{
                  background: 'rgba(79,70,229,0.2)',
                  color: '#a78bfa',
                  border: '1px solid rgba(79,70,229,0.3)'
                }}>
                  Research Tool
                </span>
              </div>
              <p style={{ color: '#64748b', fontSize: 14 }}>
                Tracing how political narratives travel and mutate across the ideological spectrum on Reddit
              </p>
            </div>

            {/* Live Stats */}
            {stats ? (
              <div className="flex gap-3">
                {[
                  { label: 'Posts Analyzed', value: stats.total_posts?.toLocaleString(), color: '#60a5fa' },
                  { label: 'Unique Authors', value: stats.unique_authors?.toLocaleString(), color: '#a78bfa' },
                  { label: 'Communities', value: stats.subreddits, color: '#34d399' },
                  { label: 'Date Range', value: 'Jul 24 – Feb 25', color: '#fb923c' },
                ].map(s => (
                  <div key={s.label} className="text-right px-4 py-2 rounded-lg" style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid #1e2d3d'
                  }}>
                    <div className="text-xl font-bold" style={{ color: s.color }}>{s.value}</div>
                    <div className="text-xs" style={{ color: '#475569' }}>{s.label}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex gap-3">
                {['Posts Analyzed', 'Unique Authors', 'Communities', 'Date Range'].map(label => (
                  <div key={label} className="text-right px-4 py-2 rounded-lg" style={{
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid #1e2d3d',
                    minWidth: 100
                  }}>
                    <div className="text-xl font-bold" style={{ color: '#1e2d3d' }}>...</div>
                    <div className="text-xs" style={{ color: '#475569' }}>{label}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Story Banner */}
          <div className="mb-5 p-4 rounded-xl" style={{
            background: 'linear-gradient(135deg, rgba(79,70,229,0.08), rgba(124,58,237,0.08))',
            border: '1px solid rgba(79,70,229,0.2)'
          }}>
            <p style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.6 }}>
              <span style={{ color: '#a78bfa', fontWeight: 600 }}>The Story: </span>
              A topic emerges — say <em>"immigration"</em>. On r/Conservative it is framed as a security threat.
              On r/socialism it is labour exploitation. On r/Anarchism it is state violence.
              On r/Liberal it is a humanitarian crisis. NarrativeTrail traces this divergence —
              which communities amplified it first, which accounts drove it,
              and how framing mutated across the ideological spectrum.
            </p>
          </div>

          {/* Tabs */}
          <div className="flex gap-2">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="px-5 py-2.5 rounded-xl text-sm font-medium transition-all"
                style={activeTab === tab.id ? {
                  background: 'linear-gradient(135deg, #4f46e5, #7c3aed)',
                  color: 'white',
                  boxShadow: '0 4px 15px rgba(79,70,229,0.4)'
                } : {
                  background: 'rgba(255,255,255,0.04)',
                  color: '#64748b',
                  border: '1px solid #1e2d3d'
                }}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div style={{ display: activeTab === 'Timeline' ? 'block' : 'none' }}><Timeline /></div>
        <div style={{ display: activeTab === 'Search' ? 'block' : 'none' }}><Search /></div>
        <div style={{ display: activeTab === 'Network' ? 'block' : 'none' }}><Network /></div>
        <div style={{ display: activeTab === 'Clusters' ? 'block' : 'none' }}><Clusters /></div>
        <div style={{ display: activeTab === 'Chat' ? 'block' : 'none' }}><Chatbot /></div>
      </div>

      {/* Footer */}
      <div className="max-w-7xl mx-auto px-6 py-4" style={{
        borderTop: '1px solid #1e2d3d',
        color: '#334155',
        fontSize: 12
      }}>
        NarrativeTrail · Built for SimPPL Research Engineering Internship ·
        Dataset: 8,799 Reddit posts across 10 political subreddits · Jul 2024 – Feb 2025
      </div>
    </main>
  );
}
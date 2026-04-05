'use client';
import { useEffect, useState } from 'react';
import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL;

export default function KeyFindings() {
  const [visible, setVisible] = useState(false);

  return (
    <div className="mb-5">
      <button
        onClick={() => setVisible(!visible)}
        className="flex items-center gap-2 text-xs font-semibold mb-2 transition-all"
        style={{ color: visible ? '#a78bfa' : '#475569' }}>
        {visible ? '▼' : '▶'} KEY FINDINGS FROM THE DATA
      </button>

      {visible && (
        <div className="grid grid-cols-3 gap-3">
          {[
            {
              icon: '📅',
              title: 'Election Day Spike',
              stat: '+340%',
              detail: 'Week of Nov 4, 2024 saw the highest single-week post volume — r/Liberal peaked at 19 posts while r/Conservative remained quiet, suggesting asymmetric engagement with election results.',
              color: '#60a5fa'
            },
            {
              icon: '🌐',
              title: 'Cross-Spectrum Bridge',
              stat: 'u/John3262005',
              detail: 'Top PageRank influencer posting across multiple subreddits. Acts as a narrative bridge between r/neoliberal and center-left communities — the most connected node in the influence network.',
              color: '#a78bfa'
            },
            {
              icon: '📰',
              title: 'February 2025 Surge',
              stat: '774 posts/week',
              detail: 'r/Conservative hit its dataset peak in week of Feb 10, 2025 — coinciding with Trump deportation executive orders. r/politics simultaneously hit 1,712 avg score per post.',
              color: '#f43f5e'
            },
          ].map(f => (
            <div key={f.title} className="card p-4"
              style={{ borderLeft: `3px solid ${f.color}` }}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{f.icon}</span>
                <div>
                  <div className="text-xs font-semibold" style={{ color: f.color }}>
                    {f.title}
                  </div>
                  <div className="text-lg font-bold text-white">{f.stat}</div>
                </div>
              </div>
              <p className="text-xs" style={{ color: '#64748b', lineHeight: 1.5 }}>
                {f.detail}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
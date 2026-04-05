'use client';
import { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API = process.env.NEXT_PUBLIC_API_URL;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: string[];
}

const STARTER_QUESTIONS = [
  "Which subreddit was most active during the 2024 election?",
  "Who are the top 3 most influential authors in this dataset?",
  "How did immigration discussion differ between left and right subreddits?",
  "What caused the spike in posts in February 2025?",
  "Which external news sources were shared most across all communities?",
  "How many authors posted in multiple subreddits?",
];

export default function Chatbot() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await axios.post(`${API}/api/chat`, {
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        message: text
      });

      const assistantMsg: Message = {
        role: 'assistant',
        content: res.data.reply,
        suggestions: res.data.suggestions || []
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        suggestions: []
      }]);
    }
    setLoading(false);
  };

  const clearChat = () => setMessages([]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-white">💬 Research Assistant</h2>
          <p className="text-sm mt-0.5" style={{ color: '#64748b' }}>
            Ask questions about the dataset in plain English.
            Powered by real-time DuckDB queries + Groq AI.
          </p>
        </div>
        {messages.length > 0 && (
          <button onClick={clearChat}
            className="px-3 py-1.5 rounded-lg text-xs"
            style={{
              background: 'rgba(255,255,255,0.04)',
              color: '#64748b', border: '1px solid #1e2d3d'
            }}>
            Clear chat
          </button>
        )}
      </div>

      {/* Empty state — starter questions */}
      {messages.length === 0 && (
        <div className="mb-5">
          <p className="text-xs font-semibold mb-3" style={{ color: '#475569' }}>
            TRY ASKING
          </p>
          <div className="grid grid-cols-2 gap-2">
            {STARTER_QUESTIONS.map(q => (
              <button key={q} onClick={() => sendMessage(q)}
                className="p-3 rounded-xl text-left text-sm transition-all"
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid #1e2d3d',
                  color: '#94a3b8'
                }}
                onMouseEnter={e => {
                  (e.target as HTMLElement).style.borderColor = 'rgba(79,70,229,0.5)';
                  (e.target as HTMLElement).style.color = '#a78bfa';
                }}
                onMouseLeave={e => {
                  (e.target as HTMLElement).style.borderColor = '#1e2d3d';
                  (e.target as HTMLElement).style.color = '#94a3b8';
                }}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat messages */}
      {messages.length > 0 && (
        <div className="card mb-4 p-4 flex flex-col gap-4"
          style={{ maxHeight: '480px', overflowY: 'auto' }}>
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div style={{ maxWidth: '80%' }}>
                {/* Avatar */}
                <div className={`flex items-center gap-2 mb-1 ${msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}>
                  <span className="text-xs" style={{ color: '#334155' }}>
                    {msg.role === 'user' ? 'You' : '🤖 NarrativeTrail AI'}
                  </span>
                </div>

                {/* Bubble */}
                <div className="px-4 py-3 rounded-2xl text-sm"
                  style={msg.role === 'user' ? {
                    background: 'linear-gradient(135deg,#4f46e5,#7c3aed)',
                    color: 'white',
                    borderBottomRightRadius: 4
                  } : {
                    background: '#0f1923',
                    border: '1px solid #1e2d3d',
                    color: '#e2e8f0',
                    borderBottomLeftRadius: 4,
                    lineHeight: 1.6
                  }}>
                  {msg.content}
                </div>

                {/* Follow-up suggestions */}
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {msg.suggestions.map((s, si) => (
                      <button key={si} onClick={() => sendMessage(s)}
                        className="text-left px-3 py-1.5 rounded-lg text-xs transition-all"
                        style={{
                          background: 'rgba(79,70,229,0.1)',
                          color: '#a78bfa',
                          border: '1px solid rgba(79,70,229,0.2)'
                        }}>
                        ↗ {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {loading && (
            <div className="flex justify-start">
              <div className="px-4 py-3 rounded-2xl text-sm"
                style={{
                  background: '#0f1923', border: '1px solid #1e2d3d',
                  color: '#475569', borderBottomLeftRadius: 4
                }}>
                <span className="animate-pulse">NarrativeTrail AI is thinking...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
          placeholder="Ask anything about the dataset..."
          className="flex-1 px-4 py-3 rounded-xl text-sm"
          style={{
            background: '#0f1923',
            border: '1px solid #1e2d3d',
            color: '#e2e8f0',
            outline: 'none'
          }}
          disabled={loading}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          className="px-6 py-3 rounded-xl text-sm font-medium text-white transition-all"
          style={{
            background: loading || !input.trim()
              ? '#1e2d3d'
              : 'linear-gradient(135deg,#4f46e5,#7c3aed)',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer'
          }}>
          {loading ? '...' : 'Send'}
        </button>
      </div>

      {/* Capabilities hint */}
      <div className="mt-3 flex gap-2 flex-wrap">
        {['Dataset stats', 'Subreddit comparison', 'Author influence',
          'Narrative patterns', 'Peak activity', 'Cross-spectrum analysis'].map(cap => (
            <span key={cap} className="px-2 py-0.5 rounded-full text-xs"
              style={{
                background: 'rgba(255,255,255,0.03)',
                color: '#334155', border: '1px solid #1e2d3d'
              }}>
              {cap}
            </span>
          ))}
      </div>
    </div>
  );
}
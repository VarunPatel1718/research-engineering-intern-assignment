import { useState, useEffect, useRef, useCallback } from "react"
import axios from "axios"

const BASE = import.meta.env.VITE_API_URL || ""

const BLOC_COLORS = {
  left_radical: "#ef4444",
  center_left: "#3b82f6",
  right: "#f97316",
  mixed: "#8b5cf6",
}

const SUBREDDIT_X = {
  "r/Anarchism": 100,
  "r/socialism": 160,
  "r/Liberal": 280,
  "r/politics": 340,
  "r/neoliberal": 400,
  "r/PoliticalDiscussion": 460,
  "r/democrats": 520,
  "r/Conservative": 640,
  "r/Republican": 700,
  "r/worldpolitics": 820,
}

export default function PropagationAnimator({ selectedSubreddit }) {
  const [query, setQuery] = useState("")
  const [input, setInput] = useState("")
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tick, setTick] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const intervalRef = useRef(null)

  const fetchData = useCallback(async (q) => {
    if (!q || q.length < 2) return
    setLoading(true)
    setError(null)
    setTick(0)
    setPlaying(false)
    try {
      const res = await axios.get(`${BASE}/api/propagation`, { params: { q } })
      setData(res.data)
    } catch {
      setError("Failed to load propagation data.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!playing || !data) return
    intervalRef.current = setInterval(() => {
      setTick(t => {
        if (t >= data.posts.length - 1) {
          setPlaying(false)
          return t
        }
        return t + 1
      })
    }, Math.max(50, 300 / speed))
    return () => clearInterval(intervalRef.current)
  }, [playing, data, speed])

  const visiblePosts = data ? data.posts.slice(0, tick + 1) : []
  const activeSubs = new Set(visiblePosts.map(p => p.subreddit))

  const getX = (sub) => SUBREDDIT_X["r/" + sub] || SUBREDDIT_X[sub] || 450
  const getY = (bloc) => ({
    left_radical: 80, center_left: 160, right: 240, mixed: 320
  }[bloc] || 200)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white">Narrative Propagation Animator</h2>
        <p className="text-sm text-gray-400 mt-1">
          Watch how a narrative spreads across communities over time. Nodes light up as each subreddit first engages with the topic.
        </p>
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <input
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
          placeholder="Enter a topic to trace (e.g. 'federal workers fired')"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { setQuery(input); fetchData(input) } }}
        />
        <button
          onClick={() => { setQuery(input); fetchData(input) }}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition"
        >
          Trace
        </button>
      </div>

      {loading && (
        <div className="text-center py-12 text-gray-400">Loading propagation data...</div>
      )}

      {error && (
        <div className="text-red-400 text-sm">{error}</div>
      )}

      {data && !loading && (
        <>
          {/* Controls */}
          <div className="flex items-center gap-4 bg-gray-800 rounded-lg px-4 py-3">
            <button
              onClick={() => setTick(0)}
              className="text-gray-400 hover:text-white text-sm transition"
            >⏮ Reset</button>

            <button
              onClick={() => setPlaying(p => !p)}
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition"
            >
              {playing ? "⏸ Pause" : "▶ Play"}
            </button>

            <input
              type="range" min={0} max={data.posts.length - 1} value={tick}
              onChange={e => { setPlaying(false); setTick(Number(e.target.value)) }}
              className="flex-1 accent-blue-500"
            />

            <span className="text-gray-400 text-xs w-24 text-right">
              {tick + 1} / {data.posts.length} posts
            </span>

            <select
              value={speed}
              onChange={e => setSpeed(Number(e.target.value))}
              className="bg-gray-700 text-white text-xs rounded px-2 py-1"
            >
              <option value={0.5}>0.5×</option>
              <option value={1}>1×</option>
              <option value={2}>2×</option>
              <option value={5}>5×</option>
            </select>
          </div>

          {/* Current post info */}
          {data.posts[tick] && (
            <div className="bg-gray-800 rounded-lg px-4 py-3 border border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ background: BLOC_COLORS[data.posts[tick].ideological_bloc] || "#6b7280" }}
                />
                <span className="text-blue-400 text-xs font-medium">r/{data.posts[tick].subreddit}</span>
                <span className="text-gray-500 text-xs">{data.posts[tick].created_utc?.slice(0, 16)}</span>
              </div>
              <p className="text-white text-sm">{data.posts[tick].title}</p>
            </div>
          )}

          {/* SVG Animator */}
          <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden">
            <svg viewBox="0 0 920 420" className="w-full">
              {/* Bloc labels */}
              {[["Left Radical", 80], ["Center Left", 160], ["Right", 240], ["Mixed", 320]].map(([label, y]) => (
                <text key={label} x={20} y={y + 5} fill="#6b7280" fontSize={11}>{label}</text>
              ))}

              {/* Grid lines */}
              {[80, 160, 240, 320].map(y => (
                <line key={y} x1={90} y1={y} x2={910} y2={y} stroke="#1f2937" strokeWidth={1} />
              ))}

              {/* Propagation lines between active nodes */}
              {data.subreddits.filter(s => activeSubs.has(s.subreddit)).map((s, i, arr) => {
                if (i === 0) return null
                const prev = arr[i - 1]
                return (
                  <line
                    key={s.subreddit}
                    x1={getX(prev.subreddit)} y1={getY(prev.bloc)}
                    x2={getX(s.subreddit)} y2={getY(s.bloc)}
                    stroke="#3b82f6" strokeWidth={1} strokeOpacity={0.3}
                    strokeDasharray="4 4"
                  />
                )
              })}

              {/* Nodes */}
              {data.subreddits.map(s => {
                const active = activeSubs.has(s.subreddit)
                const cx = getX(s.subreddit)
                const cy = getY(s.bloc)
                const color = BLOC_COLORS[s.bloc] || "#6b7280"
                const postCount = visiblePosts.filter(p => p.subreddit === s.subreddit).length
                const r = active ? Math.min(6 + postCount * 1.5, 22) : 8

                return (
                  <g key={s.subreddit}>
                    {active && (
                      <circle cx={cx} cy={cy} r={r + 6} fill={color} opacity={0.15} />
                    )}
                    <circle
                      cx={cx} cy={cy} r={r}
                      fill={active ? color : "#1f2937"}
                      stroke={active ? color : "#374151"}
                      strokeWidth={2}
                      style={{ transition: "all 0.3s ease" }}
                    />
                    <text
                      x={cx} y={cy + r + 14}
                      textAnchor="middle" fill={active ? "#e5e7eb" : "#4b5563"}
                      fontSize={9}
                    >
                      r/{s.subreddit}
                    </text>
                    {active && (
                      <text x={cx} y={cy + 4} textAnchor="middle" fill="white" fontSize={9} fontWeight="bold">
                        {postCount}
                      </text>
                    )}
                  </g>
                )
              })}
            </svg>
          </div>

          {/* First movers table */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-700">
              <h3 className="text-sm font-semibold text-white">First Movers</h3>
            </div>
            <div className="divide-y divide-gray-700">
              {data.subreddits.slice(0, 8).map((s, i) => (
                <div key={s.subreddit} className={`flex items-center gap-3 px-4 py-2.5 ${activeSubs.has(s.subreddit) ? "bg-gray-750" : "opacity-40"}`}>
                  <span className="text-gray-500 text-xs w-4">{i + 1}</span>
                  <span className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: BLOC_COLORS[s.bloc] || "#6b7280" }} />
                  <span className="text-blue-400 text-sm">r/{s.subreddit}</span>
                  <span className="text-gray-400 text-xs flex-1">{s.first_post?.slice(0, 16)}</span>
                  <span className="text-gray-500 text-xs">{s.count} posts</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {!data && !loading && (
        <div className="text-center py-16 text-gray-500 text-sm">
          Enter a topic above to trace how it propagated across communities.
        </div>
      )}
    </div>
  )
}
import { useState, useCallback } from "react"
import axios from "axios"

const BASE = import.meta.env.VITE_API_URL || ""

const BLOC_COLORS = {
  left_radical: "#ef4444",
  center_left: "#3b82f6",
  right: "#f97316",
  mixed: "#8b5cf6",
}

const INTENSITY_COLOR = (intensity) => {
  if (intensity >= 3) return "#ef4444"
  if (intensity >= 1.5) return "#f97316"
  return "#eab308"
}

export default function CoordinatedAmplification({ selectedSubreddit }) {
  const [input, setInput] = useState("")
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [windowHours, setWindowHours] = useState(6)
  const [minAuthors, setMinAuthors] = useState(3)
  const [expanded, setExpanded] = useState(null)

  const fetchData = useCallback(async () => {
    if (!input || input.length < 2) return
    setLoading(true)
    setError(null)
    setExpanded(null)
    try {
      const res = await axios.get(`${BASE}/api/coordinated`, {
        params: { q: input, window_hours: windowHours, min_authors: minAuthors }
      })
      setData(res.data)
    } catch {
      setError("Failed to load coordinated amplification data.")
    } finally {
      setLoading(false)
    }
  }, [input, windowHours, minAuthors])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white">Coordinated Amplification Detector</h2>
        <p className="text-sm text-gray-400 mt-1">
          Finds clusters where multiple authors posted semantically similar content within a short time window —
          the signature of coordinated amplification campaigns.
        </p>
      </div>

      {/* Search + params */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 space-y-3">
        <div className="flex gap-2">
          <input
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="Enter topic to scan (e.g. 'federal workers')"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") fetchData() }}
          />
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition"
          >
            Scan
          </button>
        </div>

        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-gray-400">
            Time window:
            <select
              value={windowHours}
              onChange={e => setWindowHours(Number(e.target.value))}
              className="bg-gray-900 border border-gray-700 text-white text-xs rounded px-2 py-1"
            >
              {[1, 3, 6, 12, 24].map(h => (
                <option key={h} value={h}>{h}h</option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-400">
            Min posts:
            <select
              value={minAuthors}
              onChange={e => setMinAuthors(Number(e.target.value))}
              className="bg-gray-900 border border-gray-700 text-white text-xs rounded px-2 py-1"
            >
              {[2, 3, 5, 8, 10].map(n => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {loading && (
        <div className="text-center py-12 text-gray-400">Scanning for coordinated activity...</div>
      )}

      {error && <div className="text-red-400 text-sm">{error}</div>}

      {data && !loading && (
        <>
          {/* Summary bar */}
          <div className="grid grid-cols-3 gap-3">
            {[
              ["Events Detected", data.events.length],
              ["Posts Scanned", data.total_posts],
              ["Time Window", `${data.window_hours}h`],
            ].map(([label, val]) => (
              <div key={label} className="bg-gray-800 rounded-lg px-4 py-3 border border-gray-700">
                <div className="text-2xl font-bold text-white">{val}</div>
                <div className="text-xs text-gray-400 mt-0.5">{label}</div>
              </div>
            ))}
          </div>

          {data.events.length === 0 && (
            <div className="text-center py-10 text-gray-500 text-sm">
              No coordinated amplification events detected for this topic and window size.
              Try a broader topic or larger time window.
            </div>
          )}

          {/* Events list */}
          <div className="space-y-3">
            {data.events.map((evt, i) => (
              <div
                key={i}
                className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden"
              >
                {/* Event header */}
                <button
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-750 transition text-left"
                >
                  {/* Intensity indicator */}
                  <div
                    className="w-1 self-stretch rounded-full flex-shrink-0"
                    style={{ background: INTENSITY_COLOR(evt.intensity) }}
                  />

                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ background: BLOC_COLORS[evt.bloc] || "#6b7280" }}
                  />

                  <span className="text-blue-400 text-sm font-medium">r/{evt.subreddit}</span>

                  <div className="flex-1 flex items-center gap-4 text-xs text-gray-400">
                    <span>{evt.post_count} posts</span>
                    <span>{evt.unique_authors} authors</span>
                    <span>{evt.window_start?.slice(0, 16)}</span>
                    <span>→</span>
                    <span>{evt.window_end?.slice(0, 16)}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className="text-xs px-2 py-0.5 rounded-full font-medium"
                      style={{
                        background: INTENSITY_COLOR(evt.intensity) + "22",
                        color: INTENSITY_COLOR(evt.intensity)
                      }}
                    >
                      {evt.intensity} posts/hr
                    </span>
                    <span className="text-gray-500 text-xs">{expanded === i ? "▲" : "▼"}</span>
                  </div>
                </button>

                {/* Expanded posts */}
                {expanded === i && (
                  <div className="border-t border-gray-700 divide-y divide-gray-700">
                    {/* Verdict */}
                    <div className="px-4 py-3 bg-gray-900">
                      <p className="text-xs text-gray-400">
                        <span className="text-yellow-400 font-medium">Analysis: </span>
                        {evt.post_count} posts by {evt.unique_authors} author{evt.unique_authors !== 1 ? "s" : ""} in r/{evt.subreddit} within {windowHours}h —
                        {evt.intensity >= 3
                          ? " high-intensity burst. Strong signal of coordinated amplification."
                          : evt.intensity >= 1.5
                            ? " moderate burst. Could be organic news response or light coordination."
                            : " low intensity. Likely organic community engagement."}
                      </p>
                    </div>

                    {evt.posts.map((post, j) => (
                      <div key={j} className="px-4 py-2.5 flex items-start gap-3">
                        <span className="text-gray-600 text-xs mt-0.5 w-4">{j + 1}</span>
                        <div className="flex-1">
                          <p className="text-gray-200 text-sm">{post.title}</p>
                          <p className="text-gray-500 text-xs mt-0.5">{post.created_utc?.slice(0, 16)}</p>
                        </div>
                        <span className="text-gray-500 text-xs">
                          {(post.similarity * 100).toFixed(0)}% match
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {!data && !loading && (
        <div className="text-center py-16 text-gray-500 text-sm">
          Enter a topic above to scan for coordinated amplification events.
        </div>
      )}
    </div>
  )
}
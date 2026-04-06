import { useState, useEffect, useRef, useCallback } from "react"
import axios from "axios"
import { BLOC_COLORS } from "../App"

const BASE = import.meta.env.VITE_API_URL || ""

const EXAMPLE_QUERIES = [
  "federal workers fired",
  "nuclear weapons staff",
  "immigration crackdown",
  "DOGE government cuts",
  "FAA staffing crisis",
]

const SUBREDDIT_POSITIONS = {
  Anarchism: { x: 80, y: 80 },
  socialism: { x: 80, y: 200 },
  Liberal: { x: 220, y: 60 },
  politics: { x: 220, y: 140 },
  neoliberal: { x: 220, y: 220 },
  PoliticalDiscussion: { x: 220, y: 300 },
  democrats: { x: 220, y: 380 },
  Conservative: { x: 600, y: 100 },
  Republican: { x: 600, y: 240 },
  worldpolitics: { x: 840, y: 200 },
}

const BLOC_LABEL = {
  left_radical: "Left Radical",
  center_left: "Center Left",
  right: "Right",
  mixed: "Mixed",
}

function getBlocColor(bloc) {
  return BLOC_COLORS[bloc] || "#6b7280"
}

export default function PropagationAnimator({ filters }) {
  const [query, setQuery] = useState("")
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tick, setTick] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [lastQ, setLastQ] = useState("")
  const intervalRef = useRef(null)

  const handleSearch = useCallback(async function (q) {
    const query = (q || "").trim()
    if (!query || query.length < 2) return
    setLoading(true)
    setError(null)
    setData(null)
    setTick(0)
    setPlaying(false)
    setLastQ(query)
    try {
      const res = await axios.get(BASE + "/api/propagation", { params: { q: query } })
      setData(res.data)
    } catch {
      setError("Request failed — check that the backend is running.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(function () {
    if (!playing || !data) return
    intervalRef.current = setInterval(function () {
      setTick(function (t) {
        if (t >= data.posts.length - 1) {
          setPlaying(false)
          return t
        }
        return t + 1
      })
    }, Math.max(40, 250 / speed))
    return function () { clearInterval(intervalRef.current) }
  }, [playing, data, speed])

  const visiblePosts = data ? data.posts.slice(0, tick + 1) : []
  const activeSubs = new Set(visiblePosts.map(function (p) { return p.subreddit }))

  const currentPost = data && data.posts[tick]

  const handleExample = function (q) {
    setQuery(q)
    setTimeout(function () { handleSearch(q) }, 50)
  }

  return (
    <section style={{ width: "100%" }}>
      <style>{`
        .pa-chip {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 999px;
          padding: 4px 12px;
          font-size: 11px;
          color: var(--text-sec, #94a3b8);
          cursor: pointer;
          transition: background 0.15s, color 0.15s;
          font-family: inherit;
          white-space: nowrap;
        }
        .pa-chip:hover {
          background: rgba(255,255,255,0.08);
          color: var(--text-primary, #f1f5f9);
        }
        .pa-node {
          transition: r 0.3s ease, opacity 0.3s ease;
        }
      `}</style>

      {/* ── Header ── */}
      <div style={{ marginBottom: "22px" }}>
        <p className="sec-title">Narrative Propagation Animator</p>
        <p className="sec-desc">
          Watch how a narrative spreads across communities over time.
          Nodes light up sequentially as each subreddit first engages with the topic —
          revealing cascade vs. independent emergence patterns.
        </p>
      </div>

      {/* ── Search ── */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "14px" }}>
        <input
          value={query}
          onChange={function (e) { setQuery(e.target.value) }}
          onKeyDown={function (e) { if (e.key === "Enter") handleSearch(query) }}
          placeholder='Try "federal workers fired" or "immigration policy"...'
          className="input"
          style={{ flex: 1 }}
        />
        <button
          onClick={function () { handleSearch(query) }}
          disabled={loading || query.trim().length < 2}
          className="btn btn-blue"
        >
          {loading ? "Tracing..." : "Trace"}
        </button>
      </div>

      {/* ── Short query warning ── */}
      {query.length > 0 && query.trim().length < 2 && (
        <p style={{ fontSize: "11px", color: "#fbbf24", marginBottom: "12px" }}>
          Please enter at least 2 characters
        </p>
      )}

      {/* ── Example chips ── */}
      {!data && !loading && (
        <div style={{
          display: "flex", flexWrap: "wrap",
          alignItems: "center", gap: "8px",
          marginBottom: "24px",
        }}>
          <span style={{
            fontSize: "10px", fontWeight: "600",
            color: "var(--text-dim)",
            textTransform: "uppercase", letterSpacing: "0.08em",
          }}>
            Try
          </span>
          {EXAMPLE_QUERIES.map(function (q) {
            return (
              <button key={q} onClick={function () { handleExample(q) }} className="pa-chip">
                {q}
              </button>
            )
          })}
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div style={{
          padding: "12px 16px",
          background: "rgba(248,113,113,0.06)",
          border: "1px solid rgba(248,113,113,0.2)",
          borderLeft: "3px solid #f87171",
          borderRadius: "8px",
          fontSize: "13px", color: "#fca5a5",
          marginBottom: "16px",
        }}>
          {error}
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div className="skeleton" style={{ height: "60px", borderRadius: "10px" }} />
          <div className="skeleton" style={{ height: "360px", borderRadius: "10px" }} />
          <div className="skeleton" style={{ height: "200px", borderRadius: "10px" }} />
        </div>
      )}

      {/* ── Results ── */}
      {data && !loading && (
        <div>
          {/* Stats row */}
          <div style={{
            display: "flex", flexWrap: "wrap",
            gap: "6px", marginBottom: "20px",
          }}>
            {[
              { label: "Query", value: '"' + lastQ + '"' },
              { label: "Total posts", value: String(data.posts.length) },
              { label: "Communities", value: String(data.subreddits.length) },
              { label: "First mover", value: data.subreddits[0] ? "r/" + data.subreddits[0].subreddit : "—" },
            ].map(function (item) {
              return (
                <div key={item.label} style={{
                  display: "flex", alignItems: "center", gap: "5px",
                  padding: "4px 10px",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: "999px",
                  fontSize: "11px",
                }}>
                  <span style={{ color: "var(--text-sec)" }}>{item.label + ":"}</span>
                  <span className="mono" style={{ color: "var(--text-sec)", fontWeight: "500" }}>
                    {item.value}
                  </span>
                </div>
              )
            })}
          </div>

          {/* ── Playback controls ── */}
          <div style={{
            display: "flex", alignItems: "center", gap: "12px",
            padding: "14px 18px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            marginBottom: "20px",
          }}>
            <button
              onClick={function () { setTick(0); setPlaying(false) }}
              style={{
                background: "rgba(255,255,255,0.06)",
                border: "1px solid var(--border)",
                color: "var(--text-sec)",
                borderRadius: "6px",
                padding: "5px 10px",
                fontSize: "12px",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              ⏮
            </button>

            <button
              onClick={function () { setPlaying(function (p) { return !p }) }}
              className="btn btn-blue"
              style={{ minWidth: "80px", padding: "5px 16px", fontSize: "12px" }}
            >
              {playing ? "⏸ Pause" : "▶ Play"}
            </button>

            <input
              type="range"
              min={0}
              max={data.posts.length - 1}
              value={tick}
              onChange={function (e) { setPlaying(false); setTick(Number(e.target.value)) }}
              style={{ flex: 1, accentColor: "#4f8ef7" }}
            />

            <span className="mono" style={{
              fontSize: "11px", color: "var(--text-dim)",
              whiteSpace: "nowrap", minWidth: "80px", textAlign: "right",
            }}>
              {tick + 1} / {data.posts.length}
            </span>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "10px", color: "var(--text-dim)" }}>Speed</span>
              <select
                value={speed}
                onChange={function (e) { setSpeed(Number(e.target.value)) }}
                style={{
                  background: "var(--bg-elevated, #0e1628)",
                  border: "1px solid var(--border)",
                  color: "var(--text-primary)",
                  fontSize: "11px",
                  borderRadius: "6px",
                  padding: "3px 6px",
                  cursor: "pointer",
                }}
              >
                <option value={0.5}>0.5×</option>
                <option value={1}>1×</option>
                <option value={2}>2×</option>
                <option value={5}>5×</option>
              </select>
            </div>
          </div>

          {/* ── Current post card ── */}
          {currentPost && (
            <div style={{
              padding: "14px 18px",
              background: getBlocColor(currentPost.ideological_bloc) + "08",
              border: "1px solid " + getBlocColor(currentPost.ideological_bloc) + "25",
              borderLeft: "3px solid " + getBlocColor(currentPost.ideological_bloc),
              borderRadius: "10px",
              marginBottom: "20px",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                <div style={{
                  width: "7px", height: "7px", borderRadius: "50%",
                  background: getBlocColor(currentPost.ideological_bloc),
                  flexShrink: 0,
                }} />
                <span style={{
                  fontSize: "11px", fontWeight: "600",
                  color: getBlocColor(currentPost.ideological_bloc),
                }}>
                  {"r/" + currentPost.subreddit}
                </span>
                <span style={{ fontSize: "10px", color: "var(--text-dim)" }}>
                  {currentPost.created_utc?.slice(0, 10)}
                </span>
                <span style={{
                  marginLeft: "auto",
                  fontSize: "10px", fontWeight: "600",
                  color: "var(--text-dim)",
                }}>
                  {BLOC_LABEL[currentPost.ideological_bloc] || currentPost.ideological_bloc}
                </span>
              </div>
              <p style={{
                fontSize: "13px",
                color: "var(--text-primary)",
                lineHeight: "1.55",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
                wordBreak: "break-word",
              }}>
                {currentPost.title}
              </p>
            </div>
          )}

          {/* ── SVG graph ── */}
          <div style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "12px",
            padding: "20px",
            marginBottom: "20px",
            overflow: "hidden",
          }}>
            <p style={{
              fontSize: "9px", fontWeight: "600",
              color: "var(--text-dim)",
              textTransform: "uppercase", letterSpacing: "0.1em",
              marginBottom: "16px",
            }}>
              Propagation Graph
            </p>
            <svg viewBox="0 0 960 460" style={{ width: "100%", display: "block" }}>

              {/* Bloc zone backgrounds */}
              {[
                { label: "Left Radical", x: 30, w: 140, color: BLOC_COLORS.left_radical },
                { label: "Center Left", x: 170, w: 200, color: BLOC_COLORS.center_left },
                { label: "Right", x: 540, w: 200, color: BLOC_COLORS.right },
                { label: "Mixed", x: 760, w: 180, color: BLOC_COLORS.mixed },
              ].map(function (zone) {
                return (
                  <g key={zone.label}>
                    <rect
                      x={zone.x} y={20} width={zone.w} height={420}
                      fill={zone.color} fillOpacity={0.04}
                      rx={8}
                    />
                    <text
                      x={zone.x + zone.w / 2} y={14}
                      textAnchor="middle"
                      fill={zone.color} fillOpacity={0.6}
                      fontSize={9} fontWeight={600}
                    >
                      {zone.label}
                    </text>
                  </g>
                )
              })}

              {/* Propagation lines between active nodes in order */}
              {(function () {
                const activeSorted = data.subreddits.filter(function (s) {
                  return activeSubs.has(s.subreddit)
                })
                return activeSorted.map(function (s, i) {
                  if (i === 0) return null
                  const prev = activeSorted[i - 1]
                  const p1 = SUBREDDIT_POSITIONS[prev.subreddit] || { x: 480, y: 230 }
                  const p2 = SUBREDDIT_POSITIONS[s.subreddit] || { x: 480, y: 230 }
                  return (
                    <line
                      key={s.subreddit + "-line"}
                      x1={p1.x} y1={p1.y}
                      x2={p2.x} y2={p2.y}
                      stroke="#4f8ef7"
                      strokeWidth={1.5}
                      strokeOpacity={0.25}
                      strokeDasharray="5 4"
                    />
                  )
                })
              })()}

              {/* Nodes */}
              {data.subreddits.map(function (s) {
                const pos = SUBREDDIT_POSITIONS[s.subreddit] || { x: 480, y: 230 }
                const active = activeSubs.has(s.subreddit)
                const color = getBlocColor(s.bloc)
                const count = visiblePosts.filter(function (p) { return p.subreddit === s.subreddit }).length
                const r = active ? Math.min(8 + count * 1.8, 26) : 8
                const isFirst = data.subreddits[0]?.subreddit === s.subreddit && active

                return (
                  <g key={s.subreddit}>
                    {/* Pulse ring for first mover */}
                    {isFirst && (
                      <circle
                        cx={pos.x} cy={pos.y} r={r + 10}
                        fill="none"
                        stroke={color}
                        strokeWidth={1}
                        strokeOpacity={0.3}
                      />
                    )}

                    {/* Glow */}
                    {active && (
                      <circle
                        cx={pos.x} cy={pos.y} r={r + 5}
                        fill={color} fillOpacity={0.12}
                      />
                    )}

                    {/* Node */}
                    <circle
                      cx={pos.x} cy={pos.y} r={r}
                      fill={active ? color : "var(--bg-elevated, #0e1628)"}
                      stroke={active ? color : "#374151"}
                      strokeWidth={active ? 0 : 1.5}
                      className="pa-node"
                    />

                    {/* Post count inside node */}
                    {active && count > 0 && (
                      <text
                        x={pos.x} y={pos.y + 4}
                        textAnchor="middle"
                        fill="white" fontSize={9} fontWeight={700}
                      >
                        {count}
                      </text>
                    )}

                    {/* Subreddit label */}
                    <text
                      x={pos.x} y={pos.y + r + 14}
                      textAnchor="middle"
                      fill={active ? "var(--text-sec)" : "#374151"}
                      fontSize={9}
                    >
                      {"r/" + s.subreddit}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>

          {/* ── First movers table ── */}
          <div style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            overflow: "hidden",
          }}>
            <p style={{
              fontSize: "9px", fontWeight: "600",
              color: "var(--text-dim)",
              textTransform: "uppercase", letterSpacing: "0.1em",
              padding: "14px 18px 0",
              marginBottom: "12px",
            }}>
              Propagation Order
            </p>
            <div>
              {data.subreddits.map(function (s, i) {
                const color = getBlocColor(s.bloc)
                const active = activeSubs.has(s.subreddit)
                const count = visiblePosts.filter(function (p) { return p.subreddit === s.subreddit }).length

                return (
                  <div key={s.subreddit} style={{
                    display: "flex", alignItems: "center", gap: "12px",
                    padding: "10px 18px",
                    borderTop: i > 0 ? "1px solid var(--border)" : "none",
                    opacity: active ? 1 : 0.35,
                    transition: "opacity 0.3s",
                    background: i === 0 && active ? color + "06" : "transparent",
                  }}>
                    <span className="mono" style={{
                      width: "22px", height: "22px",
                      borderRadius: "50%",
                      background: active ? color + "20" : "rgba(255,255,255,0.04)",
                      border: "1px solid " + (active ? color + "40" : "var(--border)"),
                      color: active ? color : "var(--text-dim)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "10px", fontWeight: "700",
                      flexShrink: 0,
                    }}>
                      {i + 1}
                    </span>

                    <div style={{
                      width: "7px", height: "7px", borderRadius: "50%",
                      background: color, flexShrink: 0,
                    }} />

                    <span style={{
                      fontSize: "13px", fontWeight: "600",
                      color: active ? color : "var(--text-dim)",
                      minWidth: "130px",
                    }}>
                      {"r/" + s.subreddit}
                    </span>

                    <span className="mono" style={{
                      fontSize: "11px", color: "var(--text-sec)",
                      flex: 1,
                    }}>
                      {s.first_post?.slice(0, 10)}
                    </span>

                    <span style={{
                      fontSize: "10px", color: "var(--text-dim)",
                      marginRight: "12px",
                    }}>
                      {s.count} posts
                    </span>

                    {i === 0 && active && (
                      <span style={{
                        fontSize: "9px", fontWeight: "700",
                        color: "#fbbf24",
                        background: "rgba(251,191,36,0.1)",
                        border: "1px solid rgba(251,191,36,0.2)",
                        borderRadius: "999px",
                        padding: "2px 8px",
                        whiteSpace: "nowrap",
                      }}>
                        ★ First Mover
                      </span>
                    )}

                    {active && count > 0 && (
                      <div style={{
                        height: "4px",
                        width: Math.min(count * 8, 80) + "px",
                        background: color,
                        borderRadius: "999px",
                        opacity: 0.6,
                        flexShrink: 0,
                      }} />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* ── Empty state ── */}
      {!data && !loading && (
        <div style={{
          padding: "48px 24px", textAlign: "center",
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
        }}>
          <p style={{ fontSize: "13px", color: "var(--text-sec)", marginBottom: "4px" }}>
            Enter a topic above to animate its propagation
          </p>
          <p style={{ fontSize: "11px", color: "var(--text-dim)" }}>
            Nodes light up as each community first engages with the topic
          </p>
        </div>
      )}
    </section>
  )
}
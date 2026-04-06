import { useState, useRef } from "react"
import axios from "axios"
import { BLOC_COLORS } from "../App"

const BASE = import.meta.env.VITE_API_URL || ""

const SEMANTIC_EXAMPLES = [
  {
    query: "fear of losing livelihood under new policy",
    note: "Zero overlap — surfaces posts about layoffs, budget cuts, federal firings",
    lang: "EN",
  },
  {
    query: "राजनीतिक ध्रुवीकरण और मीडिया पक्षपात",
    note: "Hindi — multilingual embeddings bridge to English political coverage posts",
    lang: "HI",
  },
  {
    query: "distrust of institutions and surveillance state",
    note: "Zero overlap — finds posts about FBI, FISA, government overreach",
    lang: "EN",
  },
]

const BLOC_FILTERS = [
  { key: "all", label: "All" },
  { key: "left_radical", label: "Left Radical" },
  { key: "center_left", label: "Center Left" },
  { key: "right", label: "Right" },
  { key: "mixed", label: "Mixed" },
]

// Sidebar subreddit → ideological bloc
const SUBREDDIT_TO_BLOC = {
  Anarchism: "left_radical",
  socialism: "left_radical",
  Liberal: "center_left",
  democrats: "center_left",
  politics: "center_left",
  neoliberal: "center_left",
  PoliticalDiscussion: "center_left",
  Conservative: "right",
  Republican: "right",
  worldpolitics: "mixed",
}

const PAGE_SIZE = 15

function getSimColor(score) {
  if (score >= 0.7) return "#34d399"
  if (score >= 0.5) return "#fbbf24"
  return "#6b7280"
}

function getFilterBtnStyle(isActive, blocKey) {
  if (isActive) {
    const bg = blocKey === "all"
      ? "var(--blue)"
      : (BLOC_COLORS[blocKey] || "var(--blue)")
    return {
      borderRadius: "999px", padding: "3px 11px",
      fontSize: "11px", fontWeight: "500",
      border: "none", cursor: "pointer",
      background: bg, color: "white",
      transition: "all 0.15s", fontFamily: "inherit",
    }
  }
  return {
    borderRadius: "999px", padding: "3px 11px",
    fontSize: "11px", fontWeight: "400",
    border: "1px solid var(--border)",
    cursor: "pointer",
    background: "rgba(255,255,255,0.03)",
    color: "var(--text-sec)",
    transition: "all 0.15s", fontFamily: "inherit",
  }
}

// ── Result card ───────────────────────────────────────────────────────────────
function ResultCard({ result, index }) {
  const bloc = result.ideological_bloc
  const color = BLOC_COLORS[bloc] || "#6b7280"
  const sim = Math.round((result.similarity || 0) * 100)
  const simColor = getSimColor(result.similarity || 0)
  const date = result.created_utc ? result.created_utc.slice(0, 10) : ""
  const href = "https://reddit.com" + (result.permalink || "")

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="sp-card"
      style={{ display: "flex", gap: "12px", textDecoration: "none", marginBottom: "6px" }}
    >
      <span className="mono" style={{
        width: "22px", height: "22px",
        borderRadius: "50%",
        background: "rgba(255,255,255,0.05)",
        color: "var(--text-dim)",
        display: "flex", alignItems: "center",
        justifyContent: "center",
        fontSize: "10px", fontWeight: "600",
        flexShrink: 0, marginTop: "2px",
      }}>
        {index + 1}
      </span>

      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{
          fontSize: "13px",
          color: "var(--text-primary)",
          lineHeight: "1.5",
          marginBottom: "8px",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
          wordBreak: "break-word",
        }}>
          {result.title}
        </p>

        <div style={{
          display: "flex", flexWrap: "wrap",
          alignItems: "center", gap: "6px",
        }}>
          <span style={{
            fontSize: "10px", fontWeight: "600",
            color: color,
            background: color + "18",
            border: "1px solid " + color + "30",
            borderRadius: "4px",
            padding: "2px 7px",
            whiteSpace: "nowrap",
          }}>
            {"r/" + result.subreddit}
          </span>

          {result.score > 0 && (
            <span style={{ fontSize: "10px", color: "var(--text-dim)" }}>
              {"↑ " + result.score.toLocaleString()}
            </span>
          )}

          {date && (
            <span className="mono" style={{ fontSize: "10px", color: "var(--text-dim)" }}>
              {date}
            </span>
          )}

          <span style={{
            marginLeft: "auto",
            fontSize: "10px", fontWeight: "700",
            color: simColor,
            background: simColor + "15",
            border: "1px solid " + simColor + "25",
            borderRadius: "999px",
            padding: "2px 8px",
            whiteSpace: "nowrap",
          }}>
            {sim + "% match"}
          </span>
        </div>
      </div>
    </a>
  )
}

// ── Suggestion chip ───────────────────────────────────────────────────────────
function SuggestionChip({ text, onClick }) {
  return (
    <button
      onClick={function () { onClick(text) }}
      className="sp-sugg-chip"
      style={{ fontFamily: "inherit" }}
    >
      {text + " →"}
    </button>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function SearchPanel({ filters }) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingSugg, setLoadingSugg] = useState(false)
  const [error, setError] = useState(null)
  const [lastQuery, setLastQuery] = useState("")
  const [blocFilter, setBlocFilter] = useState("all")
  const [showExamples, setShowExamples] = useState(false)
  const [pageSize, setPageSize] = useState(PAGE_SIZE)
  const inputRef = useRef(null)

  // ── Derive sidebar bloc context ─────────────────────────────────────────────
  const sidebarBloc = filters && filters.subreddit !== "all"
    ? (SUBREDDIT_TO_BLOC[filters.subreddit] || "all")
    : "all"

  // User's manual pill selection takes priority.
  // If user hasn't manually picked a filter, use sidebar context.
  const activeBloc = blocFilter !== "all" ? blocFilter : sidebarBloc

  const isSidebarControlling = blocFilter === "all" && sidebarBloc !== "all"

  const doSearch = async function (q) {
    const trimmed = (q || "").trim()
    if (!trimmed || trimmed.length < 2) {
      setResults({ results: [], total: 0, query: trimmed, warning: true })
      return
    }
    setLoading(true)
    setError(null)
    setResults(null)
    setSuggestions([])
    setLastQuery(trimmed)
    setBlocFilter("all")  // reset manual filter on new search
    setPageSize(PAGE_SIZE)

    try {
      const res = await axios.get(BASE + "/api/search", {
        params: { q: trimmed, limit: 25 },
      })
      setResults(res.data)
      setLoading(false)

      if (res.data.results && res.data.results.length > 0) {
        setLoadingSugg(true)
        axios
          .post(BASE + "/api/suggest_queries", {
            query: trimmed,
            results: res.data.results.slice(0, 5),
          })
          .then(function (r) {
            setSuggestions(r.data.suggestions || [])
            setLoadingSugg(false)
          })
          .catch(function () { setLoadingSugg(false) })
      }
    } catch (e) {
      setError("Search failed — check that the backend is running.")
      setLoading(false)
    }
  }

  const handleSuggestionClick = function (s) {
    setQuery(s)
    doSearch(s)
    if (inputRef.current) inputRef.current.focus()
  }

  const allResults = (results && results.results) ? results.results : []

  // Apply active bloc filter (either from sidebar or manual pill)
  const filtered = activeBloc === "all"
    ? allResults
    : allResults.filter(function (r) { return r.ideological_bloc === activeBloc })

  const displayed = filtered.slice(0, pageSize)
  const remaining = filtered.length - pageSize
  const hasMore = remaining > 0

  return (
    <section style={{ width: "100%" }}>
      <style>{`
        .sp-card {
          padding: 12px 14px;
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border, rgba(255,255,255,0.07));
          border-radius: 8px;
          transition: background 0.15s;
        }
        .sp-card:hover { background: rgba(255,255,255,0.055); }
        .sp-sugg-chip {
          padding: 5px 13px;
          border-radius: 999px;
          font-size: 12px;
          cursor: pointer;
          border: 1px solid rgba(79,142,247,0.2);
          background: rgba(79,142,247,0.06);
          color: #93bbfd;
          transition: background 0.15s, color 0.15s;
        }
        .sp-sugg-chip:hover {
          background: rgba(79,142,247,0.14);
          color: #c3d9ff;
        }
        .sp-examples-panel {
          animation: spFadeIn 0.2s ease;
        }
        @keyframes spFadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .sp-showmore-btn {
          background: transparent;
          border: 1px solid var(--border, rgba(255,255,255,0.08));
          border-radius: 8px;
          color: var(--text-sec, #94a3b8);
          font-size: 12px;
          padding: 8px 22px;
          cursor: pointer;
          transition: border-color 0.15s, color 0.15s;
          font-family: inherit;
          width: 100%;
        }
        .sp-showmore-btn:hover {
          border-color: rgba(255,255,255,0.15);
          color: var(--text-primary, #f1f5f9);
        }
      `}</style>

      {/* ── Header ── */}
      <div style={{ marginBottom: "22px" }}>
        <p className="sec-title">Semantic Search</p>
        <p className="sec-desc">
          Describe what you're looking for — not the exact words, but the idea.
          The engine maps concepts across languages and surfaces posts that carry
          the same meaning even when no words match.
        </p>
      </div>

      {/* ── Sidebar context banner — shown when sidebar is filtering ── */}
      {sidebarBloc !== "all" && (
        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          padding: "8px 14px",
          background: (BLOC_COLORS[sidebarBloc] || "var(--blue)") + "08",
          border: "1px solid " + (BLOC_COLORS[sidebarBloc] || "var(--blue)") + "25",
          borderLeft: "3px solid " + (BLOC_COLORS[sidebarBloc] || "var(--blue)"),
          borderRadius: "var(--r-sm)",
          marginBottom: "14px",
          fontSize: "11px",
        }}>
          <span style={{ color: "var(--text-dim)" }}>
            Sidebar context:
          </span>
          <span style={{
            color: BLOC_COLORS[sidebarBloc] || "var(--blue)",
            fontWeight: "600",
          }}>
            {"r/" + filters.subreddit}
          </span>
          <span style={{ color: "var(--text-dim)" }}>
            {"→ " + sidebarBloc.replace("_", " ") + " bloc"}
          </span>
          {isSidebarControlling && results && allResults.length > 0 && (
            <span style={{
              marginLeft: "4px",
              fontSize: "10px",
              color: BLOC_COLORS[sidebarBloc] || "var(--blue)",
            }}>
              · filtering results
            </span>
          )}
          {isSidebarControlling && (
            <button
              onClick={function () {
                setBlocFilter("left_radical") // force "all" by cycling
                setTimeout(function () { setBlocFilter("all") }, 0)
              }}
              style={{
                marginLeft: "auto",
                background: "none", border: "none",
                color: "var(--text-dim)", cursor: "pointer",
                fontSize: "11px", fontFamily: "inherit",
                padding: "0 2px",
                transition: "color 0.15s",
              }}
              onMouseEnter={function (e) {
                e.currentTarget.style.color = "var(--text-primary)"
              }}
              onMouseLeave={function (e) {
                e.currentTarget.style.color = "var(--text-dim)"
              }}
            >
              show all ×
            </button>
          )}
        </div>
      )}

      {/* ── Search input ── */}
      <div style={{ display: "flex", gap: "10px", marginBottom: "14px" }}>
        <input
          ref={inputRef}
          value={query}
          onChange={function (e) { setQuery(e.target.value) }}
          onKeyDown={function (e) { if (e.key === "Enter") doSearch(query) }}
          placeholder="Search by topic, theme, or concept (any language)..."
          className="input"
          style={{ flex: 1 }}
        />
        <button
          onClick={function () { doSearch(query) }}
          disabled={loading}
          className="btn btn-blue"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {/* ── Short query warning ── */}
      {query.length > 0 && query.trim().length < 2 && (
        <p style={{ fontSize: "11px", color: "#fbbf24", marginBottom: "12px" }}>
          Please enter at least 2 characters
        </p>
      )}

      {/* ── Semantic examples toggle ── */}
      <div style={{ marginBottom: "20px" }}>
        <button
          onClick={function () { setShowExamples(function (v) { return !v }) }}
          style={{
            background: "none", border: "none",
            fontSize: "11px", color: "var(--text-dim)",
            cursor: "pointer", fontFamily: "inherit",
            padding: 0, transition: "color 0.15s",
          }}
          onMouseEnter={function (e) {
            e.currentTarget.style.color = "var(--text-sec)"
          }}
          onMouseLeave={function (e) {
            e.currentTarget.style.color = "var(--text-dim)"
          }}
        >
          {(showExamples ? "▲ Hide" : "▼ Show") +
            " semantic search examples (zero keyword overlap)"}
        </button>

        {showExamples && (
          <div className="sp-examples-panel" style={{
            marginTop: "10px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "10px",
            overflow: "hidden",
          }}>
            {SEMANTIC_EXAMPLES.map(function (ex, i) {
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "flex-start",
                  gap: "12px", padding: "12px 14px",
                  borderBottom: i < SEMANTIC_EXAMPLES.length - 1
                    ? "1px solid var(--border)" : "none",
                }}>
                  <span style={{
                    padding: "2px 7px", borderRadius: "4px",
                    fontSize: "10px", fontWeight: "700",
                    flexShrink: 0, marginTop: "2px",
                    background: ex.lang === "HI"
                      ? "rgba(251,146,60,0.15)"
                      : "rgba(79,142,247,0.15)",
                    color: ex.lang === "HI" ? "#fb923c" : "#4f8ef7",
                    border: "1px solid " + (ex.lang === "HI"
                      ? "rgba(251,146,60,0.25)"
                      : "rgba(79,142,247,0.25)"),
                  }}>
                    {ex.lang}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <button
                      onClick={function () { setQuery(ex.query); doSearch(ex.query) }}
                      style={{
                        background: "none", border: "none",
                        padding: 0, cursor: "pointer",
                        fontSize: "12px", color: "#4f8ef7",
                        textAlign: "left", fontFamily: "inherit",
                        lineHeight: "1.5", wordBreak: "break-word",
                        transition: "color 0.15s",
                      }}
                      onMouseEnter={function (e) {
                        e.currentTarget.style.color = "#93bbfd"
                      }}
                      onMouseLeave={function (e) {
                        e.currentTarget.style.color = "#4f8ef7"
                      }}
                    >
                      {'"' + ex.query + '"'}
                    </button>
                    <p style={{
                      fontSize: "10px", color: "var(--text-dim)",
                      marginTop: "3px", lineHeight: "1.5",
                    }}>
                      {ex.note}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

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
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {[1, 2, 3, 4, 5].map(function (i) {
            return (
              <div key={i} className="skeleton"
                style={{ height: "68px", borderRadius: "8px" }} />
            )
          })}
        </div>
      )}

      {/* ── Results ── */}
      {results && !loading && (
        <div>
          {/* Count + bloc filters row */}
          <div style={{
            display: "flex", alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap", gap: "10px",
            marginBottom: "16px",
          }}>
            <p style={{ fontSize: "11px", color: "var(--text-sec)" }}>
              {results.warning && (
                <span style={{ color: "#fbbf24" }}>
                  Query too short — enter at least 2 characters
                </span>
              )}
              {!results.warning && results.total === 0 && (
                <span>
                  {"No results for "}
                  <span style={{ color: "var(--text-primary)" }}>
                    {'"' + lastQuery + '"'}
                  </span>
                </span>
              )}
              {!results.warning && results.total > 0 && (
                <span>
                  <span className="mono" style={{
                    color: "var(--text-primary)", fontWeight: "600",
                  }}>
                    {isSidebarControlling
                      ? filtered.length + " of " + results.total
                      : results.total
                    }
                  </span>
                  {isSidebarControlling
                    ? " results in " + sidebarBloc.replace("_", " ") + " for "
                    : " results for "
                  }
                  <span style={{ color: "var(--text-primary)" }}>
                    {'"' + lastQuery + '"'}
                  </span>
                </span>
              )}
            </p>

            {/* Bloc filter pills */}
            {results.total > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                {BLOC_FILTERS.map(function (f) {
                  const cnt = f.key === "all"
                    ? allResults.length
                    : allResults.filter(function (r) {
                      return r.ideological_bloc === f.key
                    }).length

                  // Highlight pill that matches sidebar bloc if no manual filter
                  const isActive = blocFilter === f.key ||
                    (blocFilter === "all" && f.key === sidebarBloc &&
                      sidebarBloc !== "all")

                  return (
                    <button
                      key={f.key}
                      onClick={function () {
                        // If clicking the currently sidebar-active pill, clear manual
                        if (f.key === sidebarBloc && blocFilter === "all") {
                          setBlocFilter("all")
                        } else {
                          setBlocFilter(f.key)
                        }
                        setPageSize(PAGE_SIZE)
                      }}
                      style={getFilterBtnStyle(isActive, f.key)}
                    >
                      {f.label + " " + cnt}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Zero results */}
          {results.total === 0 && !results.warning && (
            <div style={{
              padding: "48px 24px", textAlign: "center",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
            }}>
              <p style={{ fontSize: "13px", color: "var(--text-sec)", marginBottom: "4px" }}>
                No posts found matching that query
              </p>
              <p style={{ fontSize: "11px", color: "var(--text-dim)" }}>
                Try a broader or different term
              </p>
            </div>
          )}

          {/* Filtered returns zero */}
          {results.total > 0 && filtered.length === 0 && (
            <div style={{
              padding: "32px 24px", textAlign: "center",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: "10px",
              marginBottom: "10px",
            }}>
              <p style={{
                fontSize: "13px", color: "var(--text-sec)", marginBottom: "6px",
              }}>
                No results from this community for that query
              </p>
              <button
                onClick={function () { setBlocFilter("all") }}
                style={{
                  background: "none", border: "none",
                  color: "var(--blue, #4f8ef7)",
                  fontSize: "12px", cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                Show all communities →
              </button>
            </div>
          )}

          {/* Result cards */}
          {displayed.length > 0 && (
            <div style={{ marginBottom: "10px" }}>
              {displayed.map(function (r, i) {
                return <ResultCard key={i} result={r} index={i} />
              })}
            </div>
          )}

          {/* Show more */}
          {hasMore && (
            <div style={{ marginBottom: "16px" }}>
              <button
                className="sp-showmore-btn"
                onClick={function () {
                  setPageSize(function (p) { return p + PAGE_SIZE })
                }}
              >
                <span style={{ color: "var(--text-dim)" }}>
                  {"Showing " + displayed.length + " of " + filtered.length + " — "}
                </span>
                {"Show " + Math.min(PAGE_SIZE, remaining) + " more"}
              </button>
            </div>
          )}

          {/* All shown */}
          {!hasMore && filtered.length > PAGE_SIZE && (
            <div style={{
              padding: "8px 0",
              borderTop: "1px solid var(--border)",
              marginBottom: "16px",
            }}>
              <p style={{
                fontSize: "10px", color: "var(--text-dim)",
                textAlign: "center",
                textTransform: "uppercase", letterSpacing: "0.08em",
              }}>
                {"All " + filtered.length + " results shown"}
              </p>
            </div>
          )}

          {/* Query suggestions */}
          {(suggestions.length > 0 || loadingSugg) && (
            <div style={{
              paddingTop: "16px",
              borderTop: "1px solid var(--border)",
            }}>
              <p style={{
                fontSize: "9px", fontWeight: "600",
                color: "var(--text-dim)",
                textTransform: "uppercase", letterSpacing: "0.1em",
                marginBottom: "10px",
              }}>
                Explore related topics
              </p>
              {loadingSugg ? (
                <div style={{ display: "flex", gap: "8px" }}>
                  {[1, 2, 3].map(function (i) {
                    return (
                      <div key={i} className="skeleton"
                        style={{ height: "30px", width: "120px", borderRadius: "999px" }} />
                    )
                  })}
                </div>
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                  {suggestions.map(function (s, i) {
                    return (
                      <SuggestionChip
                        key={i}
                        text={s}
                        onClick={handleSuggestionClick}
                      />
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
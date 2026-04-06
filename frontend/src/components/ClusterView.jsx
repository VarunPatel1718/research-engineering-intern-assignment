import { useState, useRef, useEffect, memo } from "react"
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, Cell } from "recharts"
import { useApi } from "../hooks/useApi"

const CLUSTER_COLORS = [
  "#4f8ef7", "#f87171", "#fb923c", "#34d399", "#c084fc",
  "#fbbf24", "#22d3ee", "#f472b6", "#a3e635", "#818cf8",
  "#2dd4bf", "#fb7185", "#a78bfa", "#67e8f9", "#fdba74",
  "#bef264", "#e879f9", "#6ee7b7", "#fda4af", "#93c5fd",
]

function getClusterColor(clusterId) {
  if (clusterId === -1) return "rgba(255,255,255,0.06)"
  return CLUSTER_COLORS[(clusterId + 1) % CLUSTER_COLORS.length]
}

function ScatterTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  return (
    <div style={{
      background: "var(--bg-elevated, #0e1628)",
      border: "1px solid var(--border)",
      borderRadius: "8px",
      padding: "10px 14px",
      maxWidth: "220px",
    }}>
      <p style={{
        fontSize: "12px", color: "var(--text-primary)",
        marginBottom: "6px", lineHeight: "1.5",
        display: "-webkit-box", WebkitLineClamp: 3,
        WebkitBoxOrient: "vertical", overflow: "hidden",
        wordBreak: "break-word",
      }}>
        {d.title}
      </p>
      <p style={{ fontSize: "10px", color: "var(--text-sec)" }}>
        {"r/" + d.subreddit}
      </p>
      {d.cluster !== -1 && (
        <p style={{
          fontSize: "10px", fontWeight: "600",
          color: getClusterColor(d.cluster), marginTop: "3px",
        }}>
          {"Cluster " + d.cluster}
        </p>
      )}
      {d.cluster === -1 && (
        <p style={{ fontSize: "10px", color: "var(--text-dim)", marginTop: "3px" }}>
          Noise point
        </p>
      )}
    </div>
  )
}

const ClusterCard = memo(function ClusterCard({ clusterId, terms }) {
  const color = getClusterColor(Number(clusterId))
  return (
    <div style={{
      padding: "12px",
      background: "var(--bg-card)",
      border: "1px solid var(--border)",
      borderTop: "2px solid " + color,
      borderRadius: "var(--r-md, 10px)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "10px" }}>
        <div style={{
          width: "8px", height: "8px", borderRadius: "50%",
          background: color, flexShrink: 0,
        }} />
        <span style={{
          fontSize: "10px", fontWeight: "600",
          color: "var(--text-dim)",
          textTransform: "uppercase", letterSpacing: "0.08em",
        }}>
          {"Cluster " + clusterId}
        </span>
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
        {terms.map(function (t) {
          return (
            <span key={t} style={{
              fontSize: "10px", fontWeight: "500",
              color: color,
              background: color + "15",
              border: "1px solid " + color + "30",
              borderRadius: "999px",
              padding: "2px 8px",
            }}>
              {t}
            </span>
          )
        })}
      </div>
    </div>
  )
})

// ClusterView receives no props from App filters — safe to memo
function ClusterView() {
  const [k, setK] = useState(8)

  const chartContainerRef = useRef(null)
  const [chartWidth, setChartWidth] = useState(800)

  useEffect(function () {
    function measure() {
      if (!chartContainerRef.current) return
      const w = chartContainerRef.current.getBoundingClientRect().width
      if (w > 0) setChartWidth(Math.floor(w) - 24)
    }
    measure()
    const observer = new ResizeObserver(measure)
    if (chartContainerRef.current) observer.observe(chartContainerRef.current)
    const t = setTimeout(measure, 150)
    return function () { observer.disconnect(); clearTimeout(t) }
  }, [])

  const { data, loading, error } = useApi("/api/clusters", { k })

  const allPoints = data ? data.points || [] : []
  const clustered = allPoints.filter(function (p) { return p.cluster !== -1 })
  const noise = allPoints.filter(function (p) { return p.cluster === -1 })
  const labelEntries = data ? Object.entries(data.cluster_labels || {}) : []

  return (
    <section style={{ width: "100%" }}>

      {/* Header */}
      <div style={{ marginBottom: "22px" }}>
        <div style={{
          display: "flex", alignItems: "flex-start",
          justifyContent: "space-between",
          flexWrap: "wrap", gap: "14px",
        }}>
          <div>
            <p className="sec-title">Topic Clusters</p>
            <p className="sec-desc">
              8,799 posts clustered by semantic similarity using HDBSCAN on
              384-dimensional sentence embeddings. Adjust the slider to explore
              different cluster granularities. Gray dots = noise (no cluster assigned).
            </p>
          </div>

          <div style={{
            display: "flex", alignItems: "center", gap: "12px",
            padding: "10px 16px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-sm)",
            flexShrink: 0,
          }}>
            <span style={{
              fontSize: "10px", fontWeight: "600",
              color: "var(--text-dim)",
              textTransform: "uppercase", letterSpacing: "0.08em",
            }}>
              Clusters
            </span>
            <input
              type="range" min={5} max={20} step={1} value={k}
              onChange={function (e) { setK(Number(e.target.value)) }}
              style={{ width: "100px" }}
            />
            <span className="mono" style={{
              fontSize: "18px", fontWeight: "700",
              color: "var(--blue, #4f8ef7)",
              minWidth: "28px", textAlign: "center", lineHeight: 1,
            }}>
              {k}
            </span>
          </div>
        </div>
      </div>

      {/* Stats strip */}
      {data && !loading && (
        <div style={{
          display: "flex", gap: "10px",
          flexWrap: "wrap", marginBottom: "16px",
        }}>
          {[
            { label: "Clusters Found", value: data.cluster_count, color: "var(--blue, #4f8ef7)" },
            { label: "Noise Points", value: data.noise_count, color: "var(--text-dim)" },
            { label: "Total Posts", value: allPoints.length, color: "var(--text-primary)" },
          ].map(function (item) {
            return (
              <div key={item.label} style={{
                flex: "1", minWidth: "120px",
                padding: "12px 14px",
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--r-md, 10px)",
              }}>
                <p style={{
                  fontSize: "9px", fontWeight: "600",
                  color: "var(--text-dim)",
                  textTransform: "uppercase", letterSpacing: "0.1em",
                  marginBottom: "6px",
                }}>
                  {item.label}
                </p>
                <p className="mono" style={{
                  fontSize: "20px", fontWeight: "700",
                  color: item.color, lineHeight: 1,
                }}>
                  {item.value}
                </p>
              </div>
            )
          })}

          {data.k_actual !== data.k_requested && (
            <div style={{
              alignSelf: "center",
              fontSize: "11px", color: "#fbbf24",
              padding: "4px 10px",
              background: "rgba(251,191,36,0.06)",
              border: "1px solid rgba(251,191,36,0.15)",
              borderRadius: "999px",
            }}>
              {"Showing k=" + data.k_actual + " — nearest to " + data.k_requested}
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="skeleton"
          style={{ height: "400px", borderRadius: "var(--r-md, 10px)" }} />
      )}

      {error && !loading && (
        <div style={{
          padding: "14px 16px",
          background: "rgba(248,113,113,0.06)",
          border: "1px solid rgba(248,113,113,0.2)",
          borderLeft: "3px solid #f87171",
          borderRadius: "var(--r-sm)",
          color: "#fca5a5", fontSize: "13px",
          marginBottom: "16px",
        }}>
          Failed to load clusters — check that the backend is running
        </div>
      )}

      {/* Scatter chart */}
      {data && !loading && allPoints.length > 0 && (
        <div
          ref={chartContainerRef}
          style={{
            background: "var(--bg-base, #02060f)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-md, 10px)",
            padding: "12px",
            marginBottom: "16px",
            width: "100%",
            boxSizing: "border-box",
          }}
        >
          <ScatterChart
            width={chartWidth}
            height={360}
            margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
          >
            <XAxis dataKey="x" type="number" hide />
            <YAxis dataKey="y" type="number" hide />
            <Tooltip cursor={false} content={<ScatterTooltip />} />
            <Scatter data={noise} name="noise">
              {noise.map(function (_, i) {
                return <Cell key={i} fill="rgba(255,255,255,0.06)" opacity={0.6} />
              })}
            </Scatter>
            <Scatter data={clustered} name="clusters">
              {clustered.map(function (p, i) {
                return <Cell key={i} fill={getClusterColor(p.cluster)} opacity={0.8} />
              })}
            </Scatter>
          </ScatterChart>
        </div>
      )}

      {/* Cluster keyword cards */}
      {labelEntries.length > 0 && !loading && (
        <div style={{ marginBottom: "20px" }}>
          <p style={{
            fontSize: "9px", fontWeight: "600",
            color: "var(--text-dim)",
            textTransform: "uppercase", letterSpacing: "0.1em",
            marginBottom: "10px",
          }}>
            Top Keywords per Cluster (TF-IDF)
          </p>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
            gap: "8px",
          }}>
            {labelEntries.map(function (entry) {
              return (
                <ClusterCard key={entry[0]} clusterId={entry[0]} terms={entry[1]} />
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}

// memo — ClusterView takes no filters prop, never needs to re-render on sidebar changes
export default memo(ClusterView)
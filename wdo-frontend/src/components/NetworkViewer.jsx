import { useEffect, useRef, useState, useCallback } from 'react'
import { api } from '../api'
import { useStore } from '../store/useStore'
import styles from './NetworkViewer.module.css'

// ── Colour scale: pressure → colour ──────────────────────────────────────────
function pressureColor(pressure, minP, maxP, belowMin) {
  if (belowMin) return '#ff4d6a'         // red  = below threshold (deficit)
  if (maxP === minP) return '#00d4ff'
  const t = Math.max(0, Math.min(1, (pressure - minP) / (maxP - minP)))
  // Cool blue (low) → cyan (mid) → green (high)
  if (t < 0.5) {
    const s = t / 0.5
    return `rgb(${Math.round(255 * (1-s))}, ${Math.round(212 + 43*s)}, 255)`
  } else {
    const s = (t - 0.5) / 0.5
    return `rgb(0, ${Math.round(255 - 55*s)}, ${Math.round(255 - 155*s)})`
  }
}

// ── Flow width scale ──────────────────────────────────────────────────────────
function flowWidth(flow, maxFlow) {
  if (!maxFlow || maxFlow === 0) return 2
  return Math.max(1.5, Math.min(6, (flow / maxFlow) * 6))
}

// ── Node radius by type ───────────────────────────────────────────────────────
function nodeRadius(type) {
  if (type === 'RESERVOIR') return 14
  if (type === 'TANK')      return 11
  if (type === 'PUMP')      return 9
  return 7
}

// ── Normalise coordinates to fit SVG canvas ───────────────────────────────────
function normaliseCoords(nodes, width, height, padding = 60) {
  if (!nodes.length) return nodes
  const xs = nodes.map(n => n.x).filter(Boolean)
  const ys = nodes.map(n => n.y).filter(Boolean)
  if (!xs.length || !ys.length) return nodes

  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const rangeX = maxX - minX || 1
  const rangeY = maxY - minY || 1
  const scaleX = (width  - padding * 2) / rangeX
  const scaleY = (height - padding * 2) / rangeY
  const scale  = Math.min(scaleX, scaleY)

  return nodes.map(n => ({
    ...n,
    sx: padding + (n.x - minX) * scale,
    sy: height - padding - (n.y - minY) * scale,   // flip Y axis
  }))
}

// ─────────────────────────────────────────────────────────────────────────────

export default function NetworkViewer() {
  const { networkFile, results } = useStore()

  const [baselineTopo, setBaselineTopo]   = useState(null)
  const [optimizedTopo, setOptimizedTopo] = useState(null)
  const [loading, setLoading]             = useState(false)
  const [error, setError]                 = useState(null)
  const [viewMode, setViewMode]           = useState('split') // 'split'|'before'|'after'
  const [hovered, setHovered]             = useState(null)    // hovered node id
  const [zoom, setZoom]                   = useState(1)
  const [pan, setPan]                     = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning]         = useState(false)
  const panStart = useRef(null)

  const W = 680, H = 520

  // ── Load topologies ─────────────────────────────────────────────────────
  useEffect(() => {
    setLoading(true)
    setError(null)

    const baselineReq = api.getSimulatedTopology(networkFile, 'baseline')

    const requests = [baselineReq]

    // If we have optimization results, also fetch optimized topology
    const knee = results?.knee_solution
    if (knee?.chromosome) {
      requests.push(
        api.getChromosomeTopology(networkFile, knee.chromosome)
      )
    }

    Promise.all(requests)
      .then(([bl, opt]) => {
        setBaselineTopo(bl)
        setOptimizedTopo(opt || null)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [networkFile, results])

  // ── Zoom / pan handlers ─────────────────────────────────────────────────
  const handleWheel = useCallback((e) => {
    e.preventDefault()
    setZoom(z => Math.max(0.4, Math.min(4, z - e.deltaY * 0.001)))
  }, [])

  const handleMouseDown = (e) => {
    setIsPanning(true)
    panStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
  }
  const handleMouseMove = (e) => {
    if (!isPanning || !panStart.current) return
    setPan({ x: e.clientX - panStart.current.x, y: e.clientY - panStart.current.y })
  }
  const handleMouseUp = () => { setIsPanning(false); panStart.current = null }

  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }) }

  // ── Render one SVG network ──────────────────────────────────────────────
  const renderNetwork = (topo, label, accentColor) => {
    if (!topo) return null

    const nodeMap  = Object.fromEntries(topo.nodes.map(n => [n.id, n]))
    const normNodes = normaliseCoords(topo.nodes, W, H)
    const normMap  = Object.fromEntries(normNodes.map(n => [n.id, n]))

    const pressures = normNodes.map(n => n.pressure ?? 0)
    const minP = Math.min(...pressures)
    const maxP = Math.max(...pressures)
    const maxFlow = Math.max(...(topo.links.map(l => l.flow ?? 0)))
    const minThreshold = topo.min_pressure_threshold ?? 10.0

    return (
      <div className={styles.svgWrap}>
        {/* Label */}
        <div className={styles.svgLabel} style={{ borderColor: accentColor, color: accentColor }}>
          {label}
        </div>

        {/* Metrics strip */}
        <div className={styles.metricStrip}>
          <MetricChip label="Energy" value={`₦${(topo.energy_cost ?? 0).toFixed(0)}`} color={accentColor} />
          <MetricChip label="Pressure Var" value={(topo.pressure_variance ?? 0).toFixed(3)} color={accentColor} />
          <MetricChip label="Deficit" value={(topo.pressure_deficit ?? 0).toFixed(2)} color={accentColor} />
          <MetricChip label="Avg P" value={`${(topo.avg_pressure ?? 0).toFixed(1)}m`} color={accentColor} />
        </div>

        <svg
          width="100%" viewBox={`0 0 ${W} ${H}`}
          className={styles.svg}
          style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <defs>
            {/* Glow filter for highlighted elements */}
            <filter id={`glow-${label}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            {/* Grid pattern */}
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" strokeWidth="0.5"/>
            </pattern>
          </defs>

          {/* Background grid */}
          <rect width={W} height={H} fill="url(#grid)" />

          <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}
             style={{ transformOrigin: `${W/2}px ${H/2}px` }}>

            {/* ── Links ── */}
            {topo.links.map(link => {
              const src = normMap[link.source]
              const tgt = normMap[link.target]
              if (!src?.sx || !tgt?.sx) return null

              const isPump  = link.type === 'PUMP'
              const isValve = ['PRV','PSV','FCV','TCV','GPV','PBV'].includes(link.type)
              const lw = flowWidth(link.flow ?? 0, maxFlow)

              // Color by type
              let strokeColor = 'rgba(255,255,255,0.18)'
              if (isPump)  strokeColor = '#ffb340'
              if (isValve) strokeColor = '#a78bfa'

              const mx = (src.sx + tgt.sx) / 2
              const my = (src.sy + tgt.sy) / 2

              return (
                <g key={link.id}>
                  <line
                    x1={src.sx} y1={src.sy} x2={tgt.sx} y2={tgt.sy}
                    stroke={strokeColor}
                    strokeWidth={lw}
                    strokeLinecap="round"
                    opacity={0.85}
                  />
                  {/* Flow direction arrow at midpoint */}
                  {(link.flow ?? 0) > 0.01 && (
                    <circle cx={mx} cy={my} r={2} fill={strokeColor} opacity={0.6} />
                  )}
                  {/* Velocity label on hover - shown for all links */}
                  {hovered === `link-${link.id}` && (
                    <text x={mx + 4} y={my - 4}
                      fill="white" fontSize="9"
                      fontFamily="var(--font-mono)">
                      {(link.velocity ?? 0).toFixed(2)} m/s
                    </text>
                  )}
                  {/* Invisible hit area */}
                  <line
                    x1={src.sx} y1={src.sy} x2={tgt.sx} y2={tgt.sy}
                    stroke="transparent" strokeWidth={10}
                    onMouseEnter={() => setHovered(`link-${link.id}`)}
                    onMouseLeave={() => setHovered(null)}
                  />
                </g>
              )
            })}

            {/* ── Nodes ── */}
            {normNodes.map(node => {
              const isHovered = hovered === `node-${node.id}`
              const belowMin  = (node.pressure ?? 0) < minThreshold
              const color     = pressureColor(node.pressure ?? 0, minP, maxP, belowMin)
              const r         = nodeRadius(node.type)

              return (
                <g key={node.id}
                  onMouseEnter={() => setHovered(`node-${node.id}`)}
                  onMouseLeave={() => setHovered(null)}
                  style={{ cursor: 'pointer' }}>

                  {/* Outer glow ring when hovered or below min pressure */}
                  {(isHovered || belowMin) && (
                    <circle
                      cx={node.sx} cy={node.sy}
                      r={r + 5}
                      fill="none"
                      stroke={belowMin ? '#ff4d6a' : 'white'}
                      strokeWidth={1}
                      opacity={0.5}
                      strokeDasharray={belowMin ? '3 2' : 'none'}
                    />
                  )}

                  {/* Main node circle */}
                  <circle
                    cx={node.sx} cy={node.sy} r={r}
                    fill={color}
                    stroke={isHovered ? 'white' : 'rgba(0,0,0,0.4)'}
                    strokeWidth={isHovered ? 1.5 : 1}
                    filter={isHovered ? `url(#glow-${label})` : undefined}
                  />

                  {/* Icon for special node types */}
                  {node.type === 'RESERVOIR' && (
                    <text x={node.sx} y={node.sy + 4}
                      textAnchor="middle" fontSize="10"
                      fontFamily="var(--font-mono)" fill="#0a0e1a" fontWeight="700">R</text>
                  )}
                  {node.type === 'TANK' && (
                    <text x={node.sx} y={node.sy + 3.5}
                      textAnchor="middle" fontSize="9"
                      fontFamily="var(--font-mono)" fill="#0a0e1a" fontWeight="700">T</text>
                  )}

                  {/* Tooltip on hover */}
                  {isHovered && (
                    <g>
                      <rect
                        x={node.sx + r + 4} y={node.sy - 36}
                        width={130} height={60}
                        rx={5}
                        fill="rgba(10,14,26,0.95)"
                        stroke="rgba(255,255,255,0.15)"
                        strokeWidth={0.8}
                      />
                      <text x={node.sx + r + 10} y={node.sy - 22}
                        fontSize="9" fontFamily="var(--font-mono)" fill="rgba(255,255,255,0.5)">
                        {node.name} · {node.type}
                      </text>
                      <text x={node.sx + r + 10} y={node.sy - 10}
                        fontSize="10" fontFamily="var(--font-mono)"
                        fill={belowMin ? '#ff4d6a' : '#00d4ff'} fontWeight="500">
                        P: {(node.pressure ?? 0).toFixed(2)} m
                        {belowMin ? ' ⚠' : ''}
                      </text>
                      <text x={node.sx + r + 10} y={node.sy + 2}
                        fontSize="9" fontFamily="var(--font-mono)" fill="rgba(255,255,255,0.4)">
                        Elev: {node.elevation?.toFixed(1) ?? '—'} m
                      </text>
                    </g>
                  )}
                </g>
              )
            })}
          </g>
        </svg>

        {/* Pressure legend */}
        <PressureLegend minP={minP} maxP={maxP} threshold={minThreshold} />
      </div>
    )
  }

  const knee = results?.knee_solution

  return (
    <div className={styles.container}>
      {/* ── Toolbar ── */}
      <div className={styles.toolbar}>
        <div className={styles.toolbarLeft}>
          <span className={styles.toolbarTitle}>Network Visualizer</span>
          {baselineTopo && (
            <span className={styles.networkInfo}>
              {baselineTopo.num_nodes} nodes · {baselineTopo.num_links} links
            </span>
          )}
        </div>

        <div className={styles.viewToggle}>
          {['before', 'split', 'after'].map(m => (
            <button
              key={m}
              onClick={() => setViewMode(m)}
              className={`${styles.toggleBtn} ${viewMode === m ? styles.activeToggle : ''}`}
            >
              {m === 'split' ? '⊟ Split' : m === 'before' ? '← Before' : 'After →'}
            </button>
          ))}
        </div>

        <div className={styles.toolbarRight}>
          <button className={styles.iconBtn} onClick={resetView} title="Reset view">⊙</button>
          <button className={styles.iconBtn} onClick={() => setZoom(z => Math.min(4, z + 0.2))} title="Zoom in">+</button>
          <button className={styles.iconBtn} onClick={() => setZoom(z => Math.max(0.4, z - 0.2))} title="Zoom out">−</button>
        </div>
      </div>

      {/* ── Legend ── */}
      <div className={styles.legend}>
        <LegendItem color="#ff4d6a"            label="Below min pressure (deficit)" />
        <LegendItem color="rgb(0,212,255)"     label="Low pressure" />
        <LegendItem color="rgb(0,255,200)"     label="High pressure" />
        <LegendItem color="#ffb340"            label="Pump" dash />
        <LegendItem color="#a78bfa"            label="Valve" dash />
        <LegendItem color="rgba(255,255,255,0.18)" label="Pipe" dash />
      </div>

      {/* ── Main canvas ── */}
      {loading && (
        <div className={styles.loadingOverlay}>
          <div className={styles.spinner} />
          <span>Simulating network...</span>
        </div>
      )}

      {error && (
        <div className={styles.errorBanner}>
          ⚠ {error}
        </div>
      )}

      {!loading && !error && (
        <div className={`${styles.canvas} ${styles[viewMode]}`}>
          {(viewMode === 'before' || viewMode === 'split') &&
            renderNetwork(baselineTopo, 'Baseline (No Optimization)', '#ff4d6a')}

          {(viewMode === 'after' || viewMode === 'split') && (
            optimizedTopo
              ? renderNetwork(optimizedTopo, 'GA Optimized (Knee Point)', '#00e5a0')
              : (
                <div className={styles.noOptimized}>
                  <div className={styles.noOptimizedIcon}>⟳</div>
                  <p>Run optimization to see the improved network</p>
                  <p className={styles.noOptimizedSub}>
                    The optimized view will show pressure changes, reduced deficits,
                    and updated pump/valve settings.
                  </p>
                </div>
              )
          )}
        </div>
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function MetricChip({ label, value, color }) {
  return (
    <div className={styles.metricChip}>
      <span className={styles.metricLabel}>{label}</span>
      <span className={styles.metricValue} style={{ color }}>{value}</span>
    </div>
  )
}

function LegendItem({ color, label, dash }) {
  return (
    <div className={styles.legendItem}>
      {dash
        ? <div className={styles.legendLine} style={{ background: color }} />
        : <div className={styles.legendDot} style={{ background: color }} />
      }
      <span>{label}</span>
    </div>
  )
}

function PressureLegend({ minP, maxP, threshold }) {
  const steps = 5
  return (
    <div className={styles.pressureLegend}>
      <span className={styles.pressureLegendLabel}>Pressure (m)</span>
      <div className={styles.pressureGradient} />
      <div className={styles.pressureScale}>
        {Array.from({ length: steps }, (_, i) => {
          const p = minP + (maxP - minP) * (i / (steps - 1))
          return (
            <span key={i} style={{ color: p < threshold ? '#ff4d6a' : 'var(--text-dim)' }}>
              {p.toFixed(0)}
            </span>
          )
        })}
      </div>
    </div>
  )
}

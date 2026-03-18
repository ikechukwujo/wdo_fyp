import NetworkViewer from '../components/NetworkViewer'
import styles from './ChartPage.module.css'

export default function NetworkPage() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Network Visualization</h1>
          <p className={styles.sub}>
            Pressure heatmap · Flow rates · Before / After optimization
          </p>
        </div>
      </header>

      <NetworkViewer />

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '12px',
        marginTop: '4px'
      }}>
        <InfoCard
          icon="🔵"
          title="Node colours = Pressure"
          body="Red nodes are below the minimum pressure threshold (10m) — these represent deficit zones where water barely reaches consumers. Cyan/green nodes have healthy pressure."
        />
        <InfoCard
          icon="📏"
          title="Link width = Flow rate"
          body="Thicker pipes carry more flow. Orange links are pumps, purple links are valves. Hover any link to see its velocity in m/s."
        />
        <InfoCard
          icon="⚡"
          title="Before vs After"
          body="Use the Split view to compare baseline (default settings) against the GA-optimised network. After optimization, red nodes should reduce and pressure should be more uniform."
        />
      </div>
    </div>
  )
}

function InfoCard({ icon, title, body }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '10px',
      padding: '16px',
    }}>
      <div style={{ fontSize: '18px', marginBottom: '6px' }}>{icon}</div>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontWeight: 700, fontSize: '13px',
        color: 'var(--text)', marginBottom: '6px'
      }}>{title}</div>
      <div style={{
        fontFamily: 'var(--font-body)',
        fontSize: '12px', color: 'var(--text-muted)',
        lineHeight: 1.7
      }}>{body}</div>
    </div>
  )
}

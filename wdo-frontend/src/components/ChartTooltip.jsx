import styles from './ChartTooltip.module.css'

export default function ChartTooltip({ active, payload, label, labelPrefix = '' }) {
  if (!active || !payload?.length) return null

  return (
    <div className={styles.tooltip}>
      {label != null && (
        <div className={styles.label}>{labelPrefix}{label}</div>
      )}
      {payload.map((entry, i) => (
        <div key={i} className={styles.row}>
          <span className={styles.dot} style={{ background: entry.color }} />
          <span className={styles.name}>{entry.name}</span>
          <span className={styles.val}>
            {typeof entry.value === 'number' ? entry.value.toFixed(4) : entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}

import { fmt } from '../utils'
import styles from './StatBadge.module.css'
import clsx from 'clsx'

export default function StatBadge({ label, value, unit, baseline, decimals = 2, accent = 'cyan' }) {
  const improvement = baseline != null ? fmt.pct(baseline, value) : null

  return (
    <div className={styles.badge}>
      <span className={styles.label}>{label}</span>
      <div className={styles.row}>
        <span className={clsx(styles.value, styles[accent])}>
          {fmt.num(value, decimals)}
          <span className={styles.unit}> {unit}</span>
        </span>
        {improvement != null && (
          <span className={clsx(styles.delta, improvement > 0 ? styles.good : styles.bad)}>
            {fmt.sign(improvement)}
          </span>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../components/Card'
import styles from './ChartPage.module.css'
import tStyles from './SummaryPage.module.css'

export default function HistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getHistory()
      .then(setHistory)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Run History</h1>
          <p className={styles.sub}>{history.length} past optimization runs stored</p>
        </div>
      </header>

      <Card>
        {loading ? (
          <div className={styles.empty}>Loading history...</div>
        ) : history.length === 0 ? (
          <div className={styles.empty}>No runs stored yet — run an optimization first</div>
        ) : (
          <div className={tStyles.tableWrap}>
            <table className={tStyles.table}>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Pareto Solutions</th>
                  <th>Hypervolume</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {history.map((run, i) => (
                  <tr key={i}>
                    <td><code className={tStyles.mono} style={{ fontSize: 10 }}>{run.run_id?.slice(0, 16)}...</code></td>
                    <td className={tStyles.mono}>{run.pareto_front_size}</td>
                    <td className={tStyles.mono}>{run.hypervolume?.toFixed(4)}</td>
                    <td className={tStyles.mono}>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

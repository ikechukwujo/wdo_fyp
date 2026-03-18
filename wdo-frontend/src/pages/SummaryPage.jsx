import { useStore } from '../store/useStore'
import Card from '../components/Card'
import styles from './ChartPage.module.css'
import tStyles from './SummaryPage.module.css'

export default function SummaryPage() {
  const results = useStore(s => s.results)
  const summary = results?.summary_table

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Results Summary</h1>
          <p className={styles.sub}>Full performance metrics — Chapter 5 evaluation table</p>
        </div>
      </header>

      <Card>
        {summary?.metrics ? (
          <div className={tStyles.tableWrap}>
            <table className={tStyles.table}>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Unit</th>
                  <th>Baseline</th>
                  <th>GA-Optimized</th>
                  <th>Improvement</th>
                </tr>
              </thead>
              <tbody>
                {summary.metrics.map((row, i) => {
                  const imp = typeof row.improvement_pct === 'number'
                    ? row.improvement_pct : null
                  return (
                    <tr key={i}>
                      <td className={tStyles.metricName}>{row.metric}</td>
                      <td className={tStyles.mono}>{row.unit}</td>
                      <td className={`${tStyles.mono} ${tStyles.bad}`}>{row.baseline}</td>
                      <td className={`${tStyles.mono} ${tStyles.good}`}>{row.optimized}</td>
                      <td>
                        {imp != null ? (
                          <span className={`${tStyles.badge} ${imp > 0 ? tStyles.badgeGood : tStyles.badgeBad}`}>
                            {imp > 0 ? '▼' : '▲'} {Math.abs(imp).toFixed(1)}%
                          </span>
                        ) : (
                          <span className={tStyles.mono} style={{ color: 'var(--text-dim)' }}>N/A</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className={styles.empty}>Run optimization to generate the results table</div>
        )}
      </Card>

      {/* Knee solution raw pump/valve settings */}
      {results?.knee_solution && (
        <Card>
          <h3 className={styles.chartTitle}>Recommended Operating Schedule (Knee Point)</h3>
          <div className={tStyles.settingsGrid}>
            <div>
              <h4 className={tStyles.settingsLabel}>Pump Speed Settings</h4>
              {results.knee_solution.pump_settings?.map((v, i) => (
                <div key={i} className={tStyles.settingRow}>
                  <span className={tStyles.mono}>Pump {i + 1}</span>
                  <div className={tStyles.bar}>
                    <div className={tStyles.barFill} style={{ width: `${v * 100}%` }} />
                  </div>
                  <span className={tStyles.mono}>{(v * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
            <div>
              <h4 className={tStyles.settingsLabel}>Valve Settings</h4>
              {results.knee_solution.valve_settings?.length > 0
                ? results.knee_solution.valve_settings.map((v, i) => (
                    <div key={i} className={tStyles.settingRow}>
                      <span className={tStyles.mono}>Valve {i + 1}</span>
                      <div className={tStyles.bar}>
                        <div className={tStyles.barFill} style={{ width: `${v * 100}%`, background: 'var(--amber)' }} />
                      </div>
                      <span className={tStyles.mono}>{(v * 100).toFixed(1)}%</span>
                    </div>
                  ))
                : <p className={styles.empty} style={{ paddingTop: 0 }}>No valves in network</p>
              }
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

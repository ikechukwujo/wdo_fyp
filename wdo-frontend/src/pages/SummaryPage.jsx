import { useStore } from '../store/useStore'
import Card from '../components/Card'
import styles from './ChartPage.module.css'
import tStyles from './SummaryPage.module.css'

function buildScheduleFallback(knee) {
  const existing = knee?.operating_schedule?.hours
  if (existing?.length > 0) return existing

  const pumps = knee?.pump_settings ?? []
  const valves = knee?.valve_settings ?? []
  if (!pumps.length && !valves.length) return []

  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    label: `${String(hour).padStart(2, '0')}:00`,
    pumps: pumps.map((speed, i) => ({
      id: i + 1,
      name: `Pump ${i + 1}`,
      speed_percent: speed * 100,
    })),
    valves: valves.map((setting, i) => ({
      id: i + 1,
      name: `Valve ${i + 1}`,
      setting_percent: setting * 100,
    })),
  }))
}

const fmt = (value, decimals = 1) =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(decimals) : '-'

export default function SummaryPage() {
  const results = useStore(s => s.results)
  const summary = results?.summary_table
  const knee = results?.knee_solution
  const scheduleHours = buildScheduleFallback(results?.knee_solution)
  const zoneSummary = knee?.demand_zone_summary ?? []
  const routeRanking = knee?.route_ranking ?? []

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Results Summary</h1>
          <p className={styles.sub}>Full performance metrics - Chapter 5 evaluation table</p>
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
                            {imp === 0 ? '' : imp > 0 ? 'down ' : 'up '}
                            {Math.abs(imp).toFixed(1)}%
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
          <h3 className={styles.chartTitle}>Average Operating Settings (Knee Point)</h3>
          <div className={tStyles.settingsGrid}>
            <div>
              <h4 className={tStyles.settingsLabel}>Average Pump Speed Settings</h4>
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
              <h4 className={tStyles.settingsLabel}>Average Valve Settings</h4>
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

      {scheduleHours.length > 0 && (
        <Card>
          <h3 className={styles.chartTitle}>24-Hour Pump and Valve Schedule</h3>
          <div className={tStyles.tableWrap}>
            <table className={`${tStyles.table} ${tStyles.scheduleTable}`}>
              <thead>
                <tr>
                  <th>Hour</th>
                  {scheduleHours[0]?.pumps?.map(pump => (
                    <th key={`pump-${pump.id}`}>{pump.name} Speed</th>
                  ))}
                  {scheduleHours[0]?.valves?.map(valve => (
                    <th key={`valve-${valve.id}`}>{valve.name} Setting</th>
                  ))}
                  <th>Expected Avg P</th>
                  <th>Expected Min P</th>
                  <th>Expected Flow</th>
                  <th>Nodes Below Min</th>
                </tr>
              </thead>
              <tbody>
                {scheduleHours.map(hour => (
                  <tr key={hour.hour}>
                    <td className={tStyles.mono}>{hour.label}</td>
                    {hour.pumps.map(pump => (
                      <td key={`hour-${hour.hour}-pump-${pump.id}`} className={tStyles.good}>
                        {pump.speed_percent.toFixed(1)}%
                      </td>
                    ))}
                    {hour.valves.map(valve => (
                      <td key={`hour-${hour.hour}-valve-${valve.id}`} className={tStyles.mono}>
                        {valve.setting_percent.toFixed(1)}%
                      </td>
                    ))}
                    <td className={tStyles.mono}>{fmt(hour.expected_avg_pressure)} m</td>
                    <td className={tStyles.mono}>{fmt(hour.expected_min_pressure)} m</td>
                    <td className={tStyles.mono}>{fmt(hour.expected_total_flow)} L/s</td>
                    <td className={tStyles.mono}>{hour.expected_nodes_below_min ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {zoneSummary.length > 0 && (
        <Card>
          <h3 className={styles.chartTitle}>Demand-Zone Allocation Summary</h3>
          <div className={tStyles.tableWrap}>
            <table className={tStyles.table}>
              <thead>
                <tr>
                  <th>Zone</th>
                  <th>Nodes</th>
                  <th>Total Demand</th>
                  <th>Estimated Inflow</th>
                  <th>Avg Pressure</th>
                  <th>Min Pressure</th>
                  <th>Below Min</th>
                </tr>
              </thead>
              <tbody>
                {zoneSummary.map(zone => (
                  <tr key={zone.zone}>
                    <td className={tStyles.metricName}>{zone.zone}</td>
                    <td className={tStyles.mono}>{zone.node_count}</td>
                    <td className={tStyles.mono}>{fmt(zone.total_demand)} L/s</td>
                    <td className={tStyles.mono}>{fmt(zone.estimated_inflow)} L/s</td>
                    <td className={tStyles.good}>{fmt(zone.avg_pressure)} m</td>
                    <td className={tStyles.mono}>{fmt(zone.min_pressure)} m</td>
                    <td className={zone.nodes_below_min > 0 ? tStyles.bad : tStyles.good}>
                      {zone.nodes_below_min}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {routeRanking.length > 0 && (
        <Card>
          <h3 className={styles.chartTitle}>Route Ranking by Carried Flow</h3>
          <div className={tStyles.tableWrap}>
            <table className={tStyles.table}>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Link</th>
                  <th>Type</th>
                  <th>Route</th>
                  <th>Supplies Zone</th>
                  <th>Flow</th>
                  <th>Velocity</th>
                  <th>Diameter</th>
                  <th>Importance</th>
                </tr>
              </thead>
              <tbody>
                {routeRanking.slice(0, 12).map(route => (
                  <tr key={route.link_id}>
                    <td className={tStyles.mono}>{route.rank}</td>
                    <td className={tStyles.metricName}>{route.name}</td>
                    <td className={tStyles.mono}>{route.type}</td>
                    <td className={tStyles.mono}>{`${route.source} -> ${route.target}`}</td>
                    <td className={tStyles.mono}>{route.supplies_zone}</td>
                    <td className={tStyles.good}>{fmt(route.flow)} L/s</td>
                    <td className={tStyles.mono}>{fmt(route.velocity, 2)} m/s</td>
                    <td className={tStyles.mono}>{fmt(route.diameter, 0)}</td>
                    <td>
                      <span className={`${tStyles.badge} ${route.importance === 'Critical' || route.importance === 'High' ? tStyles.badgeGood : tStyles.badgeBad}`}>
                        {route.importance}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

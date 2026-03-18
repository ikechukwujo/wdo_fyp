import { useStore } from '../store/useStore'
import Card from '../components/Card'
import ChartTooltip from '../components/ChartTooltip'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts'
import styles from './ChartPage.module.css'

export default function ParetoPage() {
  const results = useStore(s => s.results)
  const pareto = results?.pareto_front ?? []
  const knee = results?.knee_solution

  const data = pareto.map((s, i) => ({
    name: `Solution ${i + 1}`,
    energy: parseFloat(s.f1_energy_cost?.toFixed(2) ?? 0),
    variance: parseFloat(s.f2_pressure_variance?.toFixed(4) ?? 0),
    deficit: parseFloat(s.f3_pressure_deficit?.toFixed(2) ?? 0),
  }))

  const kneePoint = knee ? {
    energy: parseFloat(knee.f1_energy_cost?.toFixed(2) ?? 0),
    variance: parseFloat(knee.f2_pressure_variance?.toFixed(4) ?? 0),
  } : null

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Pareto Front</h1>
          <p className={styles.sub}>
            Non-dominated solution set · {pareto.length} solutions ·
            Hypervolume: {results?.hypervolume?.toFixed(4) ?? '—'}
          </p>
        </div>
      </header>

      <Card>
        <p className={styles.explainer}>
          Each point is a Pareto-optimal solution — no point dominates another
          across all three objectives. The <span className={styles.hi}>◆ red diamond</span> is
          the recommended <strong>knee point</strong>: the best balanced trade-off
          between energy cost and pressure equity.
        </p>

        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height={440}>
            <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="energy"
                name="Energy Cost"
                label={{ value: 'f1 — Energy Cost (₦/day)', position: 'insideBottom', offset: -20, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}
              />
              <YAxis
                dataKey="variance"
                name="Pressure Variance"
                label={{ value: 'f2 — Pressure Variance (m²)', angle: -90, position: 'insideLeft', offset: 10, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '4 4', stroke: 'var(--border-hi)' }} />
              <Scatter data={data} fill="var(--cyan)" opacity={0.75} r={6} />
              {kneePoint && (
                <ReferenceDot
                  x={kneePoint.energy}
                  y={kneePoint.variance}
                  r={10}
                  fill="var(--red)"
                  stroke="var(--bg-card)"
                  strokeWidth={2}
                  label={{ value: 'Knee', position: 'top', fill: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 11 }}
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        ) : (
          <div className={styles.empty}>Run optimization to generate the Pareto front</div>
        )}
      </Card>

      {/* Pareto solutions table */}
      {data.length > 0 && (
        <Card>
          <h3 className={styles.tableTitle}>All Pareto-Optimal Solutions</h3>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>f1 Energy Cost (₦/day)</th>
                  <th>f2 Pressure Variance (m²)</th>
                  <th>f3 Pressure Deficit (m)</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {pareto.map((s, i) => {
                  const isKnee = knee &&
                    Math.abs(s.f1_energy_cost - knee.f1_energy_cost) < 0.01
                  return (
                    <tr key={i} className={isKnee ? styles.kneeRow : ''}>
                      <td className={styles.mono}>{i + 1}</td>
                      <td className={styles.mono}>{s.f1_energy_cost?.toFixed(2)}</td>
                      <td className={styles.mono}>{s.f2_pressure_variance?.toFixed(4)}</td>
                      <td className={styles.mono}>{s.f3_pressure_deficit?.toFixed(2)}</td>
                      <td>{isKnee ? <span className={styles.kneeBadge}>◆ Knee Point</span> : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

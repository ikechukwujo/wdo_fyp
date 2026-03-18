import { useStore } from '../store/useStore'
import Card from '../components/Card'
import ChartTooltip from '../components/ChartTooltip'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import { fmt } from '../utils'
import styles from './ChartPage.module.css'

export default function ComparisonPage() {
  const results = useStore(s => s.results)
  const baseline = useStore(s => s.baseline)
  const knee = results?.knee_solution

  const metrics = (baseline && knee) ? [
    {
      name: 'Energy Cost',
      unit: '₦/day',
      Baseline: parseFloat(baseline.energy_cost?.toFixed(2) ?? 0),
      Optimized: parseFloat(knee.f1_energy_cost?.toFixed(2) ?? 0),
    },
    {
      name: 'Pressure Variance',
      unit: 'm²',
      Baseline: parseFloat(baseline.pressure_variance?.toFixed(4) ?? 0),
      Optimized: parseFloat(knee.f2_pressure_variance?.toFixed(4) ?? 0),
    },
    {
      name: 'Pressure Deficit',
      unit: 'm',
      Baseline: parseFloat(baseline.pressure_deficit?.toFixed(2) ?? 0),
      Optimized: parseFloat(knee.f3_pressure_deficit?.toFixed(2) ?? 0),
    },
  ] : []

  const improvements = metrics.map(m => ({
    name: m.name,
    improvement: fmt.pct(m.Baseline, m.Optimized) ?? 0,
  }))

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Baseline vs GA-Optimized</h1>
          <p className={styles.sub}>Knee point solution vs unoptimized network</p>
        </div>
      </header>

      <div className={styles.twoCol}>
        <Card>
          <h3 className={styles.chartTitle}>Metric Comparison</h3>
          {metrics.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={metrics} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontFamily: 'var(--font-mono)', fontSize: 11 }} />
                <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 11 }} />
                <Tooltip content={<ChartTooltip />} />
                <Legend wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 11 }} />
                <Bar dataKey="Baseline"  fill="var(--red)"   opacity={0.85} radius={[4,4,0,0]} />
                <Bar dataKey="Optimized" fill="var(--green)"  opacity={0.85} radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className={styles.empty}>Run optimization to see comparison</div>
          )}
        </Card>

        <Card>
          <h3 className={styles.chartTitle}>Improvement (%)</h3>
          {improvements.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={improvements} margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontFamily: 'var(--font-mono)', fontSize: 11 }} />
                <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 11 }} unit="%" />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="improvement" radius={[4,4,0,0]}>
                  {improvements.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.improvement > 0 ? 'var(--green)' : 'var(--red)'}
                      opacity={0.85}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className={styles.empty}>No data yet</div>
          )}
        </Card>
      </div>
    </div>
  )
}

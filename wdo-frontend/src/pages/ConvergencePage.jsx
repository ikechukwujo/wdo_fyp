import { useStore } from '../store/useStore'
import Card from '../components/Card'
import ChartTooltip from '../components/ChartTooltip'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import styles from './ChartPage.module.css'

const OBJECTIVES = [
  { key: 'min_f1', label: 'f1 Energy Cost',       color: 'var(--red)' },
  { key: 'min_f2', label: 'f2 Pressure Variance',  color: 'var(--cyan)' },
  { key: 'min_f3', label: 'f3 Pressure Deficit',   color: 'var(--green)' },
]

export default function ConvergencePage() {
  const results = useStore(s => s.results)
  const log = results?.generation_log ?? []

  const data = log.map(g => ({
    generation: g.generation + 1,
    'f1 Energy Cost':      parseFloat(g.min_f1?.toFixed(3) ?? 0),
    'f2 Pressure Variance':parseFloat(g.min_f2?.toFixed(4) ?? 0),
    'f3 Pressure Deficit': parseFloat(g.min_f3?.toFixed(3) ?? 0),
    'Pareto Size':         g.pareto_front_size,
  }))

  const paretoData = log.map(g => ({
    generation: g.generation + 1,
    'Pareto Size': g.pareto_front_size,
  }))

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Convergence Analysis</h1>
          <p className={styles.sub}>
            {log.length} generations · Downward trend = GA is learning
          </p>
        </div>
      </header>

      <Card>
        <h3 className={styles.chartTitle}>Objective Minimization Over Generations</h3>
        <p className={styles.explainer}>
          Each line shows the best value found for that objective per generation.
          All three objectives should trend downward as NSGA-II evolves better solutions.
        </p>
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={data} margin={{ top: 10, right: 30, bottom: 40, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="generation"
                label={{ value: 'Generation', position: 'insideBottom', offset: -20, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}
              />
              <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 11 }} />
              <Tooltip content={<ChartTooltip labelPrefix="Gen " />} />
              <Legend wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 11, paddingTop: 16 }} />
              {OBJECTIVES.map(({ key, label, color }) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={label}
                  stroke={color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className={styles.empty}>Run optimization to see convergence curves</div>
        )}
      </Card>

      <Card>
        <h3 className={styles.chartTitle}>Pareto Front Growth</h3>
        <p className={styles.explainer}>
          As NSGA-II runs, it discovers more non-dominated solutions.
          A growing Pareto front indicates the algorithm is exploring the trade-off space effectively.
        </p>
        {paretoData.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={paretoData} margin={{ top: 10, right: 30, bottom: 40, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="generation"
                label={{ value: 'Generation', position: 'insideBottom', offset: -20, fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}
              />
              <YAxis label={{ value: 'Solutions', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }} />
              <Tooltip content={<ChartTooltip labelPrefix="Gen " />} />
              <Line type="monotone" dataKey="Pareto Size" stroke="var(--purple)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className={styles.empty}>No data yet</div>
        )}
      </Card>
    </div>
  )
}

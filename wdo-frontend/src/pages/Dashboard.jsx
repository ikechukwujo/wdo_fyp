import { useStore } from '../store/useStore'
import { useBaseline } from '../hooks/useOptimization'
import ConfigPanel from '../components/ConfigPanel'
import StatBadge from '../components/StatBadge'
import Card from '../components/Card'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const baseline = useBaseline()
  const results = useStore(s => s.results)
  const knee = results?.knee_solution

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Water Distribution Optimizer</h1>
          <p className={styles.sub}>
            NSGA-II Multi-Objective · Net3 Benchmark · 3 Objectives
          </p>
        </div>
        <div className={styles.chips}>
          <span className={styles.chip}>f1 Energy Cost</span>
          <span className={styles.chip}>f2 Pressure Variance</span>
          <span className={styles.chip}>f3 Pressure Deficit</span>
        </div>
      </header>

      <div className={styles.grid}>
        {/* Left: Config */}
        <div className={styles.configCol}>
          <ConfigPanel />
        </div>

        {/* Right: Stats */}
        <div className={styles.statsCol}>
          {/* Baseline */}
          <Card>
            <h3 className={styles.cardTitle}>
              <span className={styles.dot} style={{ background: 'var(--red)' }} />
              Baseline — No Optimization
            </h3>
            {baseline ? (
              <div className={styles.statGrid}>
                <StatBadge label="Energy Cost"       value={baseline.energy_cost}         unit="₦/day" accent="red" />
                <StatBadge label="Avg Pressure"      value={baseline.avg_pressure}        unit="m"     accent="cyan" />
                <StatBadge label="Pressure Variance" value={baseline.pressure_variance}   unit="m²"    accent="amber" decimals={4} />
                <StatBadge label="Pressure Deficit"  value={baseline.pressure_deficit}    unit="m"     accent="red" />
                <StatBadge label="Nodes Below Min"   value={baseline.num_nodes_below_threshold} unit="nodes" accent="red" decimals={0} />
                <StatBadge label="Min Pressure"      value={baseline.min_pressure}        unit="m"     accent="amber" />
              </div>
            ) : (
              <p className={styles.loading}>Connecting to backend...</p>
            )}
          </Card>

          {/* Optimized */}
          <Card glow={!!knee}>
            <h3 className={styles.cardTitle}>
              <span className={styles.dot} style={{ background: 'var(--green)' }} />
              GA Optimized — Knee Point Solution
            </h3>
            {knee ? (
              <div className={styles.statGrid}>
                <StatBadge label="Energy Cost"       value={knee.f1_energy_cost}        unit="₦/day" baseline={baseline?.energy_cost}       accent="green" />
                <StatBadge label="Pressure Variance" value={knee.f2_pressure_variance}  unit="m²"    baseline={baseline?.pressure_variance}   accent="green" decimals={4} />
                <StatBadge label="Pressure Deficit"  value={knee.f3_pressure_deficit}   unit="m"     baseline={baseline?.pressure_deficit}    accent="green" />
                <StatBadge label="Pareto Front Size" value={results.pareto_front_size}  unit="solutions" accent="cyan" decimals={0} />
                <StatBadge label="Hypervolume"       value={results.hypervolume}         unit=""      accent="purple" decimals={4} />
              </div>
            ) : (
              <p className={styles.loading}>
                {results === null ? 'Run optimization to see results' : 'Computing...'}
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}

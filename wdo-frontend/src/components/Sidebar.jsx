import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, GitBranch, TrendingUp,
  BarChart3, ClipboardList, History, Network
} from 'lucide-react'
import { useStore } from '../store/useStore'
import styles from './Sidebar.module.css'

const NAV = [
  { to: '/',            icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/network',     icon: Network,         label: 'Network View' },
  { to: '/pareto',      icon: GitBranch,       label: 'Pareto Front' },
  { to: '/convergence', icon: TrendingUp,      label: 'Convergence' },
  { to: '/comparison',  icon: BarChart3,       label: 'Comparison' },
  { to: '/summary',     icon: ClipboardList,   label: 'Results' },
  { to: '/history',     icon: History,         label: 'History' },
]

export default function Sidebar() {
  const { jobStatus, uploadedName, networkFile } = useStore()

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>💧</div>
        <div>
          <div className={styles.logoTitle}>WDO</div>
          <div className={styles.logoSub}>Optimizer v1.0</div>
        </div>
      </div>

      {/* Status */}
      <div className={styles.statusWrap}>
        <span className={`${styles.statusDot} ${styles[jobStatus || 'idle']}`} />
        <span className={styles.statusText}>
          {jobStatus === 'running'  ? 'NSGA-II Running...'
           : jobStatus === 'complete' ? 'Optimization Complete'
           : jobStatus === 'failed'   ? 'Failed'
           : 'Idle'}
        </span>
      </div>

      {/* Active network */}
      <div className={styles.networkBadge}>
        <span className={styles.networkBadgeLabel}>Active Network</span>
        <span className={styles.networkBadgeName}>
          {uploadedName || 'nigeria_demo.inp'}
        </span>
      </div>

      <nav className={styles.nav}>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.active : ''}`
            }
          >
            <Icon size={15} strokeWidth={1.75} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className={styles.footer}>
        <div className={styles.footerText}>Covenant University · CSC FYP</div>
        <div className={styles.footerText}>22CG031893</div>
      </div>
    </aside>
  )
}

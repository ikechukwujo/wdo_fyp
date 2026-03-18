import { Routes, Route } from 'react-router-dom'
import Layout from './pages/Layout'
import Dashboard      from './pages/Dashboard'
import NetworkPage    from './pages/NetworkPage'
import ParetoPage     from './pages/ParetoPage'
import ConvergencePage from './pages/ConvergencePage'
import ComparisonPage  from './pages/ComparisonPage'
import SummaryPage     from './pages/SummaryPage'
import HistoryPage     from './pages/HistoryPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index              element={<Dashboard />} />
        <Route path="network"     element={<NetworkPage />} />
        <Route path="pareto"      element={<ParetoPage />} />
        <Route path="convergence" element={<ConvergencePage />} />
        <Route path="comparison"  element={<ComparisonPage />} />
        <Route path="summary"     element={<SummaryPage />} />
        <Route path="history"     element={<HistoryPage />} />
      </Route>
    </Routes>
  )
}

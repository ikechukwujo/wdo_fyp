import { useEffect, useRef } from 'react'
import { useStore } from '../store/useStore'
import { api } from '../api'

export function useOptimization() {
  const {
    jobId, jobStatus, progress, params,
    setJobId, setJobStatus, setProgress, setResults, setError, reset,
  } = useStore()

  const pollRef = useRef(null)

  // ── Poll for results while job is running ─────────────────────────────────
  useEffect(() => {
    if (!jobId || jobStatus === 'complete' || jobStatus === 'failed') return

    pollRef.current = setInterval(async () => {
      try {
        const data = await api.getResults(jobId)
        setJobStatus(data.status)
        if (data.progress !== undefined) {
          setProgress(data.progress)
        }

        if (data.status === 'complete') {
          setResults(data.result)
          clearInterval(pollRef.current)
        }
        if (data.status === 'failed') {
          setError(data.error || 'Optimization failed')
          clearInterval(pollRef.current)
        }
      } catch (err) {
        console.error('Polling error:', err)
        if (err.response?.status === 404) {
          setJobStatus('failed')
          setError('Job not found (backend may have restarted)')
          clearInterval(pollRef.current)
        }
      }
    }, 3000)

    return () => clearInterval(pollRef.current)
  }, [jobId, jobStatus])

  // ── Start a new optimization run ──────────────────────────────────────────
  const startOptimization = async () => {
    reset()
    setJobStatus('running')
    try {
      const data = await api.startOptimization(params)
      setJobId(data.job_id)
    } catch (err) {
      setJobStatus('failed')
      setError(err.message)
    }
  }

  return { startOptimization, isRunning: jobStatus === 'running', progress }
}

// ── Fetch baseline once on mount ──────────────────────────────────────────────
export function useBaseline() {
  const { baseline, setBaseline } = useStore()

  useEffect(() => {
    if (baseline) return
    api.getBaseline()
      .then(setBaseline)
      .catch(err => console.error('Baseline error:', err))
  }, [])

  return baseline
}

import { useRef, useState } from 'react'
import { useStore } from '../store/useStore'
import { useOptimization } from '../hooks/useOptimization'
import { Play, Loader, Upload, CheckCircle, Network } from 'lucide-react'
import { api } from '../api'
import Card from './Card'
import styles from './ConfigPanel.module.css'

const SLIDERS = [
  { key: 'population_size',        label: 'Population Size',         min: 10,  max: 200, step: 10,   unit: '' },
  { key: 'num_generations',        label: 'Generations',             min: 10,  max: 500, step: 10,   unit: '' },
  { key: 'crossover_rate',         label: 'Crossover Rate',          min: 0.1, max: 1.0, step: 0.05, unit: '' },
  { key: 'mutation_rate',          label: 'Mutation Rate',           min: 0.01,max: 0.5, step: 0.01, unit: '' },
  { key: 'min_pressure_threshold', label: 'Min Pressure (m)',        min: 5,   max: 30,  step: 1,    unit: 'm' },
]

export default function ConfigPanel() {
  const { params, setParam, networkFile, networkStats,
          uploadedName, setNetworkFile, setNetworkStats,
          setUploadedName, setBaseline } = useStore()
  const { startOptimization, isRunning } = useOptimization()
  const fileRef   = useRef()
  const [uploading, setUploading] = useState(false)
  const [uploadErr, setUploadErr] = useState(null)

  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setUploadErr(null)
    try {
      const res = await api.uploadNetwork(file)
      setNetworkFile(res.network_file)
      setNetworkStats(res.stats)
      setUploadedName(res.filename)
      // Reload baseline for new network
      const bl = await api.getBaseline(res.network_file)
      setBaseline(bl)
    } catch (err) {
      setUploadErr(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Card>
      <h2 className={styles.title}>Configuration</h2>
      <p className={styles.subtitle}>NSGA-II · 3 Objectives</p>

      {/* ── Network File ── */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>
          <Network size={12} />
          Network File
        </div>

        <div
          className={`${styles.dropZone} ${uploading ? styles.uploading : ''}`}
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".inp"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          {uploading ? (
            <><Loader size={14} className={styles.spin} /> Validating network...</>
          ) : uploadedName ? (
            <><CheckCircle size={14} color="var(--green)" /> {uploadedName}</>
          ) : (
            <><Upload size={14} /> Drop .inp file or click to upload</>
          )}
        </div>

        {uploadErr && <p className={styles.err}>{uploadErr}</p>}

        {networkStats && (
          <div className={styles.networkPills}>
            <span className={styles.pill}>{networkStats.num_nodes} nodes</span>
            <span className={styles.pill}>{networkStats.num_links} links</span>
            <span className={styles.pill}>{networkStats.num_pumps} pumps</span>
            <span className={styles.pill}>{networkStats.num_valves} valves</span>
          </div>
        )}

        {!uploadedName && (
          <p className={styles.defaultNote}>
            Using default: <code>nigeria_demo.inp</code>
          </p>
        )}
      </div>

      {/* ── GA Sliders ── */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>
          <span>⚙</span> GA Parameters
        </div>
        <div className={styles.sliders}>
          {SLIDERS.map(({ key, label, min, max, step, unit }) => (
            <div key={key} className={styles.sliderRow}>
              <div className={styles.sliderLabel}>
                <span>{label}</span>
                <code className={styles.sliderValue}>{params[key]}{unit}</code>
              </div>
              <input
                type="range" min={min} max={max} step={step}
                value={params[key]}
                disabled={isRunning}
                onChange={e => setParam(key, parseFloat(e.target.value))}
                className={styles.range}
              />
              <div className={styles.rangeLabels}>
                <span>{min}</span><span>{max}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={startOptimization}
        disabled={isRunning || uploading}
        className={styles.runBtn}
      >
        {isRunning
          ? <><Loader size={15} className={styles.spin} /> Running NSGA-II...</>
          : <><Play size={15} /> Run Optimization</>}
      </button>
    </Card>
  )
}

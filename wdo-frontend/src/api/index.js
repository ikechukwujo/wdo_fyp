import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''
const http = axios.create({ baseURL: `${API_URL}/api` })

export const api = {
  // ── Network ──────────────────────────────────────────────────────────────
  uploadNetwork: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/network/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data)
  },

  getTopology: (networkFile) =>
    http.get('/network/topology', { params: { network_file: networkFile } })
      .then(r => r.data),

  getSimulatedTopology: (networkFile, mode = 'baseline') =>
    http.get('/network/topology/simulated', {
      params: { network_file: networkFile, mode }
    }).then(r => r.data),

  getChromosomeTopology: (networkFile, chromosome) =>
    http.post('/network/topology/chromosome', {
      network_file: networkFile,
      chromosome
    }).then(r => r.data),

  // ── Optimization ─────────────────────────────────────────────────────────
  startOptimization: (params) =>
    http.post('/optimize', params).then(r => r.data),

  getResults: (jobId) =>
    http.get(`/results/${jobId}`).then(r => r.data),

  getBaseline: (networkFile) =>
    http.get('/baseline', { params: { network_file: networkFile } })
      .then(r => r.data),

  getHistory: () =>
    http.get('/history').then(r => r.data),
}

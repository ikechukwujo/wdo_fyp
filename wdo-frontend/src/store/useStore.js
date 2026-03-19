import { create } from 'zustand'

export const useStore = create((set, get) => ({
  // ── Network state ─────────────────────────────────────────────────────────
  networkFile:   'networks/nigeria_demo.inp',
  networkStats:  null,   // { num_nodes, num_links, num_pumps, num_valves }
  uploadedName:  null,   // original filename shown in UI

  // ── Optimization state ────────────────────────────────────────────────────
  jobId:      null,
  jobStatus:  null,
  progress:   0,
  results:    null,
  baseline:   null,
  error:      null,

  // ── GA params ─────────────────────────────────────────────────────────────
  params: {
    population_size:         50,
    num_generations:         50,
    crossover_rate:          0.9,
    mutation_rate:           0.1,
    min_pressure_threshold:  10.0,
    max_velocity:            3.0,
  },

  // ── Actions ───────────────────────────────────────────────────────────────
  setNetworkFile:  (f)  => set({ networkFile: f }),
  setNetworkStats: (s)  => set({ networkStats: s }),
  setUploadedName: (n)  => set({ uploadedName: n }),
  setParam:        (k, v) => set(s => ({ params: { ...s.params, [k]: v } })),
  setJobId:        (id) => set({ jobId: id }),
  setJobStatus:    (st) => set({ jobStatus: st }),
  setProgress:     (p)  => set({ progress: p }),
  setResults:      (r)  => set({ results: r }),
  setBaseline:     (b)  => set({ baseline: b }),
  setError:        (e)  => set({ error: e }),

  reset: () => set({ jobId: null, jobStatus: 'idle', progress: 0, results: null, error: null }),
}))

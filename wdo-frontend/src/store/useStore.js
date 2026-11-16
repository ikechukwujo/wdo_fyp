import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

const DEFAULT_NETWORK_FILE = 'networks/nigeria_demo.inp'

const DEFAULT_PARAMS = {
  population_size:         20,
  num_generations:         20,
  crossover_rate:          0.9,
  mutation_rate:           0.1,
  min_pressure_threshold:  10.0,
  max_velocity:            3.0,
}

const cleanRunState = {
  jobId:      null,
  jobStatus:  'idle',
  progress:   0,
  results:    null,
  baseline:   null,
  error:      null,
}

const demoState = {
  networkFile:   DEFAULT_NETWORK_FILE,
  networkStats:  null,
  uploadedName:  null,
  ...cleanRunState,
  params: DEFAULT_PARAMS,
}

export const useStore = create(persist((set, get) => ({
  // -- Network state ---------------------------------------------------------
  networkFile:   DEFAULT_NETWORK_FILE,
  networkStats:  null,   // { num_nodes, num_links, num_pumps, num_valves }
  uploadedName:  null,   // original filename shown in UI

  // -- Optimization state ----------------------------------------------------
  jobId:      null,
  jobStatus:  null,
  progress:   0,
  results:    null,
  baseline:   null,
  error:      null,

  // -- GA params -------------------------------------------------------------
  params: DEFAULT_PARAMS,

  // -- Actions ---------------------------------------------------------------
  setNetworkFile:  (f)  => set({ networkFile: f, ...cleanRunState }),
  setNetworkStats: (s)  => set({ networkStats: s }),
  setUploadedName: (n)  => set({ uploadedName: n }),
  setParam:        (k, v) => set(s => ({ params: { ...s.params, [k]: v } })),
  setJobId:        (id) => set({ jobId: id }),
  setJobStatus:    (st) => set({ jobStatus: st }),
  setProgress:     (p)  => set({ progress: p }),
  setResults:      (r)  => set({ results: r }),
  setBaseline:     (b)  => set({ baseline: b }),
  setError:        (e)  => set({ error: e }),

  clearResults: () => set({ jobId: null, jobStatus: 'idle', progress: 0, results: null, baseline: null, error: null }),
  reset: () => set({ jobId: null, jobStatus: 'idle', progress: 0, results: null, error: null }),
  resetToDemo: () => set(demoState),
}), {
  name: 'wdo-current-run',
  storage: createJSONStorage(() => sessionStorage),
  version: 3,
  migrate: () => demoState,
  partialize: (state) => ({
    networkFile: state.networkFile,
    networkStats: state.networkStats,
    uploadedName: state.uploadedName,
    jobId: state.jobId,
    jobStatus: state.jobStatus === 'running' ? 'idle' : state.jobStatus,
    progress: state.jobStatus === 'complete' ? 100 : 0,
    results: state.results,
    baseline: state.baseline,
    params: { ...DEFAULT_PARAMS, ...state.params },
  }),
}))

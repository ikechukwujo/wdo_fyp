export const fmt = {
  num:  (v, d = 2) => (typeof v === 'number' ? v.toFixed(d) : '—'),
  pct:  (baseline, optimized) => {
    if (!baseline || baseline === 0) return null
    return ((baseline - optimized) / baseline * 100)
  },
  sign: (v) => v > 0 ? `▼ ${v.toFixed(1)}%` : v < 0 ? `▲ ${Math.abs(v).toFixed(1)}%` : '—',
}

export const clamp = (val, min, max) => Math.min(Math.max(val, min), max)

// Shared Recharts styling that follows the light and dark theme through CSS variables.
export const axisProps = {
  stroke: 'var(--chart-axis)',
  tick: { fill: 'var(--chart-axis)', fontSize: 12 },
  tickLine: false,
  axisLine: false,
} as const

export const gridProps = { stroke: 'var(--chart-grid)', strokeDasharray: '3 3', vertical: false } as const

// Series colours. ACCENT is lime on dark and olive on light, so lines and bars stay readable on both.
export const ACCENT = 'var(--accent)'
export const MUTED = 'var(--chart-axis)'
export const FAINT = 'var(--chart-grid)'
export const DANGER = 'var(--danger)'
export const SKY = '#5ab8f5'
export const CORAL = '#ff7a45'

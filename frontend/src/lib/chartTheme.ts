// Shared Recharts styling that follows the light and dark theme through CSS variables.
export const axisProps = {
  stroke: 'var(--chart-axis)',
  tick: { fill: 'var(--chart-axis)', fontSize: 12 },
  tickLine: false,
  axisLine: false,
} as const

export const gridProps = { stroke: 'var(--chart-grid)', strokeDasharray: '3 3', vertical: false } as const

export const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`
export const times = (v: number, digits = 2) => `${v.toFixed(digits)}x`
export const int = (v: number) => Math.round(v).toLocaleString('en-US')
export const money = (v: number) => `${v < 0 ? '-' : ''}$${Math.abs(Math.round(v)).toLocaleString('en-US')}`
export const num = (v: number, digits = 1) => v.toLocaleString('en-US', { maximumFractionDigits: digits })

// Segment colours: distinct hues that hold up on light and dark backgrounds.
export const SEGMENT_COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ec4899', '#0ea5e9', '#8b5cf6', '#84cc16', '#f97316']
export const segmentColor = (id: number) => SEGMENT_COLORS[id % SEGMENT_COLORS.length]

export const SPEND_LABELS: Record<string, string> = {
  wine: 'Wine',
  fruit: 'Fruit',
  meat: 'Meat',
  fish: 'Fish',
  sweet: 'Sweets',
  gold: 'Gold',
}
export const SPEND_COLORS: Record<string, string> = {
  wine: '#9f1239',
  meat: '#ea580c',
  gold: '#ca8a04',
  fish: '#0284c7',
  fruit: '#16a34a',
  sweet: '#db2777',
}
export const CHANNEL_LABELS: Record<string, string> = { web: 'Web', catalog: 'Catalog', store: 'Store' }

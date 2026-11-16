export const pct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`
export const times = (v: number, digits = 2) => `${v.toFixed(digits)}x`
export const int = (v: number) => Math.round(v).toLocaleString('en-US')
export const money = (v: number) => `${v < 0 ? '-' : ''}$${Math.abs(Math.round(v)).toLocaleString('en-US')}`
export const num = (v: number, digits = 1) => v.toLocaleString('en-US', { maximumFractionDigits: digits })

const NUMBER_WORDS = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten']
export const numberWord = (n: number) => NUMBER_WORDS[n] ?? String(n)

// Segment colours: lime first to match the accent, then hues that hold up on the dark canvas and on paper.
export const SEGMENT_COLORS = ['#b8e62e', '#5ab8f5', '#ff7a45', '#a78bfa', '#f472b6', '#2dd4bf', '#facc15', '#94a3b8']
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
  wine: '#e0457b',
  meat: '#ff7a45',
  gold: '#facc15',
  fish: '#5ab8f5',
  fruit: '#b8e62e',
  sweet: '#a78bfa',
}
export const CHANNEL_LABELS: Record<string, string> = { web: 'Web', catalog: 'Catalog', store: 'Store' }
export const CHANNEL_COLORS: Record<string, string> = { web: '#5ab8f5', catalog: '#a78bfa', store: '#b8e62e' }

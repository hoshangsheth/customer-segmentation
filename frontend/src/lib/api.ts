import type {
  CustomerIn,
  Explanation,
  Health,
  Lift,
  ModelMetrics,
  Overview,
  Persona,
  Projection,
  ScoreOut,
  SegmentsOverview,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the API. Is the backend running on port 8000?')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${res.status})`
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })

export const api = {
  health: () => request<Health>('/api/health'),
  overview: () => request<Overview>('/api/overview'),
  segments: () => request<SegmentsOverview>('/api/segments'),
  projection: () => request<Projection>('/api/projection'),
  metrics: () => request<ModelMetrics>('/api/metrics'),
  lift: () => request<Lift>('/api/lift'),
  scoreDefaults: () => request<CustomerIn>('/api/score/defaults'),
  score: (c: CustomerIn) => post<ScoreOut>('/api/score', c),
  persona: (id: number) => request<Persona>(`/api/insights/segments/${id}`),
  explain: (c: CustomerIn) => post<Explanation>('/api/insights/explain', c),
}

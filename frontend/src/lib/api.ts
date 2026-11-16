import type {
  AnalyzeIn,
  Brief,
  BriefIn,
  CustomerDetail,
  CustomerPage,
  CustomerQuery,
  FieldsOut,
  Summary,
  UploadOut,
} from './batchTypes'
import type { Health, Lift, ModelMetrics, Overview, Persona, Projection, SegmentsOverview } from './types'

const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number
  problems: string[]
  constructor(status: number, message: string, problems: string[] = []) {
    super(message)
    this.status = status
    this.problems = problems
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  const json = typeof init?.body === 'string'
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { ...(json ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'Cannot reach the API. Is the backend running on port 8000?')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = body.detail
    if (detail && Array.isArray(detail.problems)) {
      throw new ApiError(res.status, detail.problems.join(' '), detail.problems)
    }
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg).join('; ')
          : `Request failed (${res.status})`
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })

function query(params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') q.set(k, String(v))
  return q.toString()
}

export const api = {
  health: () => request<Health>('/api/health'),
  overview: () => request<Overview>('/api/overview'),
  segments: () => request<SegmentsOverview>('/api/segments'),
  projection: () => request<Projection>('/api/projection'),
  metrics: () => request<ModelMetrics>('/api/metrics'),
  lift: () => request<Lift>('/api/lift'),
  persona: (id: number) => request<Persona>(`/api/insights/segments/${id}`),

  batch: {
    fields: () => request<FieldsOut>('/api/batch/fields'),
    sample: () => request<UploadOut>('/api/batch/sample', { method: 'POST' }),
    upload: (customers: File, history?: File) => {
      const form = new FormData()
      form.append('customers', customers)
      if (history) form.append('history', history)
      return request<UploadOut>('/api/batch/upload', { method: 'POST', body: form })
    },
    analyze: (jobId: string, body: AnalyzeIn) => post<Summary>(`/api/batch/${jobId}/analyze`, body),
    summary: (jobId: string) => request<Summary>(`/api/batch/${jobId}/summary`),
    customers: (jobId: string, q: CustomerQuery) =>
      request<CustomerPage>(`/api/batch/${jobId}/customers?${query({ ...q })}`),
    customer: (jobId: string, id: string) =>
      request<CustomerDetail>(`/api/batch/${jobId}/customers/${encodeURIComponent(id)}`),
    brief: (jobId: string, body: BriefIn) => post<Brief>(`/api/batch/${jobId}/brief`, body),
    exportUrl: (jobId: string, topShare: number) => `${BASE}/api/batch/${jobId}/export?${query({ top_share: topShare })}`,
    templateUrl: () => `${BASE}/api/batch/template`,
  },
}

// Mirrors customer_segmentation/api/batch_schemas.py

export type FileRole = 'customers' | 'history'

export interface FieldSpec {
  key: string
  label: string
  group: string
  kind: 'id' | 'int' | 'float' | 'date' | 'category' | 'flag'
  description: string
  aliases: string[]
  required: boolean
  default: number | string | null
  file: FileRole
  history: boolean
}

export interface FieldsOut {
  fields: FieldSpec[]
  required_groups: { keys: string[]; message: string }[]
  max_mb: number
  max_rows: number
}

export interface ColumnRef {
  file: FileRole
  column: string
}

export interface FileInfo {
  role: FileRole
  filename: string
  rows: number
  columns: string[]
  preview: Record<string, string>[]
}

export interface UploadOut {
  job_id: string
  sample: boolean
  files: FileInfo[]
  suggestion: { mapping: Record<string, ColumnRef>; history_id_column: string | null }
}

export type DateOrder = 'auto' | 'dmy' | 'mdy' | 'ymd'

export interface AnalyzeIn {
  mapping: Record<string, ColumnRef>
  history_id_column: string | null
  date_order: DateOrder
}

export interface SegmentSummary {
  segment_id: number
  name: string
  tagline: string
  customers: number
  share: number
  mean_probability: number
  expected_responders: number
  reference_response_rate: number
  avg_spend: number
  avg_income: number
  observed_response_rate: number | null
}

export interface Preparation {
  rows_in: number
  rows_ready: number
  rejected: Record<string, number>
  rejected_examples: { row: number; customer_id: string; reason: string }[]
  duplicate_ids: number
  defaults_used: Record<string, number>
  history_rows_matched: number | null
  history_rows_unmatched: number | null
  income_above_training_range: number
  date_order: string
  as_of: string
  uses_history: boolean
  has_outcome: boolean
}

export interface Evaluation {
  available: boolean
  known: number
  reason?: string | null
  responders?: number | null
  response_rate?: number | null
  roc_auc?: number | null
  pr_auc?: number | null
  top10_lift?: number | null
  mean_predicted?: number | null
  deciles: { decile: number; customers: number; response_rate: number; lift: number }[]
}

export interface Summary {
  job_id: string
  sample: boolean
  filenames: Record<string, string>
  model: {
    kind: 'full' | 'behaviour'
    name: string
    reference_roc_auc: number
    reference_pr_auc: number
    reference_top_decile_lift: number
  }
  customers: number
  expected_responders: number
  mean_probability: number
  segments: SegmentSummary[]
  histogram: { from: number; to: number; customers: number }[]
  curve: { share: number; customers: number; expected_responders: number }[]
  drivers: { feature: string; label: string; mean_abs_shap: number }[]
  data_fit: {
    checked: boolean
    flagged: { feature: string; label: string; share_outside: number; training_range: number[] }[]
    threshold: number
  }
  evaluation: Evaluation | null
  preparation: Preparation
  defaults: { cost_per_contact: number; revenue_per_response: number }
}

export interface CustomerRow {
  customer_id: string
  segment_id: number
  segment_name: string
  probability: number
  rank: number
  top_percent: number
  income: number
  age: number
  recency: number
  frequency: number
  monetary: number
  prior_accepts: number
  reasons: { label: string; direction: 'up' | 'down' }[]
  outcome: number | null
}

export interface CustomerPage {
  total: number
  offset: number
  limit: number
  rows: CustomerRow[]
}

export interface CustomerDetail {
  customer_id: string
  segment_id: number
  segment_name: string
  probability: number
  rank: number
  top_percent: number
  reasons: { feature: string; label: string; value: number; shap: number }[]
  profile: Record<string, number>
  outcome: number | null
}

export interface BriefIn {
  top_share: number
  cost_per_contact: number
  revenue_per_response: number
}

export interface Brief {
  headline: string
  summary: string
  actions: { segment: string; audience: string; channel: string; message: string; why: string }[]
  budget_note: string
  watch_outs: string[]
  source: 'llm' | 'rule-based'
  model: string
}

export type SortKey = 'rank' | 'customer_id' | 'segment_name' | 'monetary' | 'recency' | 'income' | 'frequency'

export interface CustomerQuery {
  offset: number
  limit: number
  segment_id?: number
  q?: string
  sort: SortKey
  order: 'asc' | 'desc'
}

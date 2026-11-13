// Mirrors customer_segmentation/api/schemas.py

export interface Health {
  status: 'ok'
  model_version: string
  ai_available: boolean
  ai_provider: string | null
}

export interface SegmentCard {
  segment_id: number
  name: string
  tagline: string
  size: number
  share: number
  response_rate: number
  avg_spend: number
  avg_income: number
}

export interface Overview {
  model_version: string
  trained_at: string
  customers: number
  response_rate: number
  n_segments: number
  roc_auc: number
  pr_auc: number
  top_decile_lift: number
  top_segment_lift: number
  top_segment_name: string
  best_profit_share: number
  best_profit: number
  segments: SegmentCard[]
}

export type Means = Record<
  | 'income'
  | 'age'
  | 'children'
  | 'tenure_days'
  | 'recency'
  | 'frequency'
  | 'monetary'
  | 'avg_order_value'
  | 'deal_share'
  | 'web_visits',
  number
>

export interface SegmentProfile {
  segment_id: number
  name: string
  tagline: string
  size: number
  share: number
  response_rate: number
  prior_accept_rate: number
  means: Means
  spend_mix: Record<string, number>
  channel_mix: Record<string, number>
  traits: string[]
}

export interface KScore {
  k: number
  inertia: number
  silhouette: number
  davies_bouldin: number
}

export interface SegmentsOverview {
  segments: SegmentProfile[]
  population: Means & { response_rate: number }
  k_selection: { scores: KScore[]; chosen_k: number; elbow_k: number; rule: string }
}

export interface Projection {
  explained_variance: number[]
  points: { id: number; x: number; y: number; segment: number }[]
}

export interface CurvePoint {
  share_targeted: number
  customers: number
  responders: number
  response_rate: number
  lift: number
  capture: number
  profit: number
}

export interface DecileRow {
  decile: number
  customers: number
  responders: number
  response_rate: number
  lift: number
  cumulative_capture: number
}

export interface SegmentTargetingRow {
  segments: number[]
  names: string[]
  customers: number
  share_targeted: number
  response_rate: number
  lift: number
  capture: number
}

export interface Lift {
  method: string
  base_rate: number
  cost_per_contact: number
  revenue_per_response: number
  deciles: DecileRow[]
  curve: CurvePoint[]
  best_profit_point: CurvePoint
  segment_targeting: { method: string; test_base_rate: number; rows: SegmentTargetingRow[] }
}

export interface CVScores {
  folds: number
  roc_auc_mean: number
  roc_auc_std: number
  pr_auc_mean: number
  pr_auc_std: number
}

export interface ModelMetrics {
  train_size: number
  test_size: number
  cv_xgboost: CVScores
  cv_baseline: CVScores
  holdout: {
    n: number
    positives: number
    base_rate: number
    roc_auc: number
    pr_auc: number
    brier: number
    expected_calibration_error: number
    calibration: { mean_predicted: number; observed_rate: number; count: number }[]
  }
  baseline_holdout_roc_auc: number
  baseline_holdout_pr_auc: number
  global_importance: { feature: string; label: string; mean_abs_shap: number }[]
  cleaning: Record<string, number>
}

export type SpendKey = 'wine' | 'fruit' | 'meat' | 'fish' | 'sweet' | 'gold'
export type PurchaseKey = 'web' | 'catalog' | 'store' | 'deals'

export interface CustomerIn {
  year_birth: number
  education: 'Undergraduate' | 'Graduate' | 'Postgraduate'
  marital_status: 'Partnered' | 'Single'
  income: number
  kids: number
  teens: number
  customer_since: string
  recency: number
  spend: Record<SpendKey, number>
  purchases: Record<PurchaseKey, number>
  web_visits: number
  accepted_campaigns: number[]
  complain: boolean
}

export interface Reason {
  feature: string
  label: string
  value: number
  shap: number
}

export interface ScoreOut {
  segment_id: number
  segment_name: string
  probability: number
  base_rate: number
  lift_vs_average: number
  reasons: Reason[]
}

export interface Persona {
  segment_id: number
  segment_name: string
  persona: string
  motivations: string[]
  campaigns: { title: string; channel: string; offer: string; rationale: string }[]
  watch_outs: string[]
  source: 'llm' | 'rule-based'
  model: string
}

export interface Explanation {
  score: ScoreOut
  summary: string
  next_best_action: string
  source: 'llm' | 'rule-based'
  model: string
}

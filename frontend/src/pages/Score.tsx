import { Loader2, Sparkles } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { TooltipBox } from '../components/chart'
import { axisProps } from '../lib/chartTheme'
import { Badge, Card, ErrorBox, Loading, PageHeader, SegmentDot } from '../components/ui'
import { api } from '../lib/api'
import { num, pct, segmentColor, SPEND_LABELS, times } from '../lib/format'
import type { CustomerIn, Explanation, PurchaseKey, ScoreOut, SpendKey } from '../lib/types'
import { useApi } from '../lib/useApi'

const inputCls =
  'mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm tabular-nums shadow-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-950'

export default function Score() {
  const defaults = useApi('score-defaults', api.scoreDefaults)
  if (defaults.loading) return <Loading />
  if (defaults.error || !defaults.data) return <ErrorBox message={defaults.error ?? 'No data'} />
  return <ScoreForm defaults={defaults.data} />
}

function ScoreForm({ defaults }: { defaults: CustomerIn }) {
  const [form, setForm] = useState<CustomerIn>(defaults)
  const [result, setResult] = useState<ScoreOut>()
  const [explanation, setExplanation] = useState<Explanation>()
  const [busy, setBusy] = useState<'score' | 'explain'>()
  const [error, setError] = useState<string>()

  const set = <K extends keyof CustomerIn>(key: K, value: CustomerIn[K]) => {
    setForm({ ...form, [key]: value })
    setExplanation(undefined)
  }

  const run = async (kind: 'score' | 'explain') => {
    setBusy(kind)
    setError(undefined)
    try {
      if (kind === 'score') {
        setResult(await api.score(form))
        setExplanation(undefined)
      } else {
        const e = await api.explain(form)
        setResult(e.score)
        setExplanation(e)
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(undefined)
    }
  }

  return (
    <>
      <PageHeader
        title="Score a customer"
        subtitle="Enter a customer's profile and history. The form starts at the median customer. You get their segment, the chance they accept the next campaign, and the reasons behind it."
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            run('score')
          }}
          className="space-y-6"
        >
          <Card title="Household">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <NumField label="Birth year" value={form.year_birth} onChange={(v) => set('year_birth', v)} min={1920} max={2010} />
              <NumField label="Income ($)" value={form.income} onChange={(v) => set('income', v)} min={0} max={200000} />
              <Field label="Education">
                <select className={inputCls} value={form.education} onChange={(e) => set('education', e.target.value as CustomerIn['education'])}>
                  <option>Undergraduate</option>
                  <option>Graduate</option>
                  <option>Postgraduate</option>
                </select>
              </Field>
              <Field label="Living">
                <select
                  className={inputCls}
                  value={form.marital_status}
                  onChange={(e) => set('marital_status', e.target.value as CustomerIn['marital_status'])}
                >
                  <option value="Partnered">With a partner</option>
                  <option value="Single">Single</option>
                </select>
              </Field>
              <NumField label="Kids" value={form.kids} onChange={(v) => set('kids', v)} min={0} max={5} />
              <NumField label="Teens" value={form.teens} onChange={(v) => set('teens', v)} min={0} max={5} />
            </div>
          </Card>
          <Card title="Relationship">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Field label="Customer since">
                <input type="date" className={inputCls} value={form.customer_since} onChange={(e) => set('customer_since', e.target.value)} />
              </Field>
              <NumField label="Days since last buy" value={form.recency} onChange={(v) => set('recency', v)} min={0} max={365} />
              <NumField label="Web visits / month" value={form.web_visits} onChange={(v) => set('web_visits', v)} min={0} max={60} />
            </div>
            <div className="mt-4">
              <div className="text-xs font-medium text-slate-500 dark:text-slate-400">Accepted earlier campaigns</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {[1, 2, 3, 4, 5].map((n) => {
                  const on = form.accepted_campaigns.includes(n)
                  return (
                    <button
                      type="button"
                      key={n}
                      aria-pressed={on}
                      onClick={() =>
                        set('accepted_campaigns', on ? form.accepted_campaigns.filter((c) => c !== n) : [...form.accepted_campaigns, n].sort())
                      }
                      className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                        on
                          ? 'border-indigo-500 bg-indigo-600 text-white'
                          : 'border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600'
                      }`}
                    >
                      Campaign {n}
                    </button>
                  )
                })}
                <label className="ml-auto flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.complain} onChange={(e) => set('complain', e.target.checked)} className="accent-indigo-600" />
                  Complained recently
                </label>
              </div>
            </div>
          </Card>
          <Card title="Spend over two years ($)">
            <div className="grid grid-cols-3 gap-3">
              {(Object.keys(SPEND_LABELS) as SpendKey[]).map((k) => (
                <NumField key={k} label={SPEND_LABELS[k]} value={form.spend[k]} onChange={(v) => set('spend', { ...form.spend, [k]: v })} min={0} />
              ))}
            </div>
          </Card>
          <Card title="Purchases">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {(['web', 'catalog', 'store', 'deals'] as PurchaseKey[]).map((k) => (
                <NumField
                  key={k}
                  label={k === 'deals' ? 'On discount' : k[0].toUpperCase() + k.slice(1)}
                  value={form.purchases[k]}
                  onChange={(v) => set('purchases', { ...form.purchases, [k]: v })}
                  min={0}
                />
              ))}
            </div>
          </Card>
          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={!!busy}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-500 disabled:opacity-60"
            >
              {busy === 'score' && <Loader2 className="size-4 animate-spin" />} Score customer
            </button>
            <button
              type="button"
              onClick={() => setForm(defaults)}
              className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Reset to median
            </button>
          </div>
          {error && <ErrorBox message={error} />}
        </form>

        <div className="xl:sticky xl:top-10 xl:self-start">
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div key="result" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <ResultCard result={result} explanation={explanation} explaining={busy === 'explain'} onExplain={() => run('explain')} />
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <Card>
                  <p className="py-12 text-center text-sm text-slate-500 dark:text-slate-400">
                    Adjust the profile, then press <span className="font-medium">Score customer</span>.
                  </p>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-xs font-medium text-slate-500 dark:text-slate-400">
      {label}
      {children}
    </label>
  )
}

function NumField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
}) {
  return (
    <Field label={label}>
      <input
        type="number"
        className={inputCls}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(e.target.value === '' ? 0 : Number(e.target.value))}
      />
    </Field>
  )
}

function ResultCard({
  result,
  explanation,
  explaining,
  onExplain,
}: {
  result: ScoreOut
  explanation?: Explanation
  explaining: boolean
  onExplain: () => void
}) {
  const reasons = [...result.reasons].sort((a, b) => b.shap - a.shap)
  const above = result.probability >= result.base_rate
  const circumference = 2 * Math.PI * 52

  return (
    <Card>
      <div className="flex flex-col items-center gap-6 sm:flex-row">
        <div className="relative size-36 shrink-0">
          <svg viewBox="0 0 120 120" className="size-full -rotate-90">
            <circle cx="60" cy="60" r="52" fill="none" strokeWidth="10" className="stroke-slate-100 dark:stroke-slate-800" />
            <motion.circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              strokeWidth="10"
              strokeLinecap="round"
              stroke={above ? '#6366f1' : '#94a3b8'}
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference * (1 - result.probability) }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </svg>
          <div className="absolute inset-0 grid place-items-center text-center">
            <div>
              <div className="text-3xl font-semibold tabular-nums">{pct(result.probability, 0)}</div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400">chance to respond</div>
            </div>
          </div>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <SegmentDot color={segmentColor(result.segment_id)} />
            <span className="font-semibold">{result.segment_name}</span>
          </div>
          <div>
            <span className="font-semibold tabular-nums">{times(result.lift_vs_average, 1)}</span>{' '}
            <span className="text-slate-500 dark:text-slate-400">the average response rate of {pct(result.base_rate)}</span>
          </div>
          <Badge tone={above ? 'indigo' : 'slate'}>{above ? 'Worth contacting' : 'Below average'}</Badge>
        </div>
      </div>

      <h3 className="mt-6 text-sm font-semibold">Why: SHAP contributions</h3>
      <p className="text-xs text-slate-500 dark:text-slate-400">Bars to the right raise the chance, bars to the left lower it.</p>
      <div className="mt-2 h-60">
        <ResponsiveContainer>
          <BarChart data={reasons} layout="vertical" margin={{ left: 8, right: 16 }} barSize={16}>
            <XAxis type="number" {...axisProps} tickFormatter={(v) => v.toFixed(1)} />
            <YAxis type="category" dataKey="label" width={180} interval={0} {...axisProps} />
            <ReferenceLine x={0} stroke="var(--chart-axis)" />
            <Tooltip
              cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
              content={({ payload }) =>
                payload?.[0] ? (
                  <TooltipBox
                    title={payload[0].payload.label}
                    rows={[
                      { label: 'Value', value: num(payload[0].payload.value, 2) },
                      { label: 'Effect (log-odds)', value: Number(payload[0].payload.shap).toFixed(3) },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="shap" radius={4}>
              {reasons.map((r) => (
                <Cell key={r.feature} fill={r.shap >= 0 ? '#6366f1' : '#f43f5e'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 border-t border-slate-100 pt-4 dark:border-slate-800">
        {explanation ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-indigo-500" />
              <span className="font-semibold">In plain English</span>
              <Badge tone={explanation.source === 'llm' ? 'emerald' : 'slate'}>
                {explanation.source === 'llm' ? `AI: ${explanation.model}` : 'Rule-based'}
              </Badge>
            </div>
            <p>{explanation.summary}</p>
            <p className="font-medium">Next step: {explanation.next_best_action}</p>
          </motion.div>
        ) : (
          <button
            onClick={onExplain}
            disabled={explaining}
            className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-60 dark:border-indigo-500/40 dark:text-indigo-300 dark:hover:bg-indigo-500/10"
          >
            {explaining ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            Explain in plain English
          </button>
        )}
      </div>
    </Card>
  )
}

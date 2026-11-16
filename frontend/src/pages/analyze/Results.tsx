import { AlertTriangle, ChevronDown, Crosshair, Download, Gauge, RotateCcw, Users, Wallet } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TooltipBox } from '../../components/chart'
import { buttonOutline, buttonPrimary, Card, PageHeader, Reveal, SegmentDot, Stat } from '../../components/ui'
import { api } from '../../lib/api'
import type { Summary } from '../../lib/batchTypes'
import { ACCENT, CORAL, FAINT, MUTED, axisProps, gridProps } from '../../lib/chartTheme'
import { int, money, pct, segmentColor, times } from '../../lib/format'
import BriefCard from './BriefCard'
import CustomerTable from './CustomerTable'

export default function Results({ summary, onReset }: { summary: Summary; onReset: () => void }) {
  const [cost, setCost] = useState(summary.defaults.cost_per_contact)
  const [revenue, setRevenue] = useState(summary.defaults.revenue_per_response)
  const curve = useMemo(
    () =>
      summary.curve.map((c) => ({
        ...c,
        profit: c.expected_responders * revenue - c.customers * cost,
      })),
    [summary.curve, cost, revenue],
  )
  const bestIdx = curve.reduce((best, c, i) => (c.profit > curve[best].profit ? i : best), 0)
  const [idx, setIdx] = useState<number>(bestIdx)
  const point = curve[Math.min(idx, curve.length - 1)]
  const share = point.share

  const prep = summary.preparation
  const rejected = prep.rows_in - prep.rows_ready
  const top10 = summary.curve[9]
  const top10Lift = top10.expected_responders / top10.customers / summary.mean_probability
  const names = Object.values(summary.filenames).join(' + ')

  return (
    <>
      <PageHeader
        eyebrow="Results"
        title={`${int(summary.customers)} customers,`}
        accent="ranked and segmented."
        subtitle={`${names}. Data as of ${prep.as_of}.`}
      >
        <div className="flex flex-wrap gap-3">
          <a href={api.batch.exportUrl(summary.job_id, 1)} className={buttonOutline}>
            <Download className="size-4" /> All scores (CSV)
          </a>
          <button type="button" onClick={onReset} className={buttonOutline}>
            <RotateCcw className="size-4" /> New analysis
          </button>
        </div>
      </PageHeader>

      {summary.sample && (
        <div className="mb-5 rounded-3xl border border-accent/40 bg-lime/10 p-4 text-sm">
          This is synthetic sample data, including simulated campaign outcomes. Use it to explore the app; the numbers do not
          describe real customers.
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat icon={Users} label="Customers scored" value={int(summary.customers)} hint={rejected ? `${int(rejected)} rows skipped, see data quality` : 'no rows skipped'} />
        <Stat icon={Crosshair} label="Expected responders" value={int(summary.expected_responders)} hint={`${pct(summary.mean_probability)} average chance`} delay={0.05} />
        <Stat icon={Wallet} label="Top 10% expected lift" value={times(top10Lift, 1)} hint="vs contacting everyone" delay={0.1} />
        <Stat
          icon={Gauge}
          label={summary.model.kind === 'full' ? 'Full model' : 'Behaviour-only model'}
          value={summary.model.reference_roc_auc.toFixed(3)}
          hint="ROC AUC on held-out training data"
          delay={0.15}
        />
      </div>

      <DataQuality summary={summary} />

      <Reveal className="mt-5">
        <Card
          title="Campaign planner"
          subtitle="Expected results if you contact the customers the model ranks highest. Set your own economics."
          action={
            idx === bestIdx ? (
              <span className="rounded-full bg-lime px-3 py-1 text-[10px] font-bold tracking-wider text-on-lime uppercase">Best profit</span>
            ) : (
              <button
                type="button"
                onClick={() => setIdx(bestIdx)}
                className="rounded-full border border-accent/40 px-3 py-1 text-[10px] font-bold tracking-wider text-accent uppercase hover:bg-lime/10"
              >
                Jump to best
              </button>
            )
          }
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_2fr]">
            <MoneyInput label="Cost per contact" value={cost} onChange={setCost} />
            <MoneyInput label="Revenue per response" value={revenue} onChange={setRevenue} />
            <label className="block">
              <span className="flex items-end justify-between">
                <span className="text-[10px] tracking-widest text-mute uppercase">Contact the top</span>
                <span className="font-display text-3xl font-bold text-accent tabular-nums">{pct(share, 0)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={curve.length - 1}
                value={idx}
                onChange={(e) => setIdx(Number(e.target.value))}
                aria-label="Share of customers to contact"
                className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full [&::-moz-range-thumb]:size-5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-4 [&::-moz-range-thumb]:border-night [&::-moz-range-thumb]:bg-lime [&::-webkit-slider-thumb]:size-6 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-4 [&::-webkit-slider-thumb]:border-night [&::-webkit-slider-thumb]:bg-lime"
                style={{ background: `linear-gradient(to right, #d9ff3d ${(idx / (curve.length - 1)) * 100}%, var(--line) ${(idx / (curve.length - 1)) * 100}%)` }}
              />
            </label>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
            <Stat label="Contacts" value={int(point.customers)} />
            <Stat label="Expected responders" value={int(point.expected_responders)} hint={`${pct(point.expected_responders / summary.expected_responders, 0)} of all expected`} />
            <Stat label="Expected rate" value={pct(point.expected_responders / point.customers)} hint={`everyone: ${pct(summary.mean_probability)}`} />
            <Stat label="Cost" value={money(point.customers * cost)} hint={`revenue ${money(point.expected_responders * revenue)}`} />
            <Stat
              label="Expected profit"
              value={<span className={point.profit < 0 ? 'text-danger' : 'text-accent'}>{money(point.profit)}</span>}
              hint={`everyone: ${money(curve[curve.length - 1].profit)}`}
              className="col-span-2 md:col-span-1"
            />
          </div>
          <div className="mt-6 h-60">
            <ResponsiveContainer>
              <AreaChart data={curve} margin={{ left: 8, right: 16, top: 12 }}>
                <defs>
                  <linearGradient id="batchProfit" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#d9ff3d" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#d9ff3d" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="share" type="number" domain={[0.01, 1]} tickFormatter={(v) => pct(v, 0)} {...axisProps} />
                <YAxis tickFormatter={(v) => money(v)} {...axisProps} width={72} />
                <ReferenceLine y={0} stroke={MUTED} />
                <Tooltip
                  content={({ payload }) =>
                    payload?.[0] ? (
                      <TooltipBox
                        title={`Contact top ${pct(payload[0].payload.share, 0)}`}
                        rows={[
                          { label: 'Expected profit', value: money(payload[0].payload.profit) },
                          { label: 'Expected responders', value: int(payload[0].payload.expected_responders) },
                        ]}
                      />
                    ) : null
                  }
                />
                <Area type="monotone" dataKey="profit" stroke={ACCENT} strokeWidth={2.5} fill="url(#batchProfit)" />
                <ReferenceDot x={point.share} y={point.profit} r={7} fill="#d9ff3d" stroke="var(--night)" strokeWidth={3} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <a href={api.batch.exportUrl(summary.job_id, share)} className={buttonPrimary}>
              <Download className="size-4" /> Download target list (top {pct(share, 0)}, {int(point.customers)} customers)
            </a>
            <span className="text-xs text-mute">
              Expected numbers are model estimates. On held-out training data the model's scores ran slightly below the true response rate.
            </span>
          </div>
        </Card>
      </Reveal>

      <BriefCard jobId={summary.job_id} share={share} cost={cost} revenue={revenue} />

      <SegmentCards summary={summary} />

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Reveal className="h-full">
          <Card className="h-full" title="Score distribution" subtitle="How many customers fall in each chance-to-respond band">
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={summary.histogram.map((b) => ({ ...b, label: `${Math.round(b.from * 100)}-${Math.round(b.to * 100)}%` }))} margin={{ left: -8, right: 8, top: 8 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="label" {...axisProps} interval={0} angle={-30} textAnchor="end" height={48} tick={{ ...axisProps.tick, fontSize: 10 }} />
                  <YAxis {...axisProps} />
                  <Tooltip
                    cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
                    content={({ payload }) =>
                      payload?.[0] ? <TooltipBox title={`${payload[0].payload.label} chance`} rows={[{ label: 'Customers', value: int(payload[0].payload.customers) }]} /> : null
                    }
                  />
                  <Bar dataKey="customers" fill={ACCENT} radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Reveal>
        <Reveal className="h-full" delay={0.06}>
          <Card className="h-full" title="What drives scores in your file" subtitle="Mean absolute SHAP value across your customers">
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={summary.drivers} layout="vertical" margin={{ left: 8, right: 16 }} barSize={12}>
                  <XAxis type="number" {...axisProps} tickFormatter={(v) => v.toFixed(1)} />
                  <YAxis type="category" dataKey="label" width={170} interval={0} {...axisProps} tick={{ ...axisProps.tick, fontSize: 11 }} />
                  <Tooltip
                    cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
                    content={({ payload }) =>
                      payload?.[0] ? <TooltipBox title={payload[0].payload.label} rows={[{ label: 'Mean |SHAP|', value: Number(payload[0].value).toFixed(3) }]} /> : null
                    }
                  />
                  <Bar dataKey="mean_abs_shap" fill={ACCENT} radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Reveal>
      </div>

      {summary.evaluation && <EvaluationCard summary={summary} />}

      <CustomerTable summary={summary} topShare={share} />
    </>
  )
}

function MoneyInput({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block text-[10px] tracking-widest text-mute uppercase">
      {label}
      <input
        type="number"
        min={0}
        step="any"
        value={value}
        onChange={(e) => onChange(Math.max(0, Number(e.target.value) || 0))}
        className="mt-1.5 w-full rounded-2xl border border-line bg-night px-4 py-2.5 text-sm tracking-normal text-ink normal-case tabular-nums outline-none focus:border-accent"
      />
    </label>
  )
}

function DataQuality({ summary }: { summary: Summary }) {
  const prep = summary.preparation
  const [open, setOpen] = useState(false)
  const rejected = prep.rows_in - prep.rows_ready
  const warnings = Object.keys(prep.defaults_used).length + summary.data_fit.flagged.length + (prep.income_above_training_range ? 1 : 0)
  return (
    <section className="mt-5 rounded-3xl border border-line bg-surface">
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full items-center justify-between gap-4 p-6 text-left">
        <div className="flex items-center gap-3">
          {rejected || warnings ? <AlertTriangle className="size-5 text-accent" /> : <span className="size-2.5 rounded-full bg-lime" />}
          <div>
            <h2 className="font-display text-xl font-bold">Data quality</h2>
            <p className="text-sm text-mute">
              {int(prep.rows_ready)} of {int(prep.rows_in)} rows used
              {rejected ? `, ${int(rejected)} skipped` : ''}
              {warnings ? `, ${warnings} note${warnings > 1 ? 's' : ''}` : ''}. {summary.model.name}.
            </p>
          </div>
        </div>
        <ChevronDown className={`size-5 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="grid gap-6 border-t border-line p-6 text-sm md:grid-cols-2">
              <div>
                <h3 className="mb-2 text-[10px] tracking-widest text-mute uppercase">Skipped rows</h3>
                {rejected ? (
                  <>
                    <ul className="space-y-1">
                      {Object.entries(prep.rejected).map(([r, n]) => (
                        <li key={r} className="flex justify-between gap-4">
                          <span>{r}</span>
                          <span className="font-semibold tabular-nums">{int(n)}</span>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-3 text-xs text-mute">
                      Examples: {prep.rejected_examples.map((e) => `row ${e.row}${e.customer_id ? ` (${e.customer_id})` : ''}`).join(', ')}
                    </p>
                  </>
                ) : (
                  <p className="text-mute">None. Every row could be scored.</p>
                )}
              </div>
              <div>
                <h3 className="mb-2 text-[10px] tracking-widest text-mute uppercase">Filled in or adjusted</h3>
                <ul className="space-y-1">
                  {Object.entries(prep.defaults_used).map(([f, n]) => (
                    <li key={f} className="flex justify-between gap-4">
                      <span>{f}: default used</span>
                      <span className="font-semibold tabular-nums">{int(n)}</span>
                    </li>
                  ))}
                  {prep.history_rows_matched !== null && (
                    <li className="flex justify-between gap-4">
                      <span>Customers matched in the history file</span>
                      <span className="font-semibold tabular-nums">{int(prep.history_rows_matched)}</span>
                    </li>
                  )}
                  {prep.income_above_training_range > 0 && (
                    <li className="flex justify-between gap-4">
                      <span>Income above the training range (200,000)</span>
                      <span className="font-semibold tabular-nums">{int(prep.income_above_training_range)}</span>
                    </li>
                  )}
                  {Object.keys(prep.defaults_used).length === 0 && prep.history_rows_matched === null && !prep.income_above_training_range && (
                    <li className="text-mute">Nothing was filled in.</li>
                  )}
                </ul>
                <p className="mt-3 text-xs text-mute">
                  Dates read as {prep.date_order === 'dmy' ? 'day first' : prep.date_order === 'mdy' ? 'month first' : 'year first'}. Days as a customer are counted up to {prep.as_of}.
                </p>
              </div>
              {summary.data_fit.flagged.length > 0 && (
                <div className="md:col-span-2">
                  <h3 className="mb-2 text-[10px] tracking-widest text-mute uppercase">Unlike the training data</h3>
                  <p className="mb-2 text-mute">
                    For these measures, more than {pct(summary.data_fit.threshold, 0)} of your customers fall outside the range the model learned from, so
                    scores lean on extrapolation.
                  </p>
                  <ul className="space-y-1">
                    {summary.data_fit.flagged.map((f) => (
                      <li key={f.feature} className="flex justify-between gap-4">
                        <span>
                          {f.label} <span className="text-mute">(trained on {f.training_range.map((v) => Math.round(v * 100) / 100).join(' to ')})</span>
                        </span>
                        <span className="font-semibold tabular-nums">{pct(f.share_outside, 0)} outside</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}

function SegmentCards({ summary }: { summary: Summary }) {
  const segs = [...summary.segments].sort((a, b) => b.mean_probability - a.mean_probability)
  const max = Math.max(...segs.map((s) => s.mean_probability), 0.01)
  return (
    <section className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {segs.map((s, i) => (
        <Reveal key={s.segment_id} delay={i * 0.06} className="h-full">
          <div className="relative h-full overflow-hidden rounded-3xl border border-line bg-surface p-6">
            <div className="pointer-events-none absolute -top-20 -right-16 size-48 rounded-full opacity-60" style={{ background: `radial-gradient(circle, ${segmentColor(s.segment_id)}40, transparent 70%)` }} aria-hidden />
            <div className="relative">
              <div className="flex items-center gap-2">
                <SegmentDot color={segmentColor(s.segment_id)} />
                <h3 className="font-display text-xl font-bold">{s.name}</h3>
              </div>
              <p className="mt-1 text-sm text-mute">{s.tagline}</p>
              <dl className="mt-5 grid grid-cols-3 gap-2">
                <div>
                  <dt className="text-[10px] tracking-widest text-mute uppercase">Customers</dt>
                  <dd className="font-display text-lg font-bold tabular-nums">
                    {int(s.customers)} <span className="text-xs font-normal text-mute">{pct(s.share, 0)}</span>
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] tracking-widest text-mute uppercase">Avg spend</dt>
                  <dd className="font-display text-lg font-bold tabular-nums">{money(s.avg_spend)}</dd>
                </div>
                <div>
                  <dt className="text-[10px] tracking-widest text-mute uppercase">Expected</dt>
                  <dd className="font-display text-lg font-bold tabular-nums">{int(s.expected_responders)}</dd>
                </div>
              </dl>
              <div className="mt-5">
                <div className="mb-2 flex justify-between text-xs">
                  <span className="text-mute">Average chance to respond</span>
                  <span className="font-semibold tabular-nums">
                    {pct(s.mean_probability)}
                    {s.observed_response_rate !== null && s.observed_response_rate !== undefined && <span className="text-mute"> · actual {pct(s.observed_response_rate)}</span>}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-raised">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: segmentColor(s.segment_id) }}
                    initial={{ width: 0 }}
                    whileInView={{ width: `${(s.mean_probability / max) * 100}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                  />
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      ))}
    </section>
  )
}

function EvaluationCard({ summary }: { summary: Summary }) {
  const ev = summary.evaluation!
  return (
    <Reveal className="mt-5">
      <Card
        title="How the ranking performed on your customers"
        subtitle={
          ev.available
            ? `Measured against the campaign outcomes in your file (${int(ev.known)} customers with a known outcome).`
            : 'Campaign outcomes were mapped, but there are not enough to measure the ranking.'
        }
      >
        {ev.available ? (
          <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
            <div className="grid grid-cols-2 gap-3">
              <Stat label="ROC AUC" value={ev.roc_auc!.toFixed(3)} hint={`reference ${summary.model.reference_roc_auc.toFixed(3)}`} />
              <Stat label="Top 10% lift" value={times(ev.top10_lift!, 2)} hint="actual responders" />
              <Stat label="Actual rate" value={pct(ev.response_rate!)} hint={`${int(ev.responders!)} responders`} />
              <Stat label="Mean predicted" value={pct(ev.mean_predicted!)} hint={ev.mean_predicted! < ev.response_rate! ? 'model runs low here' : 'model runs high here'} />
            </div>
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={ev.deciles} margin={{ left: -8, right: 16, top: 8 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="decile" {...axisProps} />
                  <YAxis tickFormatter={(v) => pct(v, 0)} {...axisProps} />
                  <ReferenceLine y={ev.response_rate!} stroke={CORAL} strokeDasharray="4 4" label={{ value: 'average', fill: CORAL, fontSize: 11, position: 'insideTopRight' }} />
                  <Tooltip
                    cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
                    content={({ payload }) =>
                      payload?.[0] ? (
                        <TooltipBox
                          title={`Decile ${payload[0].payload.decile}`}
                          rows={[
                            { label: 'Actual response', value: pct(payload[0].payload.response_rate) },
                            { label: 'Lift', value: times(payload[0].payload.lift) },
                          ]}
                        />
                      ) : null
                    }
                  />
                  <Bar dataKey="response_rate" radius={[8, 8, 0, 0]}>
                    {ev.deciles.map((d) => (
                      <Cell key={d.decile} fill={d.lift >= 1 ? ACCENT : FAINT} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="text-center text-xs text-mute">Actual response rate by model decile (1 = highest scores)</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-mute">{ev.reason}</p>
        )}
      </Card>
    </Reveal>
  )
}

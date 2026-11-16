import { motion } from 'motion/react'
import { useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TooltipBox } from '../components/chart'
import { Page } from '../components/Layout'
import { Card, DisplayTitle, ErrorBox, Eyebrow, Loading, PageHeader, Reveal, Stat } from '../components/ui'
import { api } from '../lib/api'
import { ACCENT, CORAL, FAINT, MUTED, SKY, axisProps, gridProps } from '../lib/chartTheme'
import { int, money, pct, times } from '../lib/format'
import type { Lift, ModelMetrics } from '../lib/types'
import { useApi } from '../lib/useApi'

export default function Targeting() {
  const lift = useApi('lift', api.lift)
  const metrics = useApi('metrics', api.metrics)
  if (lift.loading)
    return (
      <Page>
        <Loading />
      </Page>
    )
  if (lift.error || !lift.data)
    return (
      <Page>
        <ErrorBox message={lift.error ?? 'No data'} />
      </Page>
    )

  return (
    <Page>
      <PageHeader
        eyebrow="Targeting"
        title="Contact fewer people,"
        accent="reach more buyers."
        subtitle="Rank customers by predicted response, contact the top of the list, and compare with contacting everyone. Scores are out-of-fold: each customer was scored by a model that never saw them."
      />
      <BudgetPlanner data={lift.data} />
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Reveal className="h-full">
          <GainsChart data={lift.data} />
        </Reveal>
        <Reveal delay={0.08} className="h-full">
          <DecileChart data={lift.data} />
        </Reveal>
      </div>
      <SegmentTargetingTable data={lift.data} />
      {metrics.data && <ModelQuality data={metrics.data} />}
    </Page>
  )
}

function BudgetPlanner({ data }: { data: Lift }) {
  const curve = data.curve
  const bestIdx = curve.findIndex((p) => p.share_targeted === data.best_profit_point.share_targeted)
  const [idx, setIdx] = useState(Math.max(0, bestIdx))
  const p = curve[idx]
  const everyone = curve[curve.length - 1]
  const fill = (idx / (curve.length - 1)) * 100

  return (
    <Card
      title="Budget planner"
      subtitle={`Cost ${money(data.cost_per_contact)} per contact and revenue ${money(data.revenue_per_response)} per response, from the dataset.`}
      action={
        idx === bestIdx ? (
          <span className="rounded-full bg-lime px-3 py-1 text-[10px] font-bold tracking-wider text-on-lime uppercase">
            Best profit
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setIdx(bestIdx)}
            className="rounded-full border border-accent/40 px-3 py-1 text-[10px] font-bold tracking-wider text-accent uppercase transition hover:bg-lime/10"
          >
            Jump to best
          </button>
        )
      }
    >
      <label className="block">
        <span className="flex items-end justify-between">
          <span className="text-sm text-mute">Share of customers contacted</span>
          <span className="font-display text-4xl font-bold text-accent tabular-nums">{pct(p.share_targeted, 0)}</span>
        </span>
        <input
          type="range"
          min={0}
          max={curve.length - 1}
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
          aria-label="Share of customers contacted"
          className="mt-3 h-2 w-full cursor-pointer appearance-none rounded-full [&::-moz-range-thumb]:size-5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-4 [&::-moz-range-thumb]:border-night [&::-moz-range-thumb]:bg-lime [&::-webkit-slider-thumb]:size-6 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-4 [&::-webkit-slider-thumb]:border-night [&::-webkit-slider-thumb]:bg-lime"
          style={{ background: `linear-gradient(to right, #d9ff3d ${fill}%, var(--line) ${fill}%)` }}
        />
      </label>
      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Contacts" value={int(p.customers)} />
        <Stat label="Responders" value={int(p.responders)} hint={`${pct(p.capture, 0)} of all responders`} />
        <Stat label="Response rate" value={pct(p.response_rate)} hint={`everyone: ${pct(data.base_rate)}`} />
        <Stat label="Lift" value={times(p.lift)} hint={`${p.lift >= 1 ? '+' : ''}${pct(p.lift - 1, 0)} vs everyone`} />
        <Stat
          label="Profit"
          value={<span className={p.profit < 0 ? 'text-danger' : 'text-accent'}>{money(p.profit)}</span>}
          hint={`everyone: ${money(everyone.profit)}`}
          className="col-span-2 md:col-span-1"
        />
      </div>
      <div className="mt-6 h-64">
        <ResponsiveContainer>
          <AreaChart data={curve} margin={{ left: 8, right: 16, top: 12 }}>
            <defs>
              <linearGradient id="profitFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#d9ff3d" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#d9ff3d" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="share_targeted" tickFormatter={(v) => pct(v, 0)} {...axisProps} />
            <YAxis tickFormatter={(v) => money(v)} {...axisProps} width={64} />
            <ReferenceLine y={0} stroke={MUTED} />
            <Tooltip
              cursor={{ stroke: MUTED, strokeDasharray: '4 4' }}
              content={({ payload }) =>
                payload?.[0] ? (
                  <TooltipBox
                    title={`Contact top ${pct(payload[0].payload.share_targeted, 0)}`}
                    rows={[
                      { label: 'Profit', value: money(payload[0].payload.profit) },
                      { label: 'Response rate', value: pct(payload[0].payload.response_rate) },
                    ]}
                  />
                ) : null
              }
            />
            <Area type="monotone" dataKey="profit" stroke={ACCENT} strokeWidth={2.5} fill="url(#profitFill)" />
            <ReferenceDot x={p.share_targeted} y={p.profit} r={7} fill="#d9ff3d" stroke="var(--night)" strokeWidth={3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function GainsChart({ data }: { data: Lift }) {
  const rows = [{ share_targeted: 0, capture: 0, random: 0 }, ...data.curve.map((p) => ({ ...p, random: p.share_targeted }))]
  return (
    <Card className="h-full" title="Cumulative gains" subtitle="Share of all responders reached as more customers are contacted">
      <div className="h-64">
        <ResponsiveContainer>
          <ComposedChart data={rows} margin={{ left: -8, right: 16, top: 8 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="share_targeted" type="number" domain={[0, 1]} tickFormatter={(v) => pct(v, 0)} {...axisProps} />
            <YAxis domain={[0, 1]} tickFormatter={(v) => pct(v, 0)} {...axisProps} />
            <Tooltip
              content={({ payload }) =>
                payload?.[0] ? (
                  <TooltipBox
                    title={`Top ${pct(payload[0].payload.share_targeted, 0)}`}
                    rows={[
                      { label: 'Model', value: pct(payload[0].payload.capture, 0), color: '#d9ff3d' },
                      { label: 'Random', value: pct(payload[0].payload.random, 0), color: '#7a8079' },
                    ]}
                  />
                ) : null
              }
            />
            <Line dataKey="random" stroke={MUTED} strokeDasharray="4 4" dot={false} />
            <Line dataKey="capture" stroke={ACCENT} strokeWidth={3} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function DecileChart({ data }: { data: Lift }) {
  return (
    <Card className="h-full" title="Response rate by model decile" subtitle="Decile 1 is the 10% the model ranks highest">
      <div className="h-64">
        <ResponsiveContainer>
          <BarChart data={data.deciles} margin={{ left: -8, right: 16, top: 8 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="decile" {...axisProps} />
            <YAxis tickFormatter={(v) => pct(v, 0)} {...axisProps} />
            <ReferenceLine
              y={data.base_rate}
              stroke={CORAL}
              strokeDasharray="4 4"
              label={{ value: 'everyone', fill: CORAL, fontSize: 11, position: 'insideTopRight' }}
            />
            <Tooltip
              cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
              content={({ payload }) =>
                payload?.[0] ? (
                  <TooltipBox
                    title={`Decile ${payload[0].payload.decile}`}
                    rows={[
                      { label: 'Response rate', value: pct(payload[0].payload.response_rate) },
                      { label: 'Lift', value: times(payload[0].payload.lift) },
                      { label: 'Responders', value: `${payload[0].payload.responders} / ${payload[0].payload.customers}` },
                    ]}
                  />
                ) : null
              }
            />
            <Bar dataKey="response_rate" radius={[10, 10, 0, 0]}>
              {data.deciles.map((d) => (
                <Cell key={d.decile} fill={d.lift >= 1 ? ACCENT : FAINT} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function SegmentTargetingTable({ data }: { data: Lift }) {
  const st = data.segment_targeting
  return (
    <Reveal className="mt-5">
      <Card title="Targeting by segment instead" subtitle={st.method[0].toUpperCase() + st.method.slice(1) + '.'}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-sm">
            <thead>
              <tr className="text-left text-[10px] tracking-widest text-mute uppercase">
                <th className="py-2 font-medium">Segments targeted</th>
                <th className="py-2 pl-4 text-right font-medium">Share contacted</th>
                <th className="py-2 pl-4 text-right font-medium">Response rate</th>
                <th className="py-2 pl-4 text-right font-medium">Lift</th>
                <th className="py-2 pl-4 text-right font-medium">Responders reached</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {st.rows.map((r, i) => (
                <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}>
                  <td className="py-3">{r.names.join(' + ')}</td>
                  <td className="py-3 pl-4 text-right tabular-nums">{pct(r.share_targeted, 0)}</td>
                  <td className="py-3 pl-4 text-right tabular-nums">{pct(r.response_rate)}</td>
                  <td className={`py-3 pl-4 text-right font-display font-bold tabular-nums ${r.lift > 1 ? 'text-accent' : ''}`}>
                    {times(r.lift)}
                  </td>
                  <td className="py-3 pl-4 text-right tabular-nums">{pct(r.capture, 0)}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-mute">Test-split response rate for everyone: {pct(st.test_base_rate)}.</p>
      </Card>
    </Reveal>
  )
}

function ModelQuality({ data }: { data: ModelMetrics }) {
  const h = data.holdout
  const calibration = h.calibration.map((b) => ({ x: b.mean_predicted, y: b.observed_rate, n: b.count }))
  const maxCal = Math.max(...calibration.map((c) => Math.max(c.x, c.y)), 0.1)
  const importance = data.global_importance.slice(0, 10)
  return (
    <section className="mt-24">
      <Reveal className="mb-10">
        <Eyebrow>Model quality</Eyebrow>
        <DisplayTitle accent="before you trust it.">Checked on holdout,</DisplayTitle>
      </Reveal>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="ROC AUC (holdout)" value={h.roc_auc.toFixed(3)} hint={`logistic baseline ${data.baseline_holdout_roc_auc.toFixed(3)}`} />
        <Stat
          label="PR AUC (holdout)"
          value={h.pr_auc.toFixed(3)}
          hint={`baseline ${data.baseline_holdout_pr_auc.toFixed(3)}, chance ${h.base_rate.toFixed(3)}`}
        />
        <Stat
          label={`CV ROC AUC (${data.cv_xgboost.folds}-fold)`}
          value={data.cv_xgboost.roc_auc_mean.toFixed(3)}
          hint={`plus or minus ${data.cv_xgboost.roc_auc_std.toFixed(3)}`}
        />
        <Stat label="Calibration error" value={h.expected_calibration_error.toFixed(3)} hint={`Brier ${h.brier.toFixed(3)}`} />
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Reveal className="h-full">
          <Card className="h-full" title="Calibration" subtitle={`Predicted vs observed response, ${h.n} holdout customers in 10 equal bins`}>
            <div className="h-72">
              <ResponsiveContainer>
                <ComposedChart margin={{ left: -8, right: 16, top: 8 }}>
                  <CartesianGrid {...gridProps} vertical />
                  <XAxis type="number" dataKey="x" domain={[0, maxCal]} tickFormatter={(v) => pct(v, 0)} {...axisProps} name="Predicted" />
                  <YAxis type="number" dataKey="y" domain={[0, maxCal]} tickFormatter={(v) => pct(v, 0)} {...axisProps} name="Observed" />
                  <ReferenceLine segment={[{ x: 0, y: 0 }, { x: maxCal, y: maxCal }]} stroke={MUTED} strokeDasharray="4 4" />
                  <Tooltip
                    content={({ payload }) =>
                      payload?.[0] ? (
                        <TooltipBox
                          rows={[
                            { label: 'Predicted', value: pct(payload[0].payload.x) },
                            { label: 'Observed', value: pct(payload[0].payload.y) },
                            { label: 'Customers', value: payload[0].payload.n },
                          ]}
                        />
                      ) : null
                    }
                  />
                  <Scatter data={calibration} fill={SKY} line={{ stroke: SKY, strokeWidth: 2 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Reveal>
        <Reveal delay={0.08} className="h-full">
          <Card className="h-full" title="What drives response" subtitle="Mean absolute SHAP value on the holdout set (top 10)">
            <div className="h-80">
              <ResponsiveContainer>
                <BarChart data={importance} layout="vertical" margin={{ left: 8, right: 16 }} barSize={14}>
                  <XAxis type="number" {...axisProps} tickFormatter={(v) => v.toFixed(2)} />
                  <YAxis type="category" dataKey="label" width={180} interval={0} {...axisProps} />
                  <Tooltip
                    cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
                    content={({ payload }) =>
                      payload?.[0] ? (
                        <TooltipBox
                          title={payload[0].payload.label}
                          rows={[{ label: 'Mean |SHAP|', value: Number(payload[0].value).toFixed(3) }]}
                        />
                      ) : null
                    }
                  />
                  <Bar dataKey="mean_abs_shap" fill={ACCENT} radius={[0, 10, 10, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  )
}

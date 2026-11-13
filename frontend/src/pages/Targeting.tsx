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
import { axisProps, gridProps } from '../lib/chartTheme'
import { Card, ErrorBox, Kpi, Loading, PageHeader } from '../components/ui'
import { api } from '../lib/api'
import { int, money, pct, times } from '../lib/format'
import type { Lift, ModelMetrics } from '../lib/types'
import { useApi } from '../lib/useApi'

export default function Targeting() {
  const lift = useApi('lift', api.lift)
  const metrics = useApi('metrics', api.metrics)
  if (lift.loading) return <Loading />
  if (lift.error || !lift.data) return <ErrorBox message={lift.error ?? 'No data'} />

  return (
    <>
      <PageHeader
        title="Targeting"
        subtitle={
          <>
            Rank customers by predicted response, contact the top of the list, and compare with contacting everyone.
            Scores are out-of-fold: each customer was scored by a model that never saw them.
          </>
        }
      />
      <BudgetPlanner data={lift.data} />
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <GainsChart data={lift.data} />
        <DecileChart data={lift.data} />
      </div>
      <SegmentTargetingTable data={lift.data} />
      {metrics.data && <ModelQuality data={metrics.data} />}
    </>
  )
}

function BudgetPlanner({ data }: { data: Lift }) {
  const curve = data.curve
  const bestIdx = curve.findIndex((p) => p.share_targeted === data.best_profit_point.share_targeted)
  const [idx, setIdx] = useState(Math.max(0, bestIdx))
  const p = curve[idx]
  const everyone = curve[curve.length - 1]

  return (
    <Card
      title="Budget planner"
      subtitle={`Cost ${money(data.cost_per_contact)} per contact and revenue ${money(data.revenue_per_response)} per response, from the dataset.`}
    >
      <label className="block text-sm">
        <span className="flex justify-between">
          <span>Share of customers contacted</span>
          <span className="font-semibold tabular-nums">{pct(p.share_targeted, 0)}</span>
        </span>
        <input
          type="range"
          min={0}
          max={curve.length - 1}
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
          className="mt-2 w-full"
          aria-label="Share of customers contacted"
        />
      </label>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
        <Kpi label="Contacts" value={int(p.customers)} />
        <Kpi label="Responders reached" value={int(p.responders)} hint={`${pct(p.capture, 0)} of all responders`} />
        <Kpi label="Response rate" value={pct(p.response_rate)} hint={`everyone: ${pct(data.base_rate)}`} />
        <Kpi label="Lift" value={times(p.lift)} hint={`${p.lift >= 1 ? '+' : ''}${pct(p.lift - 1, 0)} vs everyone`} />
        <Kpi
          label="Profit"
          value={<span className={p.profit < 0 ? 'text-rose-600 dark:text-rose-400' : ''}>{money(p.profit)}</span>}
          hint={`everyone: ${money(everyone.profit)}`}
        />
      </div>
      <div className="mt-6 h-64">
        <ResponsiveContainer>
          <AreaChart data={curve} margin={{ left: 8, right: 16, top: 8 }}>
            <defs>
              <linearGradient id="profitFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="share_targeted" tickFormatter={(v) => pct(v, 0)} {...axisProps} />
            <YAxis tickFormatter={(v) => money(v)} {...axisProps} width={64} />
            <ReferenceLine y={0} stroke="var(--chart-axis)" />
            <Tooltip
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
            <Area type="monotone" dataKey="profit" stroke="#6366f1" strokeWidth={2} fill="url(#profitFill)" />
            <ReferenceDot x={p.share_targeted} y={p.profit} r={6} fill="#6366f1" stroke="white" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function GainsChart({ data }: { data: Lift }) {
  const rows = [{ share_targeted: 0, capture: 0, random: 0 }, ...data.curve.map((p) => ({ ...p, random: p.share_targeted }))]
  return (
    <Card title="Cumulative gains" subtitle="Share of all responders reached as more customers are contacted">
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
                      { label: 'Model', value: pct(payload[0].payload.capture, 0), color: '#14b8a6' },
                      { label: 'Random', value: pct(payload[0].payload.random, 0), color: '#94a3b8' },
                    ]}
                  />
                ) : null
              }
            />
            <Line dataKey="random" stroke="#94a3b8" strokeDasharray="4 4" dot={false} />
            <Line dataKey="capture" stroke="#14b8a6" strokeWidth={2.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function DecileChart({ data }: { data: Lift }) {
  return (
    <Card title="Response rate by model decile" subtitle="Decile 1 is the 10% the model ranks highest">
      <div className="h-64">
        <ResponsiveContainer>
          <BarChart data={data.deciles} margin={{ left: -8, right: 16, top: 8 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="decile" {...axisProps} />
            <YAxis tickFormatter={(v) => pct(v, 0)} {...axisProps} />
            <ReferenceLine
              y={data.base_rate}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: 'everyone', fill: '#f59e0b', fontSize: 11, position: 'insideTopRight' }}
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
            <Bar dataKey="response_rate" radius={[4, 4, 0, 0]}>
              {data.deciles.map((d) => (
                <Cell key={d.decile} fill={d.lift >= 1 ? '#6366f1' : '#cbd5e1'} />
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
    <Card className="mt-6" title="Targeting by segment instead" subtitle={st.method + '.'}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400">
              <th className="py-2 font-medium">Segments targeted</th>
              <th className="py-2 pl-4 text-right font-medium">Share contacted</th>
              <th className="py-2 pl-4 text-right font-medium">Response rate</th>
              <th className="py-2 pl-4 text-right font-medium">Lift</th>
              <th className="py-2 pl-4 text-right font-medium">Responders reached</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {st.rows.map((r, i) => (
              <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}>
                <td className="py-2">{r.names.join(' + ')}</td>
                <td className="py-2 pl-4 text-right tabular-nums">{pct(r.share_targeted, 0)}</td>
                <td className="py-2 pl-4 text-right tabular-nums">{pct(r.response_rate)}</td>
                <td className="py-2 pl-4 text-right font-medium tabular-nums">{times(r.lift)}</td>
                <td className="py-2 pl-4 text-right tabular-nums">{pct(r.capture, 0)}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
        Test-split response rate for everyone: {pct(st.test_base_rate)}.
      </p>
    </Card>
  )
}

function ModelQuality({ data }: { data: ModelMetrics }) {
  const h = data.holdout
  const calibration = h.calibration.map((b) => ({ x: b.mean_predicted, y: b.observed_rate, n: b.count }))
  const maxCal = Math.max(...calibration.map((c) => Math.max(c.x, c.y)), 0.1)
  const importance = data.global_importance.slice(0, 10).reverse()
  return (
    <>
      <h2 className="mt-10 mb-4 text-lg font-semibold">Model quality</h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="ROC AUC (holdout)" value={h.roc_auc.toFixed(3)} hint={`logistic baseline ${data.baseline_holdout_roc_auc.toFixed(3)}`} />
        <Kpi label="PR AUC (holdout)" value={h.pr_auc.toFixed(3)} hint={`baseline ${data.baseline_holdout_pr_auc.toFixed(3)}, chance ${h.base_rate.toFixed(3)}`} />
        <Kpi
          label={`CV ROC AUC (${data.cv_xgboost.folds}-fold)`}
          value={data.cv_xgboost.roc_auc_mean.toFixed(3)}
          hint={`plus or minus ${data.cv_xgboost.roc_auc_std.toFixed(3)}`}
        />
        <Kpi label="Calibration error" value={h.expected_calibration_error.toFixed(3)} hint={`Brier ${h.brier.toFixed(3)}`} />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Calibration" subtitle={`Predicted vs observed response, ${h.n} holdout customers in 10 equal bins`}>
          <div className="h-64">
            <ResponsiveContainer>
              <ComposedChart margin={{ left: -8, right: 16, top: 8 }}>
                <CartesianGrid {...gridProps} vertical />
                <XAxis type="number" dataKey="x" domain={[0, maxCal]} tickFormatter={(v) => pct(v, 0)} {...axisProps} name="Predicted" />
                <YAxis type="number" dataKey="y" domain={[0, maxCal]} tickFormatter={(v) => pct(v, 0)} {...axisProps} name="Observed" />
                <ReferenceLine segment={[{ x: 0, y: 0 }, { x: maxCal, y: maxCal }]} stroke="#94a3b8" strokeDasharray="4 4" />
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
                <Scatter data={calibration} fill="#ec4899" line={{ stroke: '#ec4899', strokeWidth: 1.5 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="What drives response" subtitle="Mean absolute SHAP value on the holdout set (top 10)">
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
                <Bar dataKey="mean_abs_shap" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </>
  )
}

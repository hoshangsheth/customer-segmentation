import { motion } from 'motion/react'
import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { TooltipBox } from '../components/chart'
import { axisProps, gridProps } from '../lib/chartTheme'
import { Card, ErrorBox, Loading, PageHeader, SegmentDot } from '../components/ui'
import { api } from '../lib/api'
import { CHANNEL_LABELS, int, money, num, pct, segmentColor, SPEND_COLORS, SPEND_LABELS, times } from '../lib/format'
import type { Means, Projection, SegmentProfile, SegmentsOverview } from '../lib/types'
import { useApi } from '../lib/useApi'

const MEASURES: { key: keyof Means; label: string; fmt: (v: number) => string }[] = [
  { key: 'income', label: 'Income', fmt: money },
  { key: 'monetary', label: 'Total spend (2 yrs)', fmt: money },
  { key: 'frequency', label: 'Purchases', fmt: (v) => num(v) },
  { key: 'avg_order_value', label: 'Avg order value', fmt: money },
  { key: 'recency', label: 'Days since last purchase', fmt: (v) => num(v, 0) },
  { key: 'deal_share', label: 'Purchases on discount', fmt: (v) => pct(v, 0) },
  { key: 'web_visits', label: 'Web visits / month', fmt: (v) => num(v) },
  { key: 'children', label: 'Children at home', fmt: (v) => num(v, 2) },
  { key: 'age', label: 'Age', fmt: (v) => num(v, 0) },
  { key: 'tenure_days', label: 'Days as customer', fmt: (v) => num(v, 0) },
]

export default function Segments() {
  const seg = useApi('segments', api.segments)
  const proj = useApi('projection', api.projection)
  const [params, setParams] = useSearchParams()

  if (seg.loading) return <Loading />
  if (seg.error || !seg.data) return <ErrorBox message={seg.error ?? 'No data'} />

  const segments = seg.data.segments
  const selectedId = Number(params.get('id') ?? segments[0].segment_id)
  const selected = segments.find((s) => s.segment_id === selectedId) ?? segments[0]

  return (
    <>
      <PageHeader
        title="Segments"
        subtitle="K-Means on scaled behaviour and household features (campaign history left out, so response rates are an honest check). Pick a segment to see its profile."
      />
      <div className="mb-6 flex flex-wrap gap-2">
        {segments.map((s) => (
          <button
            key={s.segment_id}
            onClick={() => setParams({ id: String(s.segment_id) }, { replace: true })}
            className={`relative flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors ${
              s.segment_id === selected.segment_id
                ? 'border-transparent text-white'
                : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-600'
            }`}
          >
            {s.segment_id === selected.segment_id && (
              <motion.span
                layoutId="seg-pill"
                className="absolute inset-0 rounded-full"
                style={{ backgroundColor: segmentColor(s.segment_id) }}
                transition={{ type: 'spring', stiffness: 400, damping: 32 }}
              />
            )}
            <span className="relative flex items-center gap-2">
              {s.segment_id !== selected.segment_id && <SegmentDot color={segmentColor(s.segment_id)} />}
              {s.name}
            </span>
          </button>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-5">
        <Card
          className="xl:col-span-3"
          title="Customers in 2-D"
          subtitle={
            proj.data
              ? `PCA of the clustering space; the two axes keep ${pct(proj.data.explained_variance.reduce((a, b) => a + b, 0), 0)} of the variance.`
              : 'PCA of the clustering space'
          }
        >
          {proj.data ? <ProjectionChart data={proj.data} segments={segments} selected={selected.segment_id} /> : <Loading />}
        </Card>
        <ProfileCard segment={selected} population={seg.data.population} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Spend mix" subtitle="Share of each segment's spend by category">
          <MixChart segments={segments} field="spend_mix" labels={SPEND_LABELS} colors={SPEND_COLORS} />
        </Card>
        <Card title="Channel mix" subtitle="Share of purchases by channel">
          <MixChart
            segments={segments}
            field="channel_mix"
            labels={CHANNEL_LABELS}
            colors={{ web: '#0ea5e9', catalog: '#8b5cf6', store: '#14b8a6' }}
          />
        </Card>
      </div>

      <KSelectionCard data={seg.data.k_selection} />
    </>
  )
}

function ProjectionChart({
  data,
  segments,
  selected,
}: {
  data: Projection
  segments: SegmentProfile[]
  selected: number
}) {
  const bySegment = useMemo(() => {
    const groups = new Map<number, { x: number; y: number }[]>()
    for (const p of data.points) {
      if (!groups.has(p.segment)) groups.set(p.segment, [])
      groups.get(p.segment)!.push({ x: p.x, y: p.y })
    }
    return groups
  }, [data])
  const names = Object.fromEntries(segments.map((s) => [s.segment_id, s.name]))

  return (
    <div className="h-80 sm:h-96">
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
          <CartesianGrid {...gridProps} vertical />
          <XAxis type="number" dataKey="x" name="PC1" {...axisProps} />
          <YAxis type="number" dataKey="y" name="PC2" {...axisProps} />
          <Tooltip
            cursor={false}
            content={({ payload }) =>
              payload?.[0] ? <TooltipBox title={names[Number(payload[0].payload.segment)] ?? ''} rows={[]} /> : null
            }
          />
          {[...bySegment.entries()].map(([id, pts]) => (
            <Scatter
              key={id}
              data={pts.map((p) => ({ ...p, segment: id }))}
              fill={segmentColor(id)}
              fillOpacity={id === selected ? 0.85 : 0.18}
              shape="circle"
              isAnimationActive={false}
              r={2}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

function ProfileCard({ segment, population }: { segment: SegmentProfile; population: SegmentsOverview['population'] }) {
  const rateLift = segment.response_rate / population.response_rate
  return (
    <Card className="xl:col-span-2">
      <motion.div key={segment.segment_id} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}>
        <div className="flex items-center gap-2">
          <SegmentDot color={segmentColor(segment.segment_id)} />
          <h2 className="text-lg font-semibold">{segment.name}</h2>
        </div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{segment.tagline}</p>
        <div className="mt-4 grid grid-cols-3 gap-3 text-center">
          <Stat label="Customers" value={`${int(segment.size)}`} sub={pct(segment.share, 0)} />
          <Stat label="Response" value={pct(segment.response_rate)} sub={`${times(rateLift, 1)} average`} />
          <Stat label="Took a past offer" value={pct(segment.prior_accept_rate, 0)} />
        </div>
        <ul className="mt-4 space-y-1 text-sm">
          {segment.traits.map((t) => (
            <li key={t} className="flex gap-2">
              <span className="mt-2 size-1 shrink-0 rounded-full bg-slate-400" />
              {t}
            </li>
          ))}
        </ul>
        <table className="mt-4 w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400">
              <th className="py-1 font-medium">Measure</th>
              <th className="py-1 text-right font-medium">Segment</th>
              <th className="py-1 text-right font-medium">Everyone</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {MEASURES.map((m) => (
              <tr key={m.key}>
                <td className="py-1.5 text-slate-600 dark:text-slate-400">{m.label}</td>
                <td className="py-1.5 text-right font-medium tabular-nums">{m.fmt(segment.means[m.key])}</td>
                <td className="py-1.5 text-right text-slate-500 tabular-nums">{m.fmt(population[m.key])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </motion.div>
    </Card>
  )
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-2.5 dark:bg-slate-800/60">
      <div className="text-[11px] text-slate-500 dark:text-slate-400">{label}</div>
      <div className="font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-[11px] text-slate-500 dark:text-slate-400">{sub}</div>}
    </div>
  )
}

function MixChart({
  segments,
  field,
  labels,
  colors,
}: {
  segments: SegmentProfile[]
  field: 'spend_mix' | 'channel_mix'
  labels: Record<string, string>
  colors: Record<string, string>
}) {
  const keys = Object.keys(labels)
  const rows = segments.map((s) => ({ name: s.name, ...s[field] }))
  return (
    <div style={{ height: 48 * segments.length + 60 }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 8 }} barSize={18}>
          <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => pct(v, 0)} {...axisProps} />
          <YAxis type="category" dataKey="name" width={150} {...axisProps} />
          <Tooltip
            cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
            content={({ payload, label }) =>
              payload?.length ? (
                <TooltipBox
                  title={label}
                  rows={payload.map((p) => ({
                    label: labels[String(p.dataKey)],
                    value: pct(Number(p.value)),
                    color: String(p.color),
                  }))}
                />
              ) : null
            }
          />
          <Legend formatter={(v) => labels[v] ?? v} wrapperStyle={{ fontSize: 12 }} />
          {keys.map((k, i) => (
            <Bar
              key={k}
              dataKey={k}
              stackId="mix"
              fill={colors[k]}
              radius={i === keys.length - 1 ? [0, 4, 4, 0] : i === 0 ? [4, 0, 0, 4] : 0}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function KSelectionCard({ data }: { data: SegmentsOverview['k_selection'] }) {
  return (
    <Card
      className="mt-6"
      title="How the number of segments was chosen"
      subtitle={`k = ${data.chosen_k} (${data.rule}). The elbow of the inertia curve is at k = ${data.elbow_k}.`}
    >
      <div className="grid gap-6 md:grid-cols-2">
        <KChart scores={data.scores} field="silhouette" label="Silhouette (higher is better)" chosen={data.chosen_k} />
        <KChart scores={data.scores} field="inertia" label="Inertia (elbow)" chosen={data.chosen_k} />
      </div>
    </Card>
  )
}

function KChart({
  scores,
  field,
  label,
  chosen,
}: {
  scores: SegmentsOverview['k_selection']['scores']
  field: 'silhouette' | 'inertia'
  label: string
  chosen: number
}) {
  return (
    <div>
      <div className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">{label}</div>
      <div className="h-48">
        <ResponsiveContainer>
          <LineChart data={scores} margin={{ left: -8, right: 8 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="k" {...axisProps} />
            <YAxis {...axisProps} tickFormatter={(v) => (field === 'inertia' ? `${Math.round(v / 1000)}k` : v.toFixed(2))} domain={['auto', 'auto']} />
            <ReferenceLine x={chosen} stroke="#6366f1" strokeDasharray="4 4" />
            <Tooltip
              content={({ payload }) =>
                payload?.[0] ? (
                  <TooltipBox
                    title={`k = ${payload[0].payload.k}`}
                    rows={[{ label, value: Number(payload[0].value).toFixed(field === 'inertia' ? 0 : 3) }]}
                  />
                ) : null
              }
            />
            <Line type="monotone" dataKey={field} stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

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
import { Page } from '../components/Layout'
import { Card, ErrorBox, Loading, PageHeader, PillTabs, Reveal, SegmentDot } from '../components/ui'
import { api } from '../lib/api'
import { ACCENT, axisProps, gridProps } from '../lib/chartTheme'
import {
  CHANNEL_COLORS,
  CHANNEL_LABELS,
  int,
  money,
  num,
  pct,
  segmentColor,
  SPEND_COLORS,
  SPEND_LABELS,
  times,
} from '../lib/format'
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

  if (seg.loading)
    return (
      <Page>
        <Loading />
      </Page>
    )
  if (seg.error || !seg.data)
    return (
      <Page>
        <ErrorBox message={seg.error ?? 'No data'} />
      </Page>
    )

  const segments = seg.data.segments
  const selectedId = Number(params.get('id') ?? segments[0].segment_id)
  const selected = segments.find((s) => s.segment_id === selectedId) ?? segments[0]

  return (
    <Page>
      <PageHeader
        eyebrow="Segments"
        title="Who your customers"
        accent="really are."
        subtitle="K-Means on scaled behaviour and household features. Campaign history is left out, so response rates are an honest check. Pick a segment to see its profile."
      />

      <div className="mb-8">
        <PillTabs
          layoutId="segment-tab"
          value={selected.segment_id}
          onChange={(id) => setParams({ id: String(id) }, { replace: true })}
          items={segments.map((s) => ({
            value: s.segment_id,
            label: (
              <>
                <SegmentDot color={segmentColor(s.segment_id)} className="size-2.5 ring-2 ring-black/10" />
                {s.name}
              </>
            ),
          }))}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-5 xl:items-start">
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

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Reveal>
          <Card title="Spend mix" subtitle="Share of each segment's spend by category">
            <MixChart segments={segments} field="spend_mix" labels={SPEND_LABELS} colors={SPEND_COLORS} />
          </Card>
        </Reveal>
        <Reveal delay={0.08}>
          <Card title="Channel mix" subtitle="Share of purchases by channel">
            <MixChart segments={segments} field="channel_mix" labels={CHANNEL_LABELS} colors={CHANNEL_COLORS} />
          </Card>
        </Reveal>
      </div>

      <KSelectionCard data={seg.data.k_selection} />
    </Page>
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
    <div className="h-80 sm:h-[26rem]">
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
              fillOpacity={id === selected ? 0.9 : 0.15}
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
  const color = segmentColor(segment.segment_id)
  return (
    <section className="relative overflow-hidden rounded-3xl border border-line bg-surface p-6 xl:col-span-2">
      <div
        className="pointer-events-none absolute -top-24 -right-24 size-64 rounded-full"
        style={{ background: `radial-gradient(circle, ${color}33, transparent 70%)` }}
        aria-hidden
      />
      <motion.div key={segment.segment_id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="relative">
        <p className="text-[10px] tracking-widest text-mute uppercase">Segment profile</p>
        <h2 className="mt-1 font-display text-3xl font-bold tracking-tight uppercase">{segment.name}</h2>
        <p className="mt-2 text-sm text-mute">{segment.tagline}</p>
        <div className="mt-5 grid grid-cols-3 gap-2">
          <MiniStat label="Customers" value={int(segment.size)} sub={pct(segment.share, 0)} />
          <MiniStat label="Response" value={pct(segment.response_rate)} sub={`${times(rateLift, 1)} avg`} highlight={rateLift >= 1} />
          <MiniStat label="Past offer" value={pct(segment.prior_accept_rate, 0)} sub="took one" />
        </div>
        <ul className="mt-5 space-y-1.5 text-sm">
          {segment.traits.map((t) => (
            <li key={t} className="flex gap-2.5">
              <span className="mt-2 size-1.5 shrink-0 rounded-full bg-lime" />
              {t}
            </li>
          ))}
        </ul>
        <table className="mt-5 w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] tracking-widest text-mute uppercase">
              <th className="py-1.5 font-medium">Measure</th>
              <th className="py-1.5 text-right font-medium">Segment</th>
              <th className="py-1.5 text-right font-medium">Everyone</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {MEASURES.map((m) => (
              <tr key={m.key}>
                <td className="py-2 text-mute">{m.label}</td>
                <td className="py-2 text-right font-semibold tabular-nums">{m.fmt(segment.means[m.key])}</td>
                <td className="py-2 text-right text-mute tabular-nums">{m.fmt(population[m.key])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </motion.div>
    </section>
  )
}

function MiniStat({ label, value, sub, highlight }: { label: string; value: string; sub?: string; highlight?: boolean }) {
  return (
    <div className={`rounded-2xl p-3 ${highlight ? 'bg-lime text-on-lime' : 'bg-raised'}`}>
      <div className={`text-[10px] tracking-widest uppercase ${highlight ? 'text-on-lime/70' : 'text-mute'}`}>{label}</div>
      <div className="mt-0.5 font-display text-xl font-bold tabular-nums">{value}</div>
      {sub && <div className={`text-[11px] ${highlight ? 'text-on-lime/70' : 'text-mute'}`}>{sub}</div>}
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
    <div style={{ height: 52 * segments.length + 64 }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 8 }} barSize={20}>
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
          <Legend formatter={(v) => <span className="text-mute">{labels[v] ?? v}</span>} wrapperStyle={{ fontSize: 12 }} iconType="circle" />
          {keys.map((k, i) => (
            <Bar
              key={k}
              dataKey={k}
              stackId="mix"
              fill={colors[k]}
              radius={i === keys.length - 1 ? [0, 10, 10, 0] : i === 0 ? [10, 0, 0, 10] : 0}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function KSelectionCard({ data }: { data: SegmentsOverview['k_selection'] }) {
  return (
    <Reveal className="mt-5">
      <Card
        title="How the number of segments was chosen"
        subtitle={`k = ${data.chosen_k} (${data.rule}). The elbow of the inertia curve is at k = ${data.elbow_k}.`}
      >
        <div className="grid gap-6 md:grid-cols-2">
          <KChart scores={data.scores} field="silhouette" label="Silhouette (higher is better)" chosen={data.chosen_k} />
          <KChart scores={data.scores} field="inertia" label="Inertia (elbow)" chosen={data.chosen_k} />
        </div>
      </Card>
    </Reveal>
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
      <div className="mb-2 text-[10px] tracking-widest text-mute uppercase">{label}</div>
      <div className="h-52">
        <ResponsiveContainer>
          <LineChart data={scores} margin={{ left: -8, right: 8, top: 8 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="k" {...axisProps} />
            <YAxis
              {...axisProps}
              tickFormatter={(v) => (field === 'inertia' ? `${Math.round(v / 1000)}k` : v.toFixed(2))}
              domain={['auto', 'auto']}
            />
            <ReferenceLine x={chosen} stroke={ACCENT} strokeDasharray="4 4" />
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
            <Line type="monotone" dataKey={field} stroke={ACCENT} strokeWidth={2.5} dot={{ r: 4, fill: ACCENT, strokeWidth: 0 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

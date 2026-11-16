import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Loader2, Search, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { TooltipBox } from '../../components/chart'
import { Card, ErrorBox, SegmentDot } from '../../components/ui'
import { api } from '../../lib/api'
import type { CustomerDetail, CustomerPage, SortKey, Summary } from '../../lib/batchTypes'
import { ACCENT, DANGER, MUTED, axisProps } from '../../lib/chartTheme'
import { int, money, num, pct, segmentColor } from '../../lib/format'

const PAGE = 25
const SORTS: { value: SortKey; label: string; order: 'asc' | 'desc' }[] = [
  { value: 'rank', label: 'Most likely to respond', order: 'asc' },
  { value: 'monetary', label: 'Highest spend', order: 'desc' },
  { value: 'recency', label: 'Most recent buyers', order: 'asc' },
  { value: 'income', label: 'Highest income', order: 'desc' },
  { value: 'customer_id', label: 'Customer ID', order: 'asc' },
]

export default function CustomerTable({ summary, topShare }: { summary: Summary; topShare: number }) {
  const [offset, setOffset] = useState(0)
  const [segment, setSegment] = useState<number>()
  const [sort, setSort] = useState<SortKey>('rank')
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [result, setResult] = useState<{ key: string; page?: CustomerPage; error?: string }>()
  const [selected, setSelected] = useState<string>()
  const hasOutcome = summary.preparation.has_outcome
  const cutoff = Math.ceil(summary.customers * topShare)

  // Debounce the search box
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(search)
      setOffset(0)
    }, 300)
    return () => clearTimeout(t)
  }, [search])

  const order = SORTS.find((s) => s.value === sort)!.order
  const key = JSON.stringify([summary.job_id, offset, segment, q, sort])
  useEffect(() => {
    let alive = true
    api.batch
      .customers(summary.job_id, { offset, limit: PAGE, segment_id: segment, q, sort, order })
      .then((page) => alive && setResult({ key, page }))
      .catch((e: Error) => alive && setResult({ key, error: e.message }))
    return () => {
      alive = false
    }
  }, [key, summary.job_id, offset, segment, q, sort, order])

  const loading = result?.key !== key
  const page = result?.page

  return (
    <Card
      className="mt-5"
      title="Customers"
      subtitle={`Ranked by chance to respond. Rows marked "In list" are in the top ${pct(topShare, 0)} set in the planner. Click a customer for the full explanation.`}
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="relative min-w-52 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-mute" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search customer ID"
            aria-label="Search customer ID"
            className="w-full rounded-full border border-line bg-night py-2.5 pr-4 pl-10 text-sm outline-none focus:border-accent"
          />
        </label>
        <select
          aria-label="Segment"
          value={segment ?? ''}
          onChange={(e) => {
            setSegment(e.target.value === '' ? undefined : Number(e.target.value))
            setOffset(0)
          }}
          className="rounded-full border border-line bg-night px-4 py-2.5 text-sm outline-none focus:border-accent"
        >
          <option value="">All segments</option>
          {summary.segments.map((s) => (
            <option key={s.segment_id} value={s.segment_id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort"
          value={sort}
          onChange={(e) => {
            setSort(e.target.value as SortKey)
            setOffset(0)
          }}
          className="rounded-full border border-line bg-night px-4 py-2.5 text-sm outline-none focus:border-accent"
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {result?.error && !loading ? (
        <ErrorBox message={result.error} />
      ) : (
        <div className={`overflow-x-auto transition-opacity ${loading ? 'opacity-50' : ''}`}>
          <table className="w-full min-w-[48rem] text-sm">
            <thead>
              <tr className="text-left text-[10px] tracking-widest text-mute uppercase">
                <th className="py-2 pr-3 font-medium">Rank</th>
                <th className="py-2 pr-3 font-medium">Customer</th>
                <th className="py-2 pr-3 font-medium">Segment</th>
                <th className="py-2 pr-3 font-medium">Chance</th>
                <th className="py-2 pr-3 font-medium">Main reasons</th>
                <th className="py-2 pr-3 font-medium">List</th>
                {hasOutcome && <th className="py-2 font-medium">Responded</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {page?.rows.map((r) => (
                <tr
                  key={r.customer_id}
                  onClick={() => setSelected(r.customer_id)}
                  onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setSelected(r.customer_id)}
                  tabIndex={0}
                  className="cursor-pointer transition-colors hover:bg-raised focus:bg-raised focus:outline-none"
                >
                  <td className="py-3 pr-3 font-display font-bold tabular-nums">{int(r.rank)}</td>
                  <td className="py-3 pr-3 font-medium">{r.customer_id}</td>
                  <td className="py-3 pr-3">
                    <span className="flex items-center gap-2">
                      <SegmentDot color={segmentColor(r.segment_id)} />
                      {r.segment_name}
                    </span>
                  </td>
                  <td className="py-3 pr-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-raised">
                        <div className="h-full rounded-full bg-lime" style={{ width: `${r.probability * 100}%` }} />
                      </div>
                      <span className="tabular-nums">{pct(r.probability, 0)}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-3">
                    <div className="flex flex-wrap gap-1">
                      {r.reasons.map((x) => (
                        <span
                          key={x.label}
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] ${
                            x.direction === 'up' ? 'bg-lime/15 text-accent' : 'bg-danger/10 text-danger'
                          }`}
                        >
                          {x.direction === 'up' ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />}
                          {x.label}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 pr-3">
                    {r.rank <= cutoff ? (
                      <span className="rounded-full bg-lime px-2 py-0.5 text-[10px] font-bold tracking-wider text-on-lime uppercase">In list</span>
                    ) : (
                      <span className="text-xs text-mute">no</span>
                    )}
                  </td>
                  {hasOutcome && <td className="py-3 text-mute">{r.outcome === null ? 'unknown' : r.outcome ? 'yes' : 'no'}</td>}
                </tr>
              ))}
              {page && page.rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-mute">
                    No customers match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          {!page && <div className="py-10 text-center text-mute">Loading customers</div>}
        </div>
      )}

      {page && page.total > 0 && (
        <div className="mt-4 flex items-center justify-between gap-3 text-sm">
          <span className="text-mute">
            {int(offset + 1)} to {int(Math.min(offset + PAGE, page.total))} of {int(page.total)}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - PAGE))}
              aria-label="Previous page"
              className="grid size-9 place-items-center rounded-full border border-line hover:border-accent/40 disabled:opacity-40"
            >
              <ChevronLeft className="size-4" />
            </button>
            <button
              type="button"
              disabled={offset + PAGE >= page.total}
              onClick={() => setOffset((o) => o + PAGE)}
              aria-label="Next page"
              className="grid size-9 place-items-center rounded-full border border-line hover:border-accent/40 disabled:opacity-40"
            >
              <ChevronRight className="size-4" />
            </button>
          </div>
        </div>
      )}

      <AnimatePresence>
        {selected && <CustomerDrawer jobId={summary.job_id} customerId={selected} cutoff={cutoff} onClose={() => setSelected(undefined)} />}
      </AnimatePresence>
    </Card>
  )
}

function CustomerDrawer({ jobId, customerId, cutoff, onClose }: { jobId: string; customerId: string; cutoff: number; onClose: () => void }) {
  const [state, setState] = useState<{ id: string; data?: CustomerDetail; error?: string }>()

  useEffect(() => {
    let alive = true
    api.batch
      .customer(jobId, customerId)
      .then((data) => alive && setState({ id: customerId, data }))
      .catch((e: Error) => alive && setState({ id: customerId, error: e.message }))
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => {
      alive = false
      window.removeEventListener('keydown', onKey)
    }
  }, [jobId, customerId, onClose])

  const d = state?.id === customerId ? state.data : undefined
  const reasons = d ? [...d.reasons].sort((a, b) => b.shap - a.shap) : []
  const profile = d
    ? [
        ['Household income', money(d.profile.income)],
        ['Age', num(d.profile.age, 0)],
        ['Days since last purchase', num(d.profile.recency, 0)],
        ['Purchases', num(d.profile.frequency, 0)],
        ['Total spend', money(d.profile.monetary)],
        ['Earlier offers accepted', num(d.profile.prior_accepts, 0)],
      ]
    : []

  return (
    <>
      <motion.div
        className="fixed inset-0 z-[60] bg-night/60 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />
      <motion.aside
        role="dialog"
        aria-modal="true"
        aria-label={`Customer ${customerId}`}
        className="fixed inset-y-0 right-0 z-[61] w-full max-w-md overflow-y-auto border-l border-line bg-surface p-6 shadow-2xl"
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 380, damping: 38 }}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] tracking-widest text-mute uppercase">Customer</p>
            <h2 className="font-display text-3xl font-bold tracking-tight">{customerId}</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="grid size-10 place-items-center rounded-full border border-line hover:border-accent/40">
            <X className="size-4" />
          </button>
        </div>

        {state?.error && state.id === customerId ? (
          <div className="mt-6">
            <ErrorBox message={state.error} />
          </div>
        ) : !d ? (
          <div className="mt-10 flex items-center gap-2 text-sm text-mute">
            <Loader2 className="size-4 animate-spin text-accent" /> Loading
          </div>
        ) : (
          <>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-lime p-4 text-on-lime">
                <div className="text-[10px] tracking-widest uppercase opacity-70">Chance to respond</div>
                <div className="font-display text-4xl font-bold tabular-nums">{pct(d.probability, 0)}</div>
              </div>
              <div className="rounded-2xl bg-raised p-4">
                <div className="text-[10px] tracking-widest text-mute uppercase">Rank</div>
                <div className="font-display text-4xl font-bold tabular-nums">{int(d.rank)}</div>
                <div className="text-xs text-mute">
                  top {pct(d.top_percent, 1)}
                  {d.rank <= cutoff ? ' · in your list' : ''}
                </div>
              </div>
            </div>
            <p className="mt-4 flex items-center gap-2 text-sm">
              <SegmentDot color={segmentColor(d.segment_id)} />
              <span className="font-semibold">{d.segment_name}</span>
              {d.outcome !== null && d.outcome !== undefined && <span className="text-mute">· responded: {d.outcome ? 'yes' : 'no'}</span>}
            </p>

            <h3 className="mt-6 font-display text-lg font-bold">Why this score</h3>
            <p className="text-xs text-mute">Bars to the right raise the chance, bars to the left lower it.</p>
            <div className="mt-2 h-72">
              <ResponsiveContainer>
                <BarChart data={reasons} layout="vertical" margin={{ left: 4, right: 8 }} barSize={14}>
                  <XAxis type="number" {...axisProps} tickFormatter={(v) => v.toFixed(1)} />
                  <YAxis type="category" dataKey="label" width={150} interval={0} {...axisProps} tick={{ ...axisProps.tick, fontSize: 11 }} />
                  <ReferenceLine x={0} stroke={MUTED} />
                  <Tooltip
                    cursor={{ fill: 'var(--chart-grid)', opacity: 0.4 }}
                    content={({ payload }) =>
                      payload?.[0] ? (
                        <TooltipBox
                          title={payload[0].payload.label}
                          rows={[
                            { label: 'Value', value: num(payload[0].payload.value, 2) },
                            { label: 'Effect', value: Number(payload[0].payload.shap).toFixed(3) },
                          ]}
                        />
                      ) : null
                    }
                  />
                  <Bar dataKey="shap" radius={8}>
                    {reasons.map((r) => (
                      <Cell key={r.feature} fill={r.shap >= 0 ? ACCENT : DANGER} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <h3 className="mt-4 font-display text-lg font-bold">Profile</h3>
            <dl className="mt-2 divide-y divide-line text-sm">
              {profile.map(([k, v]) => (
                <div key={k} className="flex justify-between py-2">
                  <dt className="text-mute">{k}</dt>
                  <dd className="font-semibold tabular-nums">{v}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </motion.aside>
    </>
  )
}

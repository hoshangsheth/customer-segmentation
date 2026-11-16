import { ArrowUpRight, Lightbulb, Mail, Megaphone, ShoppingBag, Sparkles, Store, TriangleAlert } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { Page } from '../components/Layout'
import { Badge, Card, ErrorBox, Loading, PageHeader, SegmentDot } from '../components/ui'
import { api } from '../lib/api'
import { pct, segmentColor } from '../lib/format'
import type { Persona } from '../lib/types'
import { useApi } from '../lib/useApi'

const CHANNEL_ICONS: Record<string, typeof Mail> = { email: Mail, web: ShoppingBag, catalog: Megaphone, store: Store }

export default function Insights() {
  const health = useApi('health', api.health)
  const segments = useApi('segments', api.segments)
  const [selected, setSelected] = useState<number>()

  if (segments.loading)
    return (
      <Page>
        <Loading />
      </Page>
    )
  if (segments.error || !segments.data)
    return (
      <Page>
        <ErrorBox message={segments.error ?? 'No data'} />
      </Page>
    )
  const list = segments.data.segments
  const id = selected ?? list[0].segment_id

  return (
    <Page>
      <PageHeader
        eyebrow="AI insights"
        title="Personas and campaigns,"
        accent="grounded in the numbers."
        subtitle="Written from each segment's computed statistics. The model only sees the numbers on the Segments page, and is told not to invent any."
      >
        {health.data && (
          <Badge tone={health.data.ai_available ? 'lime' : 'outline'}>
            <Sparkles className="size-3" />
            {health.data.ai_available ? `AI on: ${health.data.ai_provider}` : 'AI off: set GEMINI_API_KEY'}
          </Badge>
        )}
      </PageHeader>
      <div className="grid gap-5 lg:grid-cols-[18rem_1fr]">
        <nav className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible" aria-label="Segments">
          {list.map((s, i) => {
            const active = s.segment_id === id
            return (
              <button
                key={s.segment_id}
                onClick={() => setSelected(s.segment_id)}
                aria-pressed={active}
                className={`group relative flex shrink-0 items-center gap-3 rounded-3xl border px-4 py-4 text-left transition-colors ${
                  active ? 'border-lime bg-lime text-on-lime' : 'border-line bg-surface hover:border-accent/40'
                }`}
              >
                <span className={`font-display text-2xl font-bold ${active ? 'text-on-lime/40' : 'text-ink/20'}`}>0{i + 1}</span>
                <span className="flex-1">
                  <span className="block font-display font-bold">{s.name}</span>
                  <span className={`text-xs ${active ? 'text-on-lime/70' : 'text-mute'}`}>{pct(s.share, 0)} of customers</span>
                </span>
                <SegmentDot color={segmentColor(s.segment_id)} className={`size-3 ${active ? 'ring-2 ring-on-lime/30' : ''}`} />
              </button>
            )
          })}
        </nav>
        <AnimatePresence mode="wait">
          <motion.div
            key={id}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            transition={{ duration: 0.25 }}
          >
            <PersonaView segmentId={id} />
          </motion.div>
        </AnimatePresence>
      </div>
    </Page>
  )
}

function PersonaView({ segmentId }: { segmentId: number }) {
  const { data, error, loading } = useApi<Persona>(`persona-${segmentId}`, () => api.persona(segmentId))
  if (loading) return <Loading label="Writing persona" />
  if (error || !data) return <ErrorBox message={error ?? 'No data'} />
  const color = segmentColor(data.segment_id)

  return (
    <div className="space-y-5">
      <section className="relative overflow-hidden rounded-3xl border border-line bg-surface p-8">
        <div
          className="pointer-events-none absolute -top-28 -right-20 size-72 rounded-full"
          style={{ background: `radial-gradient(circle, ${color}30, transparent 70%)` }}
          aria-hidden
        />
        <div className="relative">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs tracking-[0.3em] text-accent uppercase">— Persona</p>
            <Badge tone={data.source === 'llm' ? 'lime' : 'muted'}>{data.source === 'llm' ? `AI: ${data.model}` : 'Rule-based'}</Badge>
          </div>
          <h2 className="mt-4 font-display text-4xl font-bold tracking-tight uppercase md:text-5xl">{data.segment_name}</h2>
          <p className="mt-5 max-w-3xl text-lg leading-relaxed text-mute">{data.persona}</p>
          {data.motivations.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-2">
              {data.motivations.map((m) => (
                <span key={m} className="inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-sm">
                  <Lightbulb className="size-3.5 text-accent" /> {m}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      <div className="grid gap-5 md:grid-cols-2">
        {data.campaigns.map((c, i) => {
          const Icon = CHANNEL_ICONS[c.channel] ?? Megaphone
          return (
            <motion.div key={c.title} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 * i }}>
              <div className="group h-full rounded-3xl border border-line bg-surface p-6 transition-colors hover:border-accent/40">
                <div className="flex items-start justify-between gap-3">
                  <div className="grid size-12 place-items-center rounded-2xl bg-lime/10 transition group-hover:bg-lime/20">
                    <Icon className="size-5 text-accent" />
                  </div>
                  <span className="rounded-full bg-lime px-3 py-1 text-[10px] font-bold tracking-wider text-on-lime uppercase">
                    {c.channel}
                  </span>
                </div>
                <h3 className="mt-5 font-display text-2xl font-bold tracking-tight">{c.title}</h3>
                <p className="mt-2 text-sm">{c.offer}</p>
                <p className="mt-4 flex items-start gap-1.5 border-t border-line pt-4 text-xs text-mute">
                  <ArrowUpRight className="size-3.5 shrink-0 text-accent" />
                  {c.rationale}
                </p>
              </div>
            </motion.div>
          )
        })}
      </div>
      {data.watch_outs.length > 0 && (
        <Card title="Watch out for">
          <ul className="space-y-2 text-sm">
            {data.watch_outs.map((w) => (
              <li key={w} className="flex gap-2">
                <TriangleAlert className="mt-0.5 size-4 shrink-0 text-danger" />
                {w}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

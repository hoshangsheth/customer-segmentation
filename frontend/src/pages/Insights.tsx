import { Lightbulb, Mail, Megaphone, ShoppingBag, Sparkles, Store, TriangleAlert } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
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

  if (segments.loading) return <Loading />
  if (segments.error || !segments.data) return <ErrorBox message={segments.error ?? 'No data'} />
  const list = segments.data.segments
  const id = selected ?? list[0].segment_id

  return (
    <>
      <PageHeader
        title="AI insights"
        subtitle="Personas and campaign ideas written from each segment's computed statistics. The model only sees the numbers on the Segments page, and is told not to invent any."
      >
        {health.data && (
          <Badge tone={health.data.ai_available ? 'emerald' : 'slate'}>
            <Sparkles className="size-3" />
            {health.data.ai_available ? `AI on: ${health.data.ai_provider}` : 'AI off: set GEMINI_API_KEY'}
          </Badge>
        )}
      </PageHeader>
      <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <nav className="flex gap-2 overflow-x-auto lg:flex-col" aria-label="Segments">
          {list.map((s) => (
            <button
              key={s.segment_id}
              onClick={() => setSelected(s.segment_id)}
              className={`flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition-colors ${
                s.segment_id === id
                  ? 'border-indigo-300 bg-indigo-50 dark:border-indigo-500/50 dark:bg-indigo-500/10'
                  : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700'
              }`}
            >
              <SegmentDot color={segmentColor(s.segment_id)} />
              <span className="flex-1">{s.name}</span>
              <span className="text-xs text-slate-500 tabular-nums dark:text-slate-400">{pct(s.share, 0)}</span>
            </button>
          ))}
        </nav>
        <AnimatePresence mode="wait">
          <motion.div key={id} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }} transition={{ duration: 0.2 }}>
            <PersonaView segmentId={id} />
          </motion.div>
        </AnimatePresence>
      </div>
    </>
  )
}

function PersonaView({ segmentId }: { segmentId: number }) {
  const { data, error, loading } = useApi<Persona>(`persona-${segmentId}`, () => api.persona(segmentId))
  if (loading) return <Loading label="Writing persona" />
  if (error || !data) return <ErrorBox message={error ?? 'No data'} />

  return (
    <div className="space-y-6">
      <Card
        title={
          <span className="flex items-center gap-2">
            <SegmentDot color={segmentColor(data.segment_id)} />
            {data.segment_name}
          </span>
        }
        action={<Badge tone={data.source === 'llm' ? 'emerald' : 'slate'}>{data.source === 'llm' ? `AI: ${data.model}` : 'Rule-based'}</Badge>}
      >
        <p className="text-sm leading-relaxed">{data.persona}</p>
        {data.motivations.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {data.motivations.map((m) => (
              <Badge key={m} tone="indigo">
                <Lightbulb className="size-3" /> {m}
              </Badge>
            ))}
          </div>
        )}
      </Card>
      <div className="grid gap-4 md:grid-cols-2">
        {data.campaigns.map((c, i) => {
          const Icon = CHANNEL_ICONS[c.channel] ?? Megaphone
          return (
            <motion.div key={c.title} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 * i }}>
              <Card className="h-full">
                <div className="flex items-center gap-2">
                  <div className="grid size-8 place-items-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
                    <Icon className="size-4" />
                  </div>
                  <div>
                    <div className="font-semibold">{c.title}</div>
                    <div className="text-xs text-slate-500 capitalize dark:text-slate-400">{c.channel}</div>
                  </div>
                </div>
                <p className="mt-3 text-sm">{c.offer}</p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Why: {c.rationale}</p>
              </Card>
            </motion.div>
          )
        })}
      </div>
      {data.watch_outs.length > 0 && (
        <Card title="Watch out for">
          <ul className="space-y-1.5 text-sm">
            {data.watch_outs.map((w) => (
              <li key={w} className="flex gap-2">
                <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-500" />
                {w}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

import { ArrowUpRight, Loader2, Mail, Megaphone, ShoppingBag, Sparkles, Store, TriangleAlert } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { Badge, buttonOutline, ErrorBox, Reveal } from '../../components/ui'
import { api, ApiError } from '../../lib/api'
import type { Brief } from '../../lib/batchTypes'
import { pct } from '../../lib/format'

const CHANNEL_ICONS: Record<string, typeof Mail> = { email: Mail, web: ShoppingBag, catalog: Megaphone, store: Store }

export default function BriefCard({ jobId, share, cost, revenue }: { jobId: string; share: number; cost: number; revenue: number }) {
  const [brief, setBrief] = useState<Brief & { share: number }>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()

  const write = async () => {
    setBusy(true)
    setError(undefined)
    try {
      const b = await api.batch.brief(jobId, { top_share: share, cost_per_contact: cost, revenue_per_response: revenue })
      setBrief({ ...b, share })
    } catch (e) {
      setError((e as ApiError).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Reveal className="mt-5">
      <section className="relative overflow-hidden rounded-3xl border border-line bg-surface p-6">
        <div className="pointer-events-none absolute -top-24 -left-16 size-64 rounded-full" style={{ background: 'radial-gradient(circle, rgba(217,255,61,0.14), transparent 70%)' }} aria-hidden />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs tracking-[0.3em] text-accent uppercase">— Campaign brief</p>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight">
              {brief ? brief.headline : `A plan for contacting the top ${pct(share, 0)}`}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            {brief && <Badge tone={brief.source === 'llm' ? 'lime' : 'muted'}>{brief.source === 'llm' ? `AI: ${brief.model}` : 'Rule-based'}</Badge>}
            <button type="button" onClick={write} disabled={busy} className={buttonOutline}>
              {busy ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4 text-accent" />}
              {brief ? (brief.share === share ? 'Rewrite' : `Update for top ${pct(share, 0)}`) : 'Write campaign brief'}
            </button>
          </div>
        </div>
        {error && (
          <div className="relative mt-4">
            <ErrorBox message={error} />
          </div>
        )}
        {brief ? (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="relative mt-5 space-y-5">
            <p className="max-w-3xl leading-relaxed text-mute">{brief.summary}</p>
            <div className="grid gap-4 md:grid-cols-2">
              {brief.actions.map((a) => {
                const Icon = CHANNEL_ICONS[a.channel] ?? Megaphone
                return (
                  <div key={a.segment + a.message} className="rounded-2xl border border-line bg-night/40 p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="grid size-10 place-items-center rounded-xl bg-lime/10">
                        <Icon className="size-4 text-accent" />
                      </div>
                      <span className="rounded-full bg-lime px-3 py-1 text-[10px] font-bold tracking-wider text-on-lime uppercase">{a.channel}</span>
                    </div>
                    <h3 className="mt-3 font-display text-lg font-bold">{a.segment}</h3>
                    <p className="text-xs text-mute">{a.audience}</p>
                    <p className="mt-2 text-sm">{a.message}</p>
                    <p className="mt-3 flex gap-1.5 border-t border-line pt-3 text-xs text-mute">
                      <ArrowUpRight className="size-3.5 shrink-0 text-accent" />
                      {a.why}
                    </p>
                  </div>
                )
              })}
            </div>
            <p className="rounded-2xl bg-lime/10 px-4 py-3 text-sm">{brief.budget_note}</p>
            {brief.watch_outs.length > 0 && (
              <ul className="space-y-1.5 text-sm">
                {brief.watch_outs.map((w) => (
                  <li key={w} className="flex gap-2 text-mute">
                    <TriangleAlert className="mt-0.5 size-4 shrink-0 text-danger" />
                    {w}
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        ) : (
          <p className="relative mt-3 max-w-2xl text-sm text-mute">
            Turns this analysis into a short plan: which segments to contact, through which channel, with what message, and the
            expected budget. Uses AI when a Gemini key is configured, otherwise a rule-based playbook.
          </p>
        )}
      </section>
    </Reveal>
  )
}

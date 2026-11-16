import { ArrowRight, Boxes, Crosshair, Gauge, Layers, LineChart, Sparkles, Target, Users } from 'lucide-react'
import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { Page } from '../components/Layout'
import { buttonOutline, buttonPrimary, Card, ErrorBox, Eyebrow, Loading, Reveal, SegmentDot, Stat } from '../components/ui'
import { api } from '../lib/api'
import { int, money, numberWord, pct, segmentColor, times } from '../lib/format'
import type { Lift, Overview as OverviewData } from '../lib/types'
import { useApi } from '../lib/useApi'

const EASE = [0.22, 1, 0.36, 1] as const

export default function Overview() {
  const { data, error, loading } = useApi('overview', api.overview)
  const lift = useApi('lift', api.lift)
  if (loading)
    return (
      <Page>
        <Loading />
      </Page>
    )
  if (error || !data)
    return (
      <Page>
        <ErrorBox message={error ?? 'No data'} />
      </Page>
    )

  return (
    <Page>
      <Hero data={data} />
      {lift.data && <StrategyCard lift={lift.data} />}
      <Segments data={data} />
      <Pipeline data={data} />
    </Page>
  )
}

function Hero({ data }: { data: OverviewData }) {
  return (
    <section className="relative">
      <div className="pointer-events-none absolute -top-24 left-1/2 h-64 w-[70%] -translate-x-1/2 rounded-full" style={{ background: 'radial-gradient(circle, rgba(217,255,61,0.14), transparent 70%)' }} aria-hidden />
      <div className="relative grid gap-10 lg:grid-cols-[1.4fr_1fr] lg:items-end">
        <div>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-4 text-xs tracking-[0.3em] text-accent uppercase"
          >
            — Overview
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE }}
            className="font-display leading-[0.95] font-bold tracking-tight"
            style={{ fontSize: 'clamp(2.5rem, 5vw, 4.75rem)' }}
          >
            <span className="text-accent">Target</span> the customers
            <br />
            who will <span className="font-normal text-accent italic">respond.</span>
          </motion.h1>
        </div>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="space-y-5 lg:pb-3"
        >
          <p className="leading-relaxed text-mute">
            {int(data.customers)} customers of a grocery and wine retailer, grouped into {data.n_segments} behavioural
            segments, with a model that predicts who accepts the next campaign. Model and lift numbers are measured on
            customers the model did not train on.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/targeting" className={buttonPrimary}>
              See who to target <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <Link to="/analyze" className={buttonOutline}>
              Analyze your customers
            </Link>
          </div>
        </motion.div>
      </div>

      <div className="relative mt-12 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <Stat icon={Users} label="Customers" value={int(data.customers)} hint="after cleaning" delay={0.2} />
        <Stat icon={Target} label="Response rate" value={pct(data.response_rate)} hint="last campaign, everyone" delay={0.26} />
        <Stat icon={Crosshair} label="Top 10% lift" value={times(data.top_decile_lift)} hint="model-ranked, vs everyone" delay={0.32} />
        <Stat icon={Layers} label="Best segment lift" value={times(data.top_segment_lift)} hint={data.top_segment_name} delay={0.38} />
        <Stat
          icon={Gauge}
          label="ROC AUC"
          value={data.roc_auc.toFixed(3)}
          hint={`PR AUC ${data.pr_auc.toFixed(3)}`}
          delay={0.44}
          className="col-span-2 md:col-span-1"
        />
      </div>
    </section>
  )
}

function StrategyCard({ lift }: { lift: Lift }) {
  const everyone = lift.curve[lift.curve.length - 1]
  const best = lift.best_profit_point
  const seg = lift.segment_targeting.rows[0]
  const rows = [
    { label: 'Contact everyone', share: 1, rate: lift.base_rate, lift: 1, profit: everyone.profit, note: 'measured on all customers' },
    {
      label: `Model top ${pct(best.share_targeted, 0)}`,
      share: best.share_targeted,
      rate: best.response_rate,
      lift: best.lift,
      profit: best.profit,
      note: 'out-of-fold scores',
    },
    {
      label: `Segment: ${seg.names.join(' + ')}`,
      share: seg.share_targeted,
      rate: seg.response_rate,
      lift: seg.lift,
      profit: null,
      note: 'ranked on train, measured on test',
    },
  ]
  return (
    <Reveal className="mt-16">
      <Card
        title="What targeting is worth"
        subtitle={`Cost ${money(lift.cost_per_contact)} per contact and revenue ${money(lift.revenue_per_response)} per response, from the dataset.`}
        action={
          <Link to="/targeting" className="inline-flex items-center gap-1 text-sm font-semibold text-accent hover:underline">
            Budget planner <ArrowRight className="size-4" />
          </Link>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-sm">
            <thead>
              <tr className="text-left text-[10px] tracking-widest text-mute uppercase">
                <th className="py-2 font-medium">Strategy</th>
                <th className="py-2 pl-4 text-right font-medium">Contacted</th>
                <th className="py-2 pl-4 text-right font-medium">Response rate</th>
                <th className="py-2 pl-4 text-right font-medium">Lift</th>
                <th className="py-2 pl-4 text-right font-medium">Profit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.label}>
                  <td className="py-3">
                    <div className="font-medium">{r.label}</div>
                    <div className="text-xs text-mute">{r.note}</div>
                  </td>
                  <td className="py-3 pl-4 text-right tabular-nums">{pct(r.share, 0)}</td>
                  <td className="py-3 pl-4 text-right tabular-nums">{pct(r.rate)}</td>
                  <td className={`py-3 pl-4 text-right font-display font-bold tabular-nums ${r.lift > 1 ? 'text-accent' : ''}`}>
                    {times(r.lift)}
                  </td>
                  <td
                    className={`py-3 pl-4 text-right font-display font-bold tabular-nums ${
                      r.profit === null ? 'text-mute' : r.profit < 0 ? 'text-danger' : 'text-accent'
                    }`}
                  >
                    {r.profit === null ? 'n/a' : money(r.profit)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </Reveal>
  )
}

function Segments({ data }: { data: OverviewData }) {
  const segments = [...data.segments].sort((a, b) => b.response_rate - a.response_rate)
  const maxRate = Math.max(...segments.map((s) => s.response_rate))
  return (
    <section className="mt-20">
      <Reveal className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <Eyebrow>Segments</Eyebrow>
          <h2 className="font-display text-4xl font-bold tracking-tight md:text-5xl">
            {numberWord(data.n_segments)} segments, <span className="font-normal text-accent italic">by response rate.</span>
          </h2>
        </div>
        <p className="max-w-md text-sm text-mute">
          Campaign history is left out of the clustering, so each segment's response rate is an honest check.
        </p>
      </Reveal>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {segments.map((s, i) => {
          const color = segmentColor(s.segment_id)
          return (
            <Reveal key={s.segment_id} delay={i * 0.08} className="h-full">
              <Link
                to={`/segments?id=${s.segment_id}`}
                className="group relative block h-full overflow-hidden rounded-3xl border border-line bg-surface p-6 transition-colors hover:border-accent/40"
              >
                <div
                  className="pointer-events-none absolute -top-20 -right-16 size-48 rounded-full transition-opacity group-hover:opacity-100 md:opacity-60"
                  style={{ background: `radial-gradient(circle, ${color}40, transparent 70%)` }}
                  aria-hidden
                />
                <div className="relative">
                  <div className="flex items-center gap-2">
                    <SegmentDot color={color} />
                    <h3 className="font-display text-2xl font-bold tracking-tight">{s.name}</h3>
                  </div>
                  <p className="mt-2 text-sm text-mute">{s.tagline}</p>
                  <dl className="mt-6 grid grid-cols-3 gap-2">
                    <div>
                      <dt className="text-[10px] tracking-widest text-mute uppercase">Customers</dt>
                      <dd className="font-display text-lg font-bold tabular-nums">
                        {int(s.size)} <span className="text-xs font-normal text-mute">{pct(s.share, 0)}</span>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] tracking-widest text-mute uppercase">Avg spend</dt>
                      <dd className="font-display text-lg font-bold tabular-nums">{money(s.avg_spend)}</dd>
                    </div>
                    <div>
                      <dt className="text-[10px] tracking-widest text-mute uppercase">Income</dt>
                      <dd className="font-display text-lg font-bold tabular-nums">{money(s.avg_income)}</dd>
                    </div>
                  </dl>
                  <div className="mt-6">
                    <div className="mb-2 flex justify-between text-xs">
                      <span className="text-mute">Response rate</span>
                      <span className="font-semibold tabular-nums">
                        {pct(s.response_rate)} ({times(s.response_rate / data.response_rate, 1)})
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-raised">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ backgroundColor: color }}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${(s.response_rate / maxRate) * 100}%` }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 + 0.05 * i, duration: 0.7, ease: 'easeOut' }}
                      />
                    </div>
                  </div>
                  <div className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-accent">
                    Open profile <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                  </div>
                </div>
              </Link>
            </Reveal>
          )
        })}
      </div>
    </section>
  )
}

function Pipeline({ data }: { data: OverviewData }) {
  const steps = [
    {
      icon: Boxes,
      title: 'Segment',
      text: `K-Means on spend, frequency, recency, channel and household features; ${data.n_segments} segments chosen by silhouette score.`,
      to: '/segments',
    },
    {
      icon: Crosshair,
      title: 'Predict',
      text: `XGBoost predicts who accepts the next offer: holdout ROC AUC ${data.roc_auc.toFixed(3)}, PR AUC ${data.pr_auc.toFixed(3)}.`,
      to: '/targeting',
    },
    {
      icon: LineChart,
      title: 'Measure lift',
      text: `Out-of-fold scores rank every customer; the top 10% respond at ${times(data.top_decile_lift, 1)} the average rate.`,
      to: '/targeting',
    },
    {
      icon: Sparkles,
      title: 'Explain',
      text: 'SHAP shows why each customer scored as they did; an optional LLM writes personas and campaign ideas.',
      to: '/insights',
    },
  ]
  return (
    <section className="mt-20">
      <Reveal className="mb-8">
        <Eyebrow>How it works</Eyebrow>
        <h2 className="font-display text-4xl font-bold tracking-tight md:text-5xl">
          From raw data <span className="font-normal text-accent italic">to a target list.</span>
        </h2>
      </Reveal>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {steps.map((s, i) => (
          <Reveal key={s.title} delay={i * 0.06} className="h-full">
            <Link
              to={s.to}
              className="group block h-full rounded-3xl border border-line bg-surface p-6 transition-colors hover:border-accent/40"
            >
              <div className="mb-5 flex items-center justify-between">
                <div className="grid size-12 place-items-center rounded-2xl bg-lime/10 transition group-hover:bg-lime/20">
                  <s.icon className="size-5 text-accent" />
                </div>
                <span className="font-display text-3xl font-bold text-ink/15">0{i + 1}</span>
              </div>
              <h3 className="font-display text-xl font-bold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mute">{s.text}</p>
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  )
}

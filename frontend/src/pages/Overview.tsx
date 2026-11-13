import { ArrowRight } from 'lucide-react'
import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { Card, ErrorBox, Kpi, Loading, PageHeader, SegmentDot } from '../components/ui'
import { api } from '../lib/api'
import { int, money, pct, segmentColor, times } from '../lib/format'
import { useApi } from '../lib/useApi'

export default function Overview() {
  const { data, error, loading } = useApi('overview', api.overview)
  if (loading) return <Loading />
  if (error || !data) return <ErrorBox message={error ?? 'No data'} />

  const segments = [...data.segments].sort((a, b) => b.response_rate - a.response_rate)
  const maxRate = Math.max(...segments.map((s) => s.response_rate))

  return (
    <>
      <PageHeader
        title="Who to target, and what it is worth"
        subtitle={
          <>
            {int(data.customers)} customers of a grocery and wine retailer, grouped into {data.n_segments} behavioural
            segments, with a model that predicts who accepts the next campaign. Model and lift numbers are measured
            on customers the model did not train on.
          </>
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <Kpi label="Customers" value={int(data.customers)} hint="after cleaning" delay={0} />
        <Kpi label="Response rate" value={pct(data.response_rate)} hint="last campaign, everyone" delay={0.05} />
        <Kpi label="Top 10% lift" value={times(data.top_decile_lift)} hint="model-ranked, vs everyone" delay={0.1} />
        <Kpi
          label="Best segment lift"
          value={times(data.top_segment_lift)}
          hint={data.top_segment_name}
          delay={0.15}
        />
        <Kpi label="ROC AUC" value={data.roc_auc.toFixed(3)} hint={`PR AUC ${data.pr_auc.toFixed(3)}`} delay={0.2} />
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.25 }}
        className="mt-6 rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-5 dark:border-indigo-500/30 dark:from-indigo-500/10 dark:to-slate-900"
      >
        <div className="text-sm text-indigo-900 dark:text-indigo-200">
          Contacting the model's top {pct(data.best_profit_share, 0)} of customers maximises campaign profit at{' '}
          <span className="font-semibold">{money(data.best_profit)}</span>, using the dataset's own cost per contact and
          revenue per response.
        </div>
        <Link
          to="/targeting"
          className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline dark:text-indigo-300"
        >
          See the lift curve and budget trade-off <ArrowRight className="size-4" />
        </Link>
      </motion.div>

      <h2 className="mt-10 mb-4 text-lg font-semibold">Segments, by response rate</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {segments.map((s, i) => (
          <motion.div
            key={s.segment_id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * i + 0.2 }}
            whileHover={{ y: -3 }}
          >
            <Link to={`/segments?id=${s.segment_id}`} className="block h-full">
              <Card className="h-full transition-shadow hover:shadow-md">
                <div className="flex items-center gap-2">
                  <SegmentDot color={segmentColor(s.segment_id)} />
                  <h3 className="font-semibold">{s.name}</h3>
                </div>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{s.tagline}</p>
                <dl className="mt-4 grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <dt className="text-xs text-slate-500 dark:text-slate-400">Customers</dt>
                    <dd className="font-medium tabular-nums">
                      {int(s.size)} <span className="text-slate-400">({pct(s.share, 0)})</span>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500 dark:text-slate-400">Avg spend</dt>
                    <dd className="font-medium tabular-nums">{money(s.avg_spend)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-500 dark:text-slate-400">Income</dt>
                    <dd className="font-medium tabular-nums">{money(s.avg_income)}</dd>
                  </div>
                </dl>
                <div className="mt-4">
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-slate-500 dark:text-slate-400">Response rate</span>
                    <span className="font-medium tabular-nums">
                      {pct(s.response_rate)} ({times(s.response_rate / data.response_rate, 1)})
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <motion.div
                      className="h-full rounded-full"
                      style={{ backgroundColor: segmentColor(s.segment_id) }}
                      initial={{ width: 0 }}
                      animate={{ width: `${(s.response_rate / maxRate) * 100}%` }}
                      transition={{ delay: 0.3 + 0.05 * i, duration: 0.6, ease: 'easeOut' }}
                    />
                  </div>
                </div>
              </Card>
            </Link>
          </motion.div>
        ))}
      </div>
      <p className="mt-6 text-xs text-slate-500 dark:text-slate-400">
        Model {data.model_version}, trained {data.trained_at.replace('T', ' ')}. Data: Kaggle "Customer Personality
        Analysis" (public). Recreated on public data.
      </p>
    </>
  )
}

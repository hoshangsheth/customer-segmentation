import { ArrowRight, CheckCircle2, Download, FileSpreadsheet, Info, Loader2, ShieldCheck, Sparkles, Upload, X, XCircle } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'
import { buttonOutline, buttonPrimary, Card, ErrorBox, PageHeader } from '../../components/ui'
import { api, ApiError } from '../../lib/api'
import type { UploadOut } from '../../lib/batchTypes'

const ACCEPT = '.csv,.tsv,.txt,.xlsx,.xlsm,.xls'

const NEEDS = [
  'Customer ID',
  'Household income',
  'Birth year or age',
  'Customer since (date)',
  'Days since last purchase, or last purchase date',
  'Spend by category (at least one)',
  'Purchases by channel (at least one)',
]
const HELPS = [
  'Education, marital status, children and teenagers at home, website visits, complaints',
  'Campaign history: which of your last five campaigns each customer accepted. This switches to the more accurate full model.',
  'Who responded to your latest campaign, to measure how well the ranking works on your own customers.',
]

export default function UploadStep({ onUploaded }: { onUploaded: (u: UploadOut) => void }) {
  const [customers, setCustomers] = useState<File>()
  const [history, setHistory] = useState<File>()
  const [busy, setBusy] = useState<'upload' | 'sample'>()
  const [error, setError] = useState<string>()

  const run = async (kind: 'upload' | 'sample') => {
    setBusy(kind)
    setError(undefined)
    try {
      onUploaded(kind === 'sample' ? await api.batch.sample() : await api.batch.upload(customers!, history))
    } catch (e) {
      setError((e as ApiError).message)
    } finally {
      setBusy(undefined)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Analyze your customers"
        title="Upload your customers,"
        accent="get a target list."
        subtitle="Every customer is segmented and scored for how likely they are to respond to your next campaign, with the reasons behind each score. Export the list you want to contact."
      />
      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-5">
          <DropZone
            title="Customer data"
            badge="Required"
            hint="One row per customer: profile, spend and purchases. CSV or Excel."
            file={customers}
            onFile={setCustomers}
          />
          <DropZone
            title="Campaign history"
            badge="Optional"
            hint="Earlier campaign responses, joined on customer ID. Skip if this is already in the customer file."
            file={history}
            onFile={setHistory}
          />
          {error && <ErrorBox message={error} />}
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" disabled={!customers || !!busy} onClick={() => run('upload')} className={buttonPrimary}>
              Continue to column mapping
              {busy === 'upload' ? <Loader2 className="size-4 animate-spin" /> : <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />}
            </button>
            <button type="button" disabled={!!busy} onClick={() => run('sample')} className={buttonOutline}>
              {busy === 'sample' ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4 text-accent" />}
              Try with sample data
            </button>
            <a href={api.batch.templateUrl()} className="inline-flex items-center gap-1.5 text-sm font-semibold text-accent hover:underline">
              <Download className="size-4" /> Template CSV
            </a>
          </div>
        </div>

        <Card title="What your file needs">
          <ul className="space-y-2 text-sm">
            {NEEDS.map((n) => (
              <li key={n} className="flex gap-2.5">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-lime" />
                {n}
              </li>
            ))}
          </ul>
          <p className="mt-5 text-[10px] tracking-widest text-mute uppercase">Improves results</p>
          <ul className="mt-2 space-y-2 text-sm text-mute">
            {HELPS.map((n) => (
              <li key={n} className="flex gap-2.5">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-line" />
                {n}
              </li>
            ))}
          </ul>
          <p className="mt-5 text-sm text-mute">
            Column names do not need to match: you confirm the mapping in the next step.
          </p>
          <div className="mt-5 flex gap-3 rounded-2xl bg-raised p-4 text-xs text-mute">
            <ShieldCheck className="size-4 shrink-0 text-accent" />
            Uploads are not saved. The data is held in memory on this server while you work and discarded after an hour of
            inactivity.
          </div>
        </Card>
      </div>
      <DataDisclaimer />
    </>
  )
}

const WORKS = [
  'Business-to-consumer retail customers: grocery, food and drink, wine, specialty or general retail',
  'One row per individual customer or household, with about two years of purchase history',
  'Spend broken down by product category and purchases counted by channel (web, catalog, store, discount)',
  'Response to direct-marketing offers such as email, catalog or in-store promotions',
]
const LIMITS = [
  'Business-to-business accounts, subscriptions, banking, insurance, telecom or other non-retail data',
  'Transaction-level logs: summarise to one row per customer first',
  'Very different markets or currencies: the model learned from one retailer, so scores are a guide, and the data quality panel flags values outside what it has seen',
  'Decisions about credit, employment, housing or anything with legal effect: this tool ranks marketing contacts only',
]

function DataDisclaimer() {
  return (
    <section className="mt-5 rounded-3xl border border-line bg-surface p-6">
      <div className="flex items-start gap-3">
        <Info className="mt-0.5 size-5 shrink-0 text-accent" />
        <div>
          <h2 className="font-display text-xl font-bold">Which data works with this app</h2>
          <p className="mt-1 max-w-3xl text-sm text-mute">
            The models were trained on 2,236 customers of one grocery and wine retailer (public Kaggle data). They work best on
            data that looks like that. Results on other data are estimates, not guarantees; check them against a real campaign
            before relying on them.
          </p>
        </div>
      </div>
      <div className="mt-5 grid gap-6 md:grid-cols-2">
        <div>
          <p className="mb-2 text-[10px] tracking-widest text-accent uppercase">Works well</p>
          <ul className="space-y-2 text-sm">
            {WORKS.map((w) => (
              <li key={w} className="flex gap-2.5">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-accent" />
                {w}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-2 text-[10px] tracking-widest text-danger uppercase">Not suitable or use with care</p>
          <ul className="space-y-2 text-sm">
            {LIMITS.map((w) => (
              <li key={w} className="flex gap-2.5 text-mute">
                <XCircle className="mt-0.5 size-4 shrink-0 text-danger" />
                {w}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

function DropZone({
  title,
  badge,
  hint,
  file,
  onFile,
}: {
  title: string
  badge: string
  hint: string
  file?: File
  onFile: (f?: File) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setOver(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }
  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      className={`rounded-3xl border-2 border-dashed p-6 transition-colors ${
        over ? 'border-lime bg-lime/10' : file ? 'border-accent/40 bg-surface' : 'border-line bg-surface hover:border-accent/40'
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-12 place-items-center rounded-2xl bg-lime/10">
            {file ? <FileSpreadsheet className="size-5 text-accent" /> : <Upload className="size-5 text-accent" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display text-xl font-bold">{title}</span>
              <span className="rounded-full bg-raised px-2 py-0.5 text-[10px] font-bold tracking-wider text-mute uppercase">{badge}</span>
            </div>
            <p className="text-sm text-mute">{file ? `${file.name} · ${(file.size / 1024).toFixed(0)} KB` : hint}</p>
          </div>
        </div>
        {file ? (
          <button
            type="button"
            onClick={() => onFile(undefined)}
            aria-label={`Remove ${file.name}`}
            className="grid size-9 place-items-center rounded-full border border-line hover:border-danger/50 hover:text-danger"
          >
            <X className="size-4" />
          </button>
        ) : (
          <button type="button" onClick={() => input.current?.click()} className="rounded-full border border-line px-4 py-2 text-sm font-semibold hover:border-accent/40">
            Choose file
          </button>
        )}
      </div>
      {!file && <p className="mt-3 text-xs text-mute">or drag and drop it here</p>}
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          onFile(e.target.files?.[0])
          e.target.value = ''
        }}
      />
    </div>
  )
}

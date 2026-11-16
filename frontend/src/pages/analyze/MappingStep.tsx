import { ArrowLeft, ArrowRight, CheckCircle2, CircleAlert, History, Loader2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { buttonOutline, buttonPrimary, Card, ErrorBox, Loading, PageHeader } from '../../components/ui'
import { api, ApiError } from '../../lib/api'
import type { ColumnRef, DateOrder, FieldSpec, FieldsOut, FileRole, Summary, UploadOut } from '../../lib/batchTypes'
import { int } from '../../lib/format'
import { useApi } from '../../lib/useApi'

const SEP = '::'
const encode = (r: ColumnRef | null | undefined) => (r ? `${r.file}${SEP}${r.column}` : '')
const decode = (v: string): ColumnRef | null => {
  if (!v) return null
  const [file, ...rest] = v.split(SEP)
  return { file: file as FileRole, column: rest.join(SEP) }
}

export default function MappingStep({
  upload,
  onBack,
  onDone,
}: {
  upload: UploadOut
  onBack: () => void
  onDone: (s: Summary) => void
}) {
  const fields = useApi('batch-fields', api.batch.fields)
  if (fields.loading) return <Loading />
  if (fields.error || !fields.data) return <ErrorBox message={fields.error ?? 'No data'} />
  return <MappingForm upload={upload} spec={fields.data} onBack={onBack} onDone={onDone} />
}

function MappingForm({
  upload,
  spec,
  onBack,
  onDone,
}: {
  upload: UploadOut
  spec: FieldsOut
  onBack: () => void
  onDone: (s: Summary) => void
}) {
  const [mapping, setMapping] = useState<Record<string, ColumnRef | null>>(() => ({ ...upload.suggestion.mapping }))
  const [historyId, setHistoryId] = useState(upload.suggestion.history_id_column ?? '')
  const [dateOrder, setDateOrder] = useState<DateOrder>('auto')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError>()

  const files = Object.fromEntries(upload.files.map((f) => [f.role, f]))
  const hasHistoryFile = !!files.history
  const mapped = useMemo(() => new Set(Object.entries(mapping).filter(([, v]) => v).map(([k]) => k)), [mapping])

  const groups = useMemo(() => {
    const out = new Map<string, FieldSpec[]>()
    for (const f of spec.fields) out.set(f.group, [...(out.get(f.group) ?? []), f])
    return [...out.entries()]
  }, [spec])

  const problems = [
    ...spec.fields.filter((f) => f.required && !mapped.has(f.key)).map((f) => `Map ${f.label}.`),
    ...spec.required_groups.filter((g) => !g.keys.some((k) => mapped.has(k))).map((g) => g.message),
  ]
  const usesHistoryFile = Object.values(mapping).some((v) => v?.file === 'history')
  if (usesHistoryFile && !historyId) problems.push('Choose the customer ID column of the campaign history file.')
  const usesHistory = spec.fields.some((f) => f.history && mapped.has(f.key))
  const optionalOneOf = new Set(spec.required_groups.flatMap((g) => g.keys))

  const submit = async () => {
    setBusy(true)
    setError(undefined)
    try {
      const clean = Object.fromEntries(Object.entries(mapping).filter(([, v]) => v)) as Record<string, ColumnRef>
      onDone(await api.batch.analyze(upload.job_id, { mapping: clean, history_id_column: historyId || null, date_order: dateOrder }))
    } catch (e) {
      setError(e as ApiError)
    } finally {
      setBusy(false)
    }
  }

  const sampleValues = (ref: ColumnRef | null | undefined) => {
    if (!ref) return ''
    const vals = files[ref.file]?.preview.map((r) => r[ref.column]).filter((v) => v !== '' && v !== undefined)
    return vals?.slice(0, 3).join(', ') ?? ''
  }

  return (
    <>
      <PageHeader
        eyebrow="Map columns"
        title="Tell us what"
        accent="each column means."
        subtitle="Columns were matched automatically by name. Check each one, fix any that are wrong, and leave fields you do not have as 'Not in my file'."
      >
        <div className="space-y-2">
          {upload.files.map((f) => (
            <div key={f.role} className="flex items-center justify-between gap-4 rounded-2xl border border-line bg-surface px-4 py-3 text-sm">
              <span className="truncate font-medium">{f.filename}</span>
              <span className="shrink-0 text-xs text-mute">
                {int(f.rows)} rows · {f.columns.length} columns
              </span>
            </div>
          ))}
          {upload.sample && (
            <p className="text-xs text-mute">Sample data: synthetic customers generated for this demo, with a few deliberately broken rows.</p>
          )}
        </div>
      </PageHeader>

      <div className="grid gap-5 xl:grid-cols-[1fr_22rem] xl:items-start">
        <div className="space-y-5">
          {groups.map(([group, list]) => (
            <Card key={group} title={group} subtitle={group === 'Campaign history' ? 'Optional, but the strongest signal for who will respond.' : undefined}>
              <div className="divide-y divide-line">
                {list.map((f) => {
                  const ref = mapping[f.key]
                  return (
                    <div key={f.key} className="grid gap-2 py-3 sm:grid-cols-[1fr_16rem] sm:items-center">
                      <div>
                        <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                          {f.label}
                          {f.required && <span className="rounded-full bg-lime px-2 py-0.5 text-[9px] font-bold tracking-wider text-on-lime uppercase">Required</span>}
                          {!f.required && optionalOneOf.has(f.key) && (
                            <span className="rounded-full border border-accent/40 px-2 py-0.5 text-[9px] font-bold tracking-wider text-accent uppercase">One of</span>
                          )}
                        </div>
                        <p className="text-xs text-mute">{f.description}</p>
                        {ref && <p className="mt-1 truncate text-xs text-accent">e.g. {sampleValues(ref) || 'empty in the first rows'}</p>}
                      </div>
                      <select
                        aria-label={f.label}
                        value={encode(ref)}
                        onChange={(e) => setMapping((m) => ({ ...m, [f.key]: decode(e.target.value) }))}
                        className={`w-full rounded-2xl border bg-night px-3 py-2.5 text-sm outline-none focus:border-accent ${ref ? 'border-accent/40' : 'border-line text-mute'}`}
                      >
                        <option value="">Not in my file</option>
                        {upload.files.map((file) => (
                          <optgroup key={file.role} label={`${file.role === 'customers' ? 'Customer file' : 'History file'}: ${file.filename}`}>
                            {file.columns.map((c) => (
                              <option key={c} value={`${file.role}${SEP}${c}`}>
                                {c}
                              </option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                    </div>
                  )
                })}
              </div>
            </Card>
          ))}
        </div>

        <div className="space-y-5 xl:sticky xl:top-28">
          <Card title="Ready to analyze?">
            {problems.length ? (
              <ul className="space-y-2 text-sm">
                {problems.map((p) => (
                  <li key={p} className="flex gap-2">
                    <CircleAlert className="mt-0.5 size-4 shrink-0 text-danger" />
                    {p}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="flex gap-2 text-sm">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-accent" /> Everything the model needs is mapped.
              </p>
            )}
            <div className="mt-5 flex gap-3 rounded-2xl bg-raised p-4 text-xs">
              <History className="size-4 shrink-0 text-accent" />
              <span className="text-mute">
                {usesHistory
                  ? 'Campaign history is mapped, so the full model is used.'
                  : 'No campaign history mapped: the behaviour-only model is used. It is less accurate but never treats missing history as refused offers.'}
              </span>
            </div>
            {hasHistoryFile && (
              <label className="mt-5 block text-[10px] tracking-widest text-mute uppercase">
                Customer ID column in the history file
                <select
                  value={historyId}
                  onChange={(e) => setHistoryId(e.target.value)}
                  className="mt-1.5 w-full rounded-2xl border border-line bg-night px-3 py-2.5 text-sm tracking-normal text-ink normal-case outline-none focus:border-accent"
                >
                  <option value="">Choose a column</option>
                  {files.history.columns.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
            )}
            <label className="mt-4 block text-[10px] tracking-widest text-mute uppercase">
              Date format
              <select
                value={dateOrder}
                onChange={(e) => setDateOrder(e.target.value as DateOrder)}
                className="mt-1.5 w-full rounded-2xl border border-line bg-night px-3 py-2.5 text-sm tracking-normal text-ink normal-case outline-none focus:border-accent"
              >
                <option value="auto">Detect automatically</option>
                <option value="dmy">Day first (31/12/2024)</option>
                <option value="mdy">Month first (12/31/2024)</option>
                <option value="ymd">Year first (2024-12-31)</option>
              </select>
            </label>
            {error && (
              <div className="mt-4">
                <ErrorBox message={error.problems.length ? error.problems.join(' ') : error.message} />
              </div>
            )}
            <div className="mt-5 flex flex-wrap gap-3">
              <button type="button" onClick={submit} disabled={problems.length > 0 || busy} className={buttonPrimary}>
                Analyze {int(files.customers.rows)} customers
                {busy ? <Loader2 className="size-4 animate-spin" /> : <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />}
              </button>
              <button type="button" onClick={onBack} className={buttonOutline}>
                <ArrowLeft className="size-4" /> Back
              </button>
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}

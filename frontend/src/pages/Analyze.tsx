import { Check } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Page } from '../components/Layout'
import { ErrorBox, Loading } from '../components/ui'
import { api, ApiError } from '../lib/api'
import type { Summary, UploadOut } from '../lib/batchTypes'
import MappingStep from './analyze/MappingStep'
import Results from './analyze/Results'
import UploadStep from './analyze/UploadStep'

const STEPS = ['Upload', 'Map columns', 'Results']

export default function Analyze() {
  const [params, setParams] = useSearchParams()
  const jobParam = params.get('job')
  const [upload, setUpload] = useState<UploadOut>()
  const [summary, setSummary] = useState<Summary>()
  const [restore, setRestore] = useState<{ job: string; error?: string }>()

  // Reload results after a page refresh: the job id lives in the URL; uploads expire on the server.
  useEffect(() => {
    if (!jobParam || summary?.job_id === jobParam) return
    let alive = true
    api.batch
      .summary(jobParam)
      .then((s) => alive && setSummary(s))
      .catch((e: ApiError) => alive && setRestore({ job: jobParam, error: e.message }))
    return () => {
      alive = false
    }
  }, [jobParam, summary?.job_id])

  const reset = () => {
    setUpload(undefined)
    setSummary(undefined)
    setRestore(undefined)
    setParams({}, { replace: true })
  }

  const step = summary ? 2 : upload ? 1 : 0
  const restoring = jobParam && !summary && restore?.job !== jobParam

  return (
    <Page>
      <ol className="mb-10 flex flex-wrap items-center gap-2 text-sm" aria-label="Progress">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span
              className={`grid size-7 place-items-center rounded-full text-xs font-bold ${
                i < step ? 'bg-lime/20 text-accent' : i === step ? 'bg-lime text-on-lime' : 'border border-line text-mute'
              }`}
            >
              {i < step ? <Check className="size-3.5" /> : i + 1}
            </span>
            <span className={i === step ? 'font-semibold' : 'text-mute'}>{label}</span>
            {i < STEPS.length - 1 && <span className="mx-2 h-px w-8 bg-line" />}
          </li>
        ))}
      </ol>

      {restoring ? (
        <Loading label="Loading your analysis" />
      ) : summary ? (
        <Results summary={summary} onReset={reset} />
      ) : upload ? (
        <MappingStep
          upload={upload}
          onBack={() => setUpload(undefined)}
          onDone={(s) => {
            setSummary(s)
            setParams({ job: s.job_id }, { replace: true })
          }}
        />
      ) : (
        <>
          {restore?.error && (
            <div className="mb-6">
              <ErrorBox message={`${restore.error} Start a new analysis below.`} />
            </div>
          )}
          <UploadStep onUploaded={setUpload} />
        </>
      )}
    </Page>
  )
}

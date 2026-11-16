import type { ReactNode } from 'react'

interface TooltipRow {
  label: string
  value: ReactNode
  color?: string
}

export function TooltipBox({ title, rows }: { title?: ReactNode; rows: TooltipRow[] }) {
  return (
    <div className="rounded-2xl border border-line bg-surface px-3.5 py-2.5 text-xs shadow-xl">
      {title && <div className="mb-1 font-display text-sm font-bold">{title}</div>}
      {rows.map((r) => (
        <div key={r.label} className="flex items-center justify-between gap-5">
          <span className="flex items-center gap-1.5 text-mute">
            {r.color && <span className="size-2 rounded-full" style={{ backgroundColor: r.color }} />}
            {r.label}
          </span>
          <span className="font-semibold tabular-nums">{r.value}</span>
        </div>
      ))}
    </div>
  )
}

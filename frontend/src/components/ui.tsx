import { AlertTriangle, Loader2, type LucideIcon } from 'lucide-react'
import { motion } from 'motion/react'
import type { ReactNode } from 'react'

const EASE = [0.22, 1, 0.36, 1] as const

/** Small uppercase label in the accent colour, like "— Segments". */
export function Eyebrow({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <p className={`mb-4 text-xs tracking-[0.3em] text-accent uppercase ${className}`}>— {children}</p>
}

/** Big display heading; `accent` is set on its own line in italic accent type. */
export function DisplayTitle({
  children,
  accent,
  as: Tag = 'h2',
  size = 'section',
  className = '',
}: {
  children: ReactNode
  accent?: ReactNode
  as?: 'h1' | 'h2'
  size?: 'hero' | 'page' | 'section'
  className?: string
}) {
  const fontSize = {
    hero: 'clamp(2.75rem, 7.5vw, 7rem)',
    page: 'clamp(2.25rem, 5.5vw, 4.5rem)',
    section: 'clamp(2rem, 4.5vw, 3.75rem)',
  }[size]
  return (
    <Tag className={`font-display leading-[1] font-bold tracking-tight text-ink ${className}`} style={{ fontSize }}>
      {children}
      {accent && (
        <>
          <br />
          <span className="font-normal text-accent italic">{accent}</span>
        </>
      )}
    </Tag>
  )
}

export function PageHeader({
  eyebrow,
  title,
  accent,
  subtitle,
  children,
}: {
  eyebrow: string
  title: ReactNode
  accent?: ReactNode
  subtitle?: ReactNode
  children?: ReactNode
}) {
  return (
    <motion.header
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: EASE }}
      className="mb-12 flex flex-col gap-6 md:mb-16 lg:flex-row lg:items-end lg:justify-between"
    >
      <div className="max-w-4xl">
        <Eyebrow>{eyebrow}</Eyebrow>
        <DisplayTitle as="h1" size="page" accent={accent}>
          {title}
        </DisplayTitle>
      </div>
      {(subtitle || children) && (
        <div className="max-w-md space-y-4 lg:pb-2">
          {subtitle && <p className="leading-relaxed text-mute">{subtitle}</p>}
          {children}
        </div>
      )}
    </motion.header>
  )
}

/** Fades a block up as it scrolls into view. */
export function Reveal({ children, delay = 0, className = '' }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.6, delay, ease: EASE }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

export function Card({
  title,
  subtitle,
  action,
  children,
  className = '',
  interactive = false,
}: {
  title?: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
  interactive?: boolean
}) {
  return (
    <section
      className={`rounded-3xl border border-line bg-surface p-6 transition-colors ${
        interactive ? 'hover:border-accent/40' : ''
      } ${className}`}
    >
      {(title || action) && (
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="font-display text-xl font-bold tracking-tight">{title}</h2>}
            {subtitle && <p className="mt-1 text-sm text-mute">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

/** Stat chip: icon in a tinted circle, tiny uppercase label, big display number. */
export function Stat({
  label,
  value,
  hint,
  icon: Icon,
  delay = 0,
  className = '',
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon?: LucideIcon
  delay?: number
  className?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 16 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: 'backOut' }}
      className={`rounded-3xl border border-line bg-surface p-5 ${className}`}
    >
      {Icon && (
        <div className="mb-3 grid size-9 place-items-center rounded-full bg-lime/20">
          <Icon className="size-4 text-accent" strokeWidth={2} />
        </div>
      )}
      <div className="text-[10px] tracking-widest text-mute uppercase">{label}</div>
      <div className="mt-1 font-display text-3xl font-bold tracking-tight tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-mute">{hint}</div>}
    </motion.div>
  )
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-24 text-sm text-mute" role="status">
      <Loader2 className="size-4 animate-spin text-accent" /> {label}
    </div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-3xl border border-danger/40 bg-danger/10 p-5 text-sm">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-danger" />
      <div>{message}</div>
    </div>
  )
}

export function Badge({ children, tone = 'muted' }: { children: ReactNode; tone?: 'muted' | 'lime' | 'outline' }) {
  const tones = {
    muted: 'bg-raised text-mute',
    lime: 'bg-lime text-on-lime',
    outline: 'border border-accent/40 text-accent',
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold tracking-wider whitespace-nowrap uppercase ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export const buttonPrimary =
  'group inline-flex items-center justify-center gap-2 rounded-full bg-lime px-6 py-3 text-sm font-semibold text-on-lime transition-all hover:gap-3 hover:bg-ink hover:text-night disabled:pointer-events-none disabled:opacity-60'
export const buttonOutline =
  'inline-flex items-center justify-center gap-2 rounded-full border border-accent/40 px-6 py-3 text-sm font-semibold transition hover:bg-lime/10 disabled:opacity-60'

export function SegmentDot({ color, className = 'size-2.5' }: { color: string; className?: string }) {
  return <span className={`inline-block shrink-0 rounded-full ${className}`} style={{ backgroundColor: color }} />
}

/** Pill tabs with a sliding lime highlight. */
export function PillTabs<T extends string | number>({
  items,
  value,
  onChange,
  layoutId,
}: {
  items: { value: T; label: ReactNode }[]
  value: T
  onChange: (v: T) => void
  layoutId: string
}) {
  return (
    <div className="inline-flex max-w-full flex-wrap gap-1 rounded-3xl border border-line bg-surface p-1.5 sm:rounded-full">
      {items.map((it) => {
        const active = it.value === value
        return (
          <button
            key={String(it.value)}
            type="button"
            onClick={() => onChange(it.value)}
            className={`relative rounded-full px-4 py-2 text-sm transition-colors ${
              active ? 'font-semibold text-on-lime' : 'text-mute hover:text-ink'
            }`}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-full bg-lime"
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative flex items-center gap-2">{it.label}</span>
          </button>
        )
      })}
    </div>
  )
}

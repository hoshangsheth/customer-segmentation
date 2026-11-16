import { Menu, Moon, Sun, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { api } from '../lib/api'
import { useTheme } from '../lib/theme'
import { useApi } from '../lib/useApi'

const NAV = [
  { to: '/', label: 'Overview' },
  { to: '/analyze', label: 'Analyze' },
  { to: '/segments', label: 'Segments' },
  { to: '/performance', label: 'Performance' },
  { to: '/insights', label: 'AI insights' },
]

function useScrolled(threshold = 12) {
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > threshold)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [threshold])
  return scrolled
}

const KAGGLE_URL = 'https://www.kaggle.com/datasets/imakash3011/customer-personality-analysis'

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="Customer Segments home">
      <div className="grid size-9 place-items-center rounded-lg bg-lime">
        <svg viewBox="0 0 20 20" className="size-5" aria-hidden>
          <circle cx="6.5" cy="7" r="2.6" fill="#0a0e0a" />
          <circle cx="13.5" cy="6.5" r="2" fill="#0a0e0a" fillOpacity=".6" />
          <circle cx="10" cy="13.5" r="3.2" fill="#0a0e0a" fillOpacity=".85" />
        </svg>
      </div>
      <span className="font-display text-lg font-bold tracking-tight md:text-xl">
        Customer Segments
      </span>
    </Link>
  )
}

export default function Layout({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme()
  const location = useLocation()
  const health = useApi('health', api.health)
  const [menuOpen, setMenuOpen] = useState(false)
  const scrolled = useScrolled()
  const ai = health.data?.ai_available
  const statusText = health.error ? 'API offline' : ai ? `AI on · ${health.data?.ai_provider}` : 'AI off · rule-based'

  return (
    <div className="flex min-h-screen flex-col">
      <header
        className={`fixed inset-x-0 top-0 z-50 border-b transition-colors duration-300 ${
          scrolled ? 'border-line bg-night/90 backdrop-blur-md' : 'border-transparent'
        }`}
      >
        <div className="relative mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-5 py-4 md:px-8">
          <Logo />

          <nav
            aria-label="Main"
            className="hidden items-center gap-1 rounded-full border border-line bg-surface px-1.5 py-1.5 md:flex"
          >
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `relative rounded-full px-4 py-1.5 text-sm transition-colors ${isActive ? 'text-ink' : 'text-mute hover:text-ink'}`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="nav-active"
                        className="absolute inset-0 rounded-full bg-ink/10"
                        transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                      />
                    )}
                    <span className="relative">{label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <span
              title={health.data?.model_version ? `Model ${health.data.model_version}` : undefined}
              className="hidden items-center gap-2 rounded-full border border-accent/40 px-4 py-2 text-xs font-semibold sm:inline-flex"
            >
              <span className={`size-2 rounded-full ${health.error ? 'bg-danger' : ai ? 'bg-lime shadow-[0_0_10px_#d9ff3d]' : 'bg-mute'}`} />
              {statusText}
            </span>
            <button
              onClick={toggle}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
              className="grid size-10 place-items-center rounded-full border border-line bg-surface transition hover:border-accent/40"
            >
              {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
            </button>
            <button
              onClick={() => setMenuOpen((o) => !o)}
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              className="grid size-10 place-items-center rounded-full border border-line bg-surface md:hidden"
            >
              {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
            </button>
          </div>
        </div>

        <AnimatePresence>
          {menuOpen && (
            <motion.nav
              aria-label="Main"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="relative mx-5 rounded-3xl border border-line bg-surface p-2 shadow-2xl md:hidden"
            >
              {NAV.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) =>
                    `block rounded-2xl px-4 py-3 font-display text-lg font-bold ${isActive ? 'bg-lime text-on-lime' : 'text-ink'}`
                  }
                >
                  {label}
                </NavLink>
              ))}
              <div className="mt-1 flex items-center gap-2 px-4 py-3 text-xs text-mute">
                <span className={`size-2 rounded-full ${health.error ? 'bg-danger' : ai ? 'bg-lime' : 'bg-mute'}`} />
                {statusText}
              </div>
            </motion.nav>
          )}
        </AnimatePresence>
      </header>

      <main className="relative flex-1">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="border-t border-line px-5 py-6 md:px-8">
        <div className="mx-auto flex max-w-[1400px] flex-col justify-between gap-3 text-xs text-mute md:flex-row md:items-center">
          <span>
            Data:{' '}
            <a href={KAGGLE_URL} target="_blank" rel="noreferrer" className="underline-offset-2 hover:text-ink hover:underline">
              Kaggle "Customer Personality Analysis"
            </a>
            . Recreated on public data.
          </span>
        </div>
      </footer>
    </div>
  )
}

/** Standard page width and top padding under the fixed header. */
export function Page({ children }: { children: ReactNode }) {
  return <div className="mx-auto max-w-[1400px] px-5 pt-32 pb-24 md:px-8 md:pt-40">{children}</div>
}

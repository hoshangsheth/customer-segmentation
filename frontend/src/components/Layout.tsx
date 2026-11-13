import { BarChart3, Gauge, LayoutDashboard, Moon, Sparkles, Sun, Target, Users } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { api } from '../lib/api'
import { useTheme } from '../lib/theme'
import { useApi } from '../lib/useApi'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/segments', label: 'Segments', icon: Users },
  { to: '/targeting', label: 'Targeting', icon: Target },
  { to: '/score', label: 'Score a customer', icon: Gauge },
  { to: '/insights', label: 'AI insights', icon: Sparkles },
]

export default function Layout({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme()
  const location = useLocation()
  const health = useApi('health', api.health)

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <aside className="sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur lg:h-screen lg:border-r lg:border-b-0 dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-center justify-between gap-3 px-4 py-3 lg:flex-col lg:items-stretch lg:px-5 lg:py-6">
          <div className="flex items-center gap-2.5">
            <div className="grid size-9 place-items-center rounded-xl bg-indigo-600 text-white shadow-sm">
              <BarChart3 className="size-5" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">Customer Segments</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">and campaign targeting</div>
            </div>
          </div>
          <button
            onClick={toggle}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden dark:text-slate-400 dark:hover:bg-slate-800"
          >
            {theme === 'dark' ? <Sun className="size-5" /> : <Moon className="size-5" />}
          </button>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:px-3 lg:pb-0">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `relative flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-indigo-700 dark:text-indigo-300'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 rounded-lg bg-indigo-50 dark:bg-indigo-500/15"
                      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                    />
                  )}
                  <Icon className="relative size-4" />
                  <span className="relative">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="absolute inset-x-0 bottom-0 hidden space-y-3 p-5 lg:block">
          <div className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
            <div className="flex items-center gap-2">
              <span
                className={`size-2 rounded-full ${health.data?.ai_available ? 'bg-emerald-500' : 'bg-slate-400'}`}
              />
              <span className="font-medium">
                {health.data?.ai_available ? `AI on (${health.data.ai_provider})` : 'AI off: rule-based text'}
              </span>
            </div>
            {health.data?.model_version && (
              <div className="mt-1 text-slate-500 dark:text-slate-400">Model {health.data.model_version}</div>
            )}
          </div>
          <button
            onClick={toggle}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
            {theme === 'dark' ? 'Light theme' : 'Dark theme'}
          </button>
        </div>
      </aside>
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}

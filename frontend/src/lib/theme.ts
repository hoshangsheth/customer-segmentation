import { useState } from 'react'

export type Theme = 'light' | 'dark'

function current(): Theme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

/**
 * Switch themes in one synchronous step. Transitions are paused for that frame, so the browser
 * repaints once instead of animating colour on every element.
 */
function apply(theme: Theme) {
  const root = document.documentElement
  root.classList.add('theme-switching')
  root.classList.toggle('dark', theme === 'dark')
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0a0e0a' : '#f3f4ee')
  void root.offsetHeight // commit styles with transitions off
  setTimeout(() => root.classList.remove('theme-switching'), 50) // a timer also fires in background tabs
  try {
    localStorage.setItem('theme', theme)
  } catch {
    // storage can be blocked; the theme still applies for this visit
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(current)
  const toggle = () => {
    const next: Theme = current() === 'dark' ? 'light' : 'dark'
    apply(next)
    setTheme(next)
  }
  return { theme, toggle }
}

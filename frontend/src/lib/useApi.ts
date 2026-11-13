import { useEffect, useState } from 'react'

// GET responses are cached for the session: the model is fixed while the app runs.
const cache = new Map<string, unknown>()

export interface ApiState<T> {
  data: T | undefined
  error: string | undefined
  loading: boolean
}

export function useApi<T>(key: string, fetcher: () => Promise<T>): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>(() => ({
    data: cache.get(key) as T | undefined,
    error: undefined,
    loading: !cache.has(key),
  }))

  useEffect(() => {
    if (cache.has(key)) {
      setState({ data: cache.get(key) as T, error: undefined, loading: false })
      return
    }
    let alive = true
    setState((s) => ({ ...s, loading: true, error: undefined }))
    fetcher()
      .then((data) => {
        cache.set(key, data)
        if (alive) setState({ data, error: undefined, loading: false })
      })
      .catch((e: Error) => alive && setState({ data: undefined, error: e.message, loading: false }))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state
}

import { useCallback, useEffect, useRef, useState } from 'react'

import { api } from './client'
import { rememberList } from './listSources'

/** Încarcă o resursă; se reîncarcă la schimbarea parametrilor. */
export function useFetch<T>(url: string | null, params?: Record<string, unknown>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const key = JSON.stringify(params ?? {})
  const seq = useRef(0)

  const reload = useCallback(async () => {
    if (!url) return
    const mine = ++seq.current
    setLoading(true)
    try {
      const { data } = await api.get<T>(url, { params: JSON.parse(key) })
      if (mine === seq.current) {
        rememberList(data, url, JSON.parse(key))  // pentru exportul tuturor paginilor în Excel
        setData(data)
        setError(null)
      }
    } catch (e) {
      if (mine === seq.current) setError(e)
    } finally {
      if (mine === seq.current) setLoading(false)
    }
  }, [url, key])

  useEffect(() => {
    reload()
  }, [reload])

  return { data, loading, error, reload, setData }
}

// Nomenclatoarele mici (segmente, surse, unități...) se încarcă o dată pe sesiune.
const cache = new Map<string, Promise<unknown>>()

export function useCachedList<T>(url: string, enabled = true) {
  const [data, setData] = useState<T[]>([])
  useEffect(() => {
    if (!enabled) return
    let alive = true
    if (!cache.has(url)) {
      cache.set(url, api.get(url, { params: { page_size: 1000 } }).then((r) => r.data).catch((e) => {
        cache.delete(url)
        throw e
      }))
    }
    cache.get(url)!
      .then((d) => {
        if (alive) setData((Array.isArray(d) ? d : (d as { results: T[] }).results) as T[])
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [url, enabled])
  return data
}

export function invalidateCache(prefix = '') {
  for (const key of [...cache.keys()]) if (key.startsWith(prefix)) cache.delete(key)
}

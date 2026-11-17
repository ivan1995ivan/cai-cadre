import { useCallback, useEffect, useState } from 'react'

import { api } from './client'

/**
 * Aranjarea interfeței a fiecărui utilizator (coloanele listelor, grupele formelor), păstrată pe server:
 * se încarcă o dată pe sesiune, se salvează la fiecare schimbare.
 */
type Prefs = Record<string, unknown>

let loaded: Promise<Prefs> | null = null
let cache: Prefs = {}
const listeners = new Set<() => void>()

function load(): Promise<Prefs> {
  if (!loaded) {
    loaded = api.get<Prefs>('/ui-prefs/').then((r) => (cache = r.data || {})).catch(() => (cache = {}))
  }
  return loaded
}

/** Cheia fără „/” (adresa o împarte): „table:invoices:a1b2”. */
export function prefKey(...parts: string[]): string {
  return parts.join(':').replace(/[/\\?#%]+/g, '.').replace(/\.+/g, '.').slice(0, 190)
}

export function useUiPref<T>(key: string | null): [T | undefined, (value: T) => void, () => void, boolean] {
  const [, force] = useState(0)
  const [ready, setReady] = useState(!!loaded && key !== null && key in cache ? true : false)
  useEffect(() => {
    const listener = () => force((n) => n + 1)
    listeners.add(listener)
    load().then(() => setReady(true))
    return () => { listeners.delete(listener) }
  }, [])
  const save = useCallback((value: T) => {
    if (!key) return
    cache = { ...cache, [key]: value }
    listeners.forEach((l) => l())
    api.put(`/ui-prefs/${encodeURIComponent(key)}/`, { value }).catch(() => undefined)
  }, [key])
  const reset = useCallback(() => {
    if (!key) return
    const next = { ...cache }
    delete next[key]
    cache = next
    listeners.forEach((l) => l())
    api.delete(`/ui-prefs/${encodeURIComponent(key)}/`).catch(() => undefined)
  }, [key])
  return [key ? (cache[key] as T | undefined) : undefined, save, reset, ready]
}

// --- aranjarea implicită pentru toți (pusă de administrator; o folosește cine nu și-a făcut-o pe a lui) ---

let defaultsLoaded: Promise<Prefs> | null = null
let defaults: Prefs = {}

function loadDefaults(): Promise<Prefs> {
  if (!defaultsLoaded) {
    defaultsLoaded = api.get<Prefs>('/ui-defaults/').then((r) => (defaults = r.data || {})).catch(() => (defaults = {}))
  }
  return defaultsLoaded
}

/** [aranjarea pentru toți, salvează pentru toți, șterge-o] — salvarea cere dreptul de a modifica setările. */
export function useUiDefault<T>(key: string | null): [T | undefined, (value: T) => Promise<void>, () => Promise<void>] {
  const [, force] = useState(0)
  useEffect(() => {
    const listener = () => force((n) => n + 1)
    listeners.add(listener)
    loadDefaults().then(listener)
    return () => { listeners.delete(listener) }
  }, [])
  const save = useCallback(async (value: T) => {
    if (!key) return
    await api.put(`/ui-defaults/${encodeURIComponent(key)}/`, { value })
    defaults = { ...defaults, [key]: value }
    listeners.forEach((l) => l())
  }, [key])
  const reset = useCallback(async () => {
    if (!key) return
    await api.delete(`/ui-defaults/${encodeURIComponent(key)}/`)
    const next = { ...defaults }
    delete next[key]
    defaults = next
    listeners.forEach((l) => l())
  }, [key])
  return [key ? (defaults[key] as T | undefined) : undefined, save, reset]
}

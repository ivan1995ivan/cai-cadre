import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

/** Baza aleasă pe platformă (cookie-ul „crm_base”): fiecare bază își ține separat sesiunea în browser. */
export function currentBaseId(): string {
  const match = document.cookie.match(/(?:^|;\s*)crm_base=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

const SUFFIX = currentBaseId() ? `.${currentBaseId()}` : ''
const ACCESS = `crm.access${SUFFIX}`
const REFRESH = `crm.refresh${SUFFIX}`

function storageGet(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function storageSet(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* stocarea poate fi blocată de browser */
  }
}

export const tokens = {
  get access() {
    return storageGet(ACCESS)
  },
  get refresh() {
    return storageGet(REFRESH)
  },
  set(access: string | null, refresh?: string | null) {
    storageSet(ACCESS, access)
    if (refresh !== undefined) storageSet(REFRESH, refresh)
  },
  clear() {
    storageSet(ACCESS, null)
    storageSet(REFRESH, null)
  },
}

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const access = tokens.access
  if (access) config.headers.Authorization = `Bearer ${access}`
  config.headers['Accept-Language'] = document.documentElement.lang || 'ro'
  return config
})

let refreshing: Promise<string | null> | null = null
let onSessionExpired: () => void = () => {}

export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler
}

async function refreshAccess(): Promise<string | null> {
  const refresh = tokens.refresh
  if (!refresh) return null
  try {
    const { data } = await axios.post('/api/auth/refresh/', { refresh })
    tokens.set(data.access, data.refresh ?? refresh)
    return data.access
  } catch {
    return null
  }
}

const LOGOUT_REASON = 'crm.logoutReason'

/** Motivul ieșirii forțate (sesiunea închisă de administrator, baza blocată): îl arată pagina de intrare o dată. */
export function takeLogoutReason(): string {
  try {
    const reason = sessionStorage.getItem(LOGOUT_REASON) || ''
    sessionStorage.removeItem(LOGOUT_REASON)
    return reason
  } catch {
    return ''
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const body = error.response?.data as { code?: string; detail?: string } | undefined
    if (error.response?.status === 401 && (body?.code === 'session_closed' || body?.code === 'maintenance')) {
      // consola serverului a închis sesiunea sau a blocat intrarea: reîmprospătarea n-ar ajuta
      try { sessionStorage.setItem(LOGOUT_REASON, body.detail || '') } catch { /* fără stocare */ }
      tokens.clear()
      onSessionExpired()
      return Promise.reject(error)
    }
    if (error.response?.status === 401 && original && !original._retry && !original.url?.includes('auth/login')) {
      original._retry = true
      refreshing = refreshing ?? refreshAccess().finally(() => (refreshing = null))
      const access = await refreshing
      if (access) {
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      }
      tokens.clear()
      onSessionExpired()
    }
    return Promise.reject(error)
  },
)

/** Textul erorii din răspunsul serverului (detail sau primul mesaj de câmp). */
export function errorText(error: unknown, fallback = 'Eroare'): string {
  const response = (error as AxiosError<Record<string, unknown>>)?.response
  const data = response?.data
  if (!data) return (error as Error)?.message || fallback
  // pagina HTML a serverului (de ex. 500 / 502): măcar codul, ca eroarea să poată fi găsită în server.log
  if (typeof data === 'string') return response?.status ? `${fallback} (HTTP ${response.status})` : fallback
  if (typeof data.detail === 'string') return data.detail
  const first = Object.entries(data)[0]
  if (first) {
    const [field, value] = first
    const msg = Array.isArray(value) ? value[0] : typeof value === 'object' ? JSON.stringify(value) : value
    return field === 'non_field_errors' ? String(msg) : `${field}: ${msg}`
  }
  return fallback
}

/** Erorile de câmp pentru Form.setFields din Ant Design. */
export function fieldErrors(error: unknown): { name: string | string[]; errors: string[] }[] {
  const data = (error as AxiosError<Record<string, unknown>>)?.response?.data
  if (!data || typeof data !== 'object') return []
  return Object.entries(data)
    .filter(([k]) => k !== 'detail')
    .map(([name, value]) => ({
      name,
      errors: Array.isArray(value) ? value.map(String) : [String(value)],
    }))
}

export interface Paged<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

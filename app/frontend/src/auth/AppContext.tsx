import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import i18n from 'i18next'
import dayjs from 'dayjs'
import 'dayjs/locale/ro'
import 'dayjs/locale/ru'

import { api, setSessionExpiredHandler, tokens } from '../api/client'
import type { Branding, Lang, Me } from '../api/types'
import { resolveTheme, type ButtonStyle, type Density, type ThemeChoice, type ThemeName } from '../theme/themes'

const LOCAL_THEME = 'crm.theme'
const LOCAL_LANG = 'crm.lang'

function localGet(key: string) {
  try {
    return localStorage.getItem(key) || ''
  } catch {
    return ''
  }
}
function localSet(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* ignorat */
  }
}

interface AppState {
  branding: Branding | null
  me: Me | null
  ready: boolean
  themeName: ThemeName
  themeChoice: ThemeChoice
  density: Density
  buttons: ButtonStyle
  lang: Lang
  /** Limbile pornite în Constante (cel puțin una); comutatoarele arată doar aceste limbi. */
  languages: Lang[]
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  reloadMe: () => Promise<void>
  reloadBranding: () => Promise<void>
  updateMe: (patch: Partial<Me>) => Promise<void>
  setThemeChoice: (theme: ThemeChoice) => void
  setDensity: (density: Density) => void
  setButtons: (buttons: ButtonStyle) => void
  setLang: (lang: Lang) => void
  hasPerm: (code: string) => boolean
  /** Profilul „acoperișuri și garduri”: calculatorul, rolele de tablă, foile. În profilul „comerț” (implicit) sunt ascunse. */
  roofing: boolean
  companyName: string
}

const Ctx = createContext<AppState | null>(null)

function usePrefersDark() {
  const query = '(prefers-color-scheme: dark)'
  const [dark, setDark] = useState(() => window.matchMedia?.(query).matches ?? false)
  useEffect(() => {
    const mql = window.matchMedia?.(query)
    if (!mql) return
    const listener = (e: MediaQueryListEvent) => setDark(e.matches)
    mql.addEventListener('change', listener)
    return () => mql.removeEventListener('change', listener)
  }, [])
  return dark
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<Branding | null>(null)
  const [me, setMe] = useState<Me | null>(null)
  const [ready, setReady] = useState(false)
  const [localTheme, setLocalTheme] = useState<ThemeChoice>(() => localGet(LOCAL_THEME) as ThemeChoice)
  const [localLang, setLocalLang] = useState<Lang>(() => (localGet(LOCAL_LANG) as Lang) || 'ro')
  const prefersDark = usePrefersDark()

  const reloadBranding = useCallback(async () => {
    const { data } = await api.get<Branding>('/public/branding/')
    setBranding(data)
  }, [])

  const reloadMe = useCallback(async () => {
    const { data } = await api.get<Me>('/auth/me/')
    setMe(data)
  }, [])

  useEffect(() => {
    setSessionExpiredHandler(() => setMe(null))
    const init = async () => {
      try {
        await reloadBranding()
      } catch {
        /* fără branding se folosesc valorile implicite */
      }
      if (tokens.access || tokens.refresh) {
        try {
          await reloadMe()
        } catch {
          tokens.clear()
        }
      }
      setReady(true)
    }
    init()
  }, [reloadBranding, reloadMe])

  const languages = useMemo<Lang[]>(() => (branding?.languages?.length ? branding.languages : ['ro', 'ru', 'en']), [branding])
  const wanted: Lang = me?.language || localLang
  const lang: Lang = languages.includes(wanted) ? wanted : languages[0]
  useEffect(() => {
    i18n.changeLanguage(lang)
    dayjs.locale(lang)
    document.documentElement.lang = lang
  }, [lang])

  const themeChoice: ThemeChoice = me ? me.theme : localTheme
  const themeName = resolveTheme(themeChoice, branding?.default_theme || 'green', prefersDark)
  const density: Density = me?.density || 'normal'
  const buttons: ButtonStyle = me?.buttons || '3d'

  const updateMe = useCallback(async (patch: Partial<Me>) => {
    const { data } = await api.patch<Me>('/auth/me/', patch)
    setMe(data)
  }, [])

  const login = useCallback(
    async (username: string, password: string) => {
      const { data } = await api.post('/auth/login/', { username, password })
      tokens.set(data.access, data.refresh)
      await reloadMe()
    },
    [reloadMe],
  )

  const logout = useCallback(() => {
    tokens.clear()
    navigator.serviceWorker?.controller?.postMessage('logout')
    setMe(null)
  }, [])

  const setThemeChoice = useCallback(
    (theme: ThemeChoice) => {
      localSet(LOCAL_THEME, theme)
      setLocalTheme(theme)
      if (me) updateMe({ theme })
    },
    [me, updateMe],
  )

  const setDensity = useCallback((d: Density) => (me ? updateMe({ density: d }) : undefined), [me, updateMe])
  const setButtons = useCallback((b: ButtonStyle) => (me ? updateMe({ buttons: b }) : undefined), [me, updateMe])

  const setLang = useCallback(
    (l: Lang) => {
      localSet(LOCAL_LANG, l)
      setLocalLang(l)
      if (me) updateMe({ language: l })
    },
    [me, updateMe],
  )

  const hasPerm = useCallback((code: string) => !!me && (me.is_admin || me.permissions.includes(code)), [me])
  const roofing = me?.profile === 'roofing'

  const companyName = (lang === 'ru' && branding?.name_ru) || branding?.name_ro || 'CAI CADRE'

  const value = useMemo<AppState>(
    () => ({
      branding, me, ready, themeName, themeChoice, density, buttons, lang, languages, login, logout, reloadMe, reloadBranding,
      updateMe, setThemeChoice, setDensity, setButtons, setLang, hasPerm, companyName, roofing,
    }),
    [branding, me, ready, themeName, themeChoice, density, buttons, lang, languages, login, logout, reloadMe, reloadBranding,
      updateMe, setThemeChoice, setDensity, setButtons, setLang, hasPerm, companyName, roofing],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useApp() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp în afara AppProvider')
  return ctx
}

/** Denumirea în limba curentă dintr-un obiect cu name_ro / name_ru. */
export function useLocalName() {
  const { lang } = useApp()
  return (obj: { name_ro: string; name_ru?: string; name_en?: string } | null | undefined) =>
    obj ? (lang === 'ru' && obj.name_ru) || (lang === 'en' && obj.name_en) || obj.name_ro : ''
}

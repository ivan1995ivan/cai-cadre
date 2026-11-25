import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button, Tabs, Tooltip } from 'antd'
import dayjs from 'dayjs'
import { CloseCircleOutlined, CloseSquareOutlined, HomeOutlined, StarFilled, StarOutlined } from '@ant-design/icons'

import { useFavorites } from './favorites'
import { itemOfPath, ROUTE_ITEMS } from './menu'
import { movedTo, navLabel } from './nav'

/**
 * Ferestrele deschise (ca bara de jos din 1C): fiecare pagină deschisă rămâne ca filă — fișa clientului, oferta unui
 * client, oferta altuia, un raport — și se trece între ele cu un clic. Pagina de start e mereu prima.
 * Paginile își pot pune singure titlul (useTabTitle, se ține în filă); altfel fila poartă denumirea din meniu, luată la
 * fiecare afișare („Oferte #12”) — urmează limba interfeței și denumirile noi.
 * Fila paginii curente se închide abia după ce s-a plecat de pe ea: forma cu modificări nesalvate poate opri plecarea
 * („Salvați modificările?” → Anulare, vezi UnsavedGuard) și atunci fila rămâne.
 */
/**
 * Titlul filei: un text care nu se traduce (numele angajatului) sau cheia de traducere cu parametrii ei — se traduce la
 * fiecare afișare, ca fila să urmeze limba interfeței („Ordinul 1-p” → „Приказ 1-p”); `{ month: n }` — luna n în limba
 * interfeței.
 */
export type TabTitle = string | { key: string; params?: Record<string, string | number | { month: number }> }

export interface OpenTab { path: string; title?: TabTitle }

const validTitle = (x: unknown): x is TabTitle => typeof x === 'string'
  || (!!x && typeof x === 'object' && typeof (x as { key?: unknown }).key === 'string')

const STORE = 'crm.tabs.v2'
const OLD_STORE = 'crm.tabs' // până la 1.4.1: și denumirea din meniu de la deschidere, rămasă apoi veche
const MAX = 20
const HOME = '/'

interface TabsApi {
  tabs: { path: string; title: string }[]
  setTitle: (path: string, title: TabTitle) => void
  close: (path: string) => void
  closeAll: () => void
  /** Închide toate filele în afară de cea deschisă acum. */
  closeOthers: () => void
  /** Plecarea de pe pagină a fost oprită (utilizatorul rămâne în formă): filele puse la închidere rămân. */
  keepClosing: () => void
}

const TabsContext = createContext<TabsApi>({
  tabs: [], setTitle: () => undefined, close: () => undefined, closeAll: () => undefined, closeOthers: () => undefined,
  keepClosing: () => undefined,
})

function read(): OpenTab[] {
  try {
    const own = localStorage.getItem(STORE)
    const data = JSON.parse(own ?? localStorage.getItem(OLD_STORE) ?? '[]')
    // filele adreselor de dinainte de Setări nu se mai deschid (adresa duce la setarea nouă)
    const moved = (path: string) => { const [p, q = ''] = path.split('?'); return movedTo(p, q) }
    return Array.isArray(data)
      ? data.filter((x) => typeof x?.path === 'string' && x.path.startsWith('/') && !moved(x.path)).slice(0, MAX)
        .map((x) => ({ path: x.path, ...(own !== null && validTitle(x.title) ? { title: x.title } : {}) }))
      : []
  } catch {
    return []
  }
}

export function useFallbackTitle() {
  const { t } = useTranslation()
  return useCallback((path: string) => {
    if (path === HOME) return t('menu.dashboard')
    const clean = path.split('?')[0]
    const item = itemOfPath(ROUTE_ITEMS.filter((i) => i.path !== HOME), clean)
    if (!item) return clean
    const rest = clean.slice(item.path.length).replace(/^\//, '')
    return rest ? `${navLabel(t, item)} · ${rest === 'new' ? t('tabs.new') : `#${rest.split('/')[0]}`}` : navLabel(t, item)
  }, [t])
}

export function TabsProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const fallback = useFallbackTitle()
  const [tabs, setTabs] = useState<OpenTab[]>(read)
  const current = location.pathname + location.search
  // filele de închis după plecarea de pe pagina curentă (null — nimic de închis)
  const closing = useRef<string[] | null>(null)

  useEffect(() => {
    const gone = closing.current
    closing.current = null
    setTabs((all) => {
      const cur = gone ? all.filter((x) => !gone.includes(x.path)) : all
      // panoul unei secțiuni (Panoul funcțiilor) e meniul, nu o fereastră: nu ia filă
      if (location.pathname === HOME || location.pathname.startsWith('/panel/') || movedTo(location.pathname, location.search)) return cur
      const same = cur.find((x) => x.path.split('?')[0] === location.pathname)
      if (same) return same.path === current ? cur : cur.map((x) => (x === same ? { ...x, path: current } : x))
      const next = [...cur, { path: current }]
      return next.length > MAX ? next.slice(next.length - MAX) : next
    })
  }, [current, location.pathname])

  useEffect(() => {
    try {
      localStorage.setItem(STORE, JSON.stringify(tabs))
      localStorage.removeItem(OLD_STORE)
    } catch { /* fără stocare */ }
  }, [tabs])

  const setTitle = useCallback((path: string, title: TabTitle) => {
    const sig = JSON.stringify(title)
    setTabs((cur) => cur.map((x) => (x.path.split('?')[0] === path && JSON.stringify(x.title) !== sig ? { ...x, title } : x)))
  }, [])
  const close = useCallback((path: string) => {
    if (current !== path) {
      setTabs((cur) => cur.filter((x) => x.path !== path))
      return
    }
    const i = tabs.findIndex((x) => x.path === path)
    const next = tabs.filter((x) => x.path !== path)
    closing.current = [path]
    navigate(next[Math.min(i, next.length - 1)]?.path ?? HOME)
  }, [current, tabs, navigate])

  const closeAll = useCallback(() => {
    if (current === HOME) {
      setTabs([])
      return
    }
    closing.current = tabs.map((x) => x.path)
    navigate(HOME)
  }, [current, tabs, navigate])

  const closeOthers = useCallback(() => {
    setTabs((cur) => cur.filter((x) => x.path === current))
  }, [current])

  const keepClosing = useCallback(() => { closing.current = null }, [])

  const { t, i18n } = useTranslation()
  const render = useCallback((title: TabTitle) => {
    if (typeof title === 'string') return title
    const params = Object.fromEntries(Object.entries(title.params ?? {}).map(([k, v]) => [k,
      typeof v === 'object' ? dayjs().locale(i18n.language).month(v.month - 1).format('MMMM') : v]))
    return t(title.key, params)
  }, [t, i18n.language])
  const titled = useMemo(() => tabs.map((x) => ({ path: x.path, title: x.title !== undefined ? render(x.title) : fallback(x.path) })),
    [tabs, fallback, render])
  const value = useMemo(() => ({ tabs: titled, setTitle, close, closeAll, closeOthers, keepClosing }),
    [titled, setTitle, close, closeAll, closeOthers, keepClosing])
  return <TabsContext.Provider value={value}>{children}</TabsContext.Provider>
}

/** Filele deschise și închiderea lor (✕ din formă, UnsavedGuard). */
export function useTabs() {
  return useContext(TabsContext)
}

/** Pagina își dă titlul filei (numele angajatului; „Ordinul 1-p” ca cheie de traducere, ca să urmeze limba interfeței). */
export function useTabTitle(title: TabTitle | null | undefined) {
  const { setTitle } = useContext(TabsContext)
  const { pathname } = useLocation()
  const sig = title ? JSON.stringify(title) : ''
  useEffect(() => {
    if (sig) setTitle(pathname, JSON.parse(sig) as TabTitle)
  }, [sig, pathname, setTitle])
}

/** Bara de jos cu ferestrele deschise: „Închide toate” lângă Pagina de start; steluța pune pagina curentă la favorite. */
export function OpenTabsBar() {
  const { t } = useTranslation()
  const { tabs, close, closeAll, closeOthers } = useContext(TabsContext)
  const location = useLocation()
  const navigate = useNavigate()
  const { isFavorite, toggle } = useFavorites()
  const current = location.pathname + location.search
  const active = location.pathname === HOME ? HOME : tabs.find((x) => x.path.split('?')[0] === location.pathname)?.path ?? current
  const activeTab = tabs.find((x) => x.path === active)
  const starred = active !== HOME && isFavorite(active)
  return (
    <div style={{
      position: 'sticky', bottom: 0, zIndex: 9, display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px 0',
      background: 'var(--ant-color-bg-layout)', borderTop: '1px solid var(--ant-color-border-secondary)',
    }}>
      <Tooltip title={t('tabs.closeAllHint')}>
        <Button size="small" icon={<CloseCircleOutlined />} disabled={tabs.length === 0} onClick={closeAll} aria-label={t('tabs.closeAll')}
          style={{ marginBottom: 4 }}>{t('tabs.closeAll')}</Button>
      </Tooltip>
      <Tooltip title={t('tabs.closeOthersHint')}>
        <Button size="small" icon={<CloseSquareOutlined />} disabled={tabs.filter((x) => x.path !== active).length === 0}
          onClick={closeOthers} aria-label={t('tabs.closeOthers')} style={{ marginBottom: 4 }} />
      </Tooltip>
      <Tabs type="editable-card" hideAdd size="small" activeKey={active} style={{ flex: 1, minWidth: 0, marginBottom: 0 }}
        tabBarStyle={{ marginBottom: 0 }}
        onChange={(key) => navigate(key)}
        onEdit={(key, action) => { if (action === 'remove') close(String(key)) }}
        items={[
          { key: HOME, label: <span><HomeOutlined /> {t('tabs.home')}</span>, closable: false },
          ...tabs.map((x) => ({ key: x.path, label: <span title={x.title}>{x.title.length > 34 ? `${x.title.slice(0, 33)}…` : x.title}</span> })),
        ]} />
      {active !== HOME && activeTab && (
        <Tooltip title={t(starred ? 'tabs.unstar' : 'tabs.star')}>
          <Button type="text" size="small" icon={starred ? <StarFilled style={{ color: '#f5a623' }} /> : <StarOutlined />}
            onClick={() => toggle({ path: activeTab.path.split('?')[0], key: '', title: activeTab.title })} />
        </Tooltip>
      )}
    </div>
  )
}

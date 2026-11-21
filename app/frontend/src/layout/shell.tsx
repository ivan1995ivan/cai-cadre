import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useNavigationType } from 'react-router-dom'

import { SETTINGS_NAV, navLabel } from './nav'
import {
  itemOfPath, panelPath, ROUTE_ITEMS, useFunctionPanel, useMainMenu, useSectionPanel, type MenuSectionView,
} from './menu'

/* Ce folosesc ambele aspecte ale programului (meniul lateral — AppLayout, programul clasic de birou — DesktopLayout). */

/** Cheia instrucțiunii pentru ruta curentă: "/admin/users" → "admin/users", "/" → "start". */
export function helpKeyFor(pathname: string) {
  if (pathname.startsWith('/panel/')) return 'panel' // panoul oricărei secțiuni are aceeași instrucțiune
  const clean = pathname.replace(/\/\d+.*$/, '').replace(/^\/|\/$/g, '')
  return clean || 'start'
}

/** Platforma cu mai multe baze (launcher.py): numele bazei curente; null când serverul rulează fără platformă. */
export function usePlatform() {
  const [info, setInfo] = useState<{ base: { id: string; name: string } | null; count: number } | null>(null)
  useEffect(() => {
    fetch('/__platform/current').then((r) => (r.ok ? r.json() : null)).then(setInfo).catch(() => setInfo(null))
  }, [])
  return info
}

/**
 * Înapoi / Înainte ca în browser, dar știind când nu mai e unde: react-router ține poziția în istoric (`history.state.idx`);
 * după o navigare nouă (PUSH) nu mai e „înainte”.
 */
export function useHistoryNav() {
  const location = useLocation()
  const type = useNavigationType()
  const idx: number = (window.history.state as { idx?: number } | null)?.idx ?? 0
  const seen = useRef({ key: location.key, furthest: idx })
  if (seen.current.key !== location.key) {
    // socotit la desenare (nu în efect), ca butoanele să fie corecte chiar de la prima afișare a paginii noi
    seen.current = { key: location.key, furthest: type === 'PUSH' ? idx : Math.max(seen.current.furthest, idx) }
  }
  return { canBack: idx > 0, canForward: idx < seen.current.furthest }
}

/**
 * Secțiunea meniului principal a paginii deschise (pentru meniul de sus, panoul funcțiilor, bara de meniu clasică): funcția
 * cu adresa cea mai lungă potrivită și secțiunea ei; cu Panoul funcțiilor — și secțiunea din care s-a deschis pagina.
 */
export function useSectionChoice() {
  const location = useLocation()
  const navigate = useNavigate()
  const sections = useMainMenu()
  const fnPanel = useFunctionPanel()
  const panelKey = location.pathname.startsWith('/panel/') ? location.pathname.split('/')[2] : null
  // adresa curentă cu parametrii (filele din modul: /training?tab=plans)
  const full = location.pathname + location.search
  const matches = (path: string) => (path === '/' ? location.pathname === '/' : full.startsWith(path))
  // funcția cu adresa cea mai lungă potrivită („/reports/movement”, nu și „/reports”) și secțiunea ei; o setare deschisă
  // (Valute, Ture, un clasificator) ține de funcția „Setări”, chiar dacă adresa ei seamănă cu a unui registru (/leave/settings)
  const menuFunctions = sections.flatMap((sec) => sec.navItems)
  const selectedItem = itemOfPath(SETTINGS_NAV, location.pathname)
    ? menuFunctions.find((i) => i.key === 'settings')
    : menuFunctions.filter((i) => matches(i.path)).sort((a, b) => b.path.length - a.path.length)[0]
  const [chosen, setChosen] = useState<string | null>(() => {
    try { return localStorage.getItem('crm.section') } catch { return null }
  })
  const remember = (key: string) => {
    setChosen(key)
    try { localStorage.setItem('crm.section', key) } catch { /* fără stocare */ }
  }
  // Panoul funcțiilor: fila secțiunii din care s-a deschis pagina rămâne aleasă — și pentru un clasificator din panoul ei,
  // și pentru o funcție care stă în mai multe secțiuni
  const chosenSection = sections.find((sec) => sec.key === chosen)
  const chosenPanel = useSectionPanel(fnPanel ? chosenSection : undefined)
  const openSetting = itemOfPath(SETTINGS_NAV, location.pathname)
  const keepsChosen = !!chosenSection && (openSetting
    ? !!chosenPanel?.classifiers.some((i) => i.key === openSetting.key)
    : !!selectedItem && chosenSection.navItems.includes(selectedItem))
  const current = fnPanel && panelKey ? sections.find((sec) => sec.key === panelKey)
    : fnPanel && keepsChosen ? chosenSection
    : selectedItem && sections.find((sec) => sec.navItems.includes(selectedItem))
  useEffect(() => {
    if (!fnPanel || !panelKey) return
    setChosen(panelKey)
    try { localStorage.setItem('crm.section', panelKey) } catch { /* fără stocare */ }
  }, [fnPanel, panelKey])
  const active = current ?? sections.find((sec) => sec.key === chosen) ?? sections[0]
  const pickSection = (key: string) => {
    const sec = sections.find((x) => x.key === key)
    remember(key)
    if (fnPanel) navigate(panelPath(key))
    else if (sec && !sec.navItems.some((i) => matches(i.path))) navigate(sec.navItems[0].path)
  }
  return { sections, fnPanel, panelKey, selectedItem, current, active, pickSection }
}

/** F1 — instrucțiunea ecranului curent, ca în 1C (și oprește ajutorul browserului). */
export function useHelpKey(open: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'F1') return
      e.preventDefault()
      open()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
}

/** Denumirea ecranului curent (pentru fișa de ajutor): setarea sau funcția din meniu cu calea cea mai lungă potrivită;
 *  la o setare — „Administrare → Setări → Valute”. */
export function screenTitleOf(t: (key: string) => string, pathname: string, sections: MenuSectionView[], current?: MenuSectionView) {
  if (pathname.startsWith('/panel/')) return [current?.label, t('fnPanel.title')].filter(Boolean).join(' → ')
  const setting = itemOfPath(SETTINGS_NAV, pathname)
  const item = setting ? ROUTE_ITEMS.find((i) => i.key === 'settings') : itemOfPath(ROUTE_ITEMS, pathname)
  const section = item && sections.find((sec) => sec.navItems.some((i) => i.key === item.key))
  return item ? [section?.label, navLabel(t, item), setting && navLabel(t, setting)].filter(Boolean).join(' → ') : ''
}


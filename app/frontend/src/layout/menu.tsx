import { useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ApartmentOutlined, BarChartOutlined, CalendarOutlined, FileTextOutlined, FolderOutlined, HomeOutlined, ReadOutlined,
  SettingOutlined, StarOutlined, TeamOutlined, WalletOutlined,
} from '@ant-design/icons'

import { Grid } from 'antd'

import { useFetch } from '../api/hooks'
import { useUiPref } from '../api/uiPrefs'
import { useApp } from '../auth/AppContext'
import { ADMIN_NAV, NAV, PANEL_CLASSIFIERS, PANEL_FLOWS, PANEL_KIND, REPORT_NAV, SETTINGS_NAV, navLabel, type NavItem } from './nav'

/** Iconițele secțiunilor meniului principal (se aleg în editorul meniului). */
export const SECTION_ICONS: Record<string, React.ReactNode> = {
  home: <HomeOutlined />, org: <ApartmentOutlined />, crm: <TeamOutlined />, orders: <FileTextOutlined />,
  calendar: <CalendarOutlined />, wallet: <WalletOutlined />, training: <ReadOutlined />, reports: <BarChartOutlined />,
  admin: <SettingOutlined />, star: <StarOutlined />, folder: <FolderOutlined />,
}

/** Grupele fiecărei secțiuni: Registre și Rapoarte. Setările nu mai stau în secțiuni — toate sunt la Administrare → Setări. */
export type MenuGroup = 'items' | 'reports'
export const GROUPS: MenuGroup[] = ['items', 'reports']

export interface MenuSection { key: string; name_ro: string; name_ru: string; icon: string; items: string[]; reports: string[] }

/** Toate funcțiile unei secțiuni, din ambele grupe (o funcție poate sta în mai multe grupe sau secțiuni). */
export const sectionKeys = (s: MenuSection) => [...s.items, ...s.reports]

const section = (key: string, icon: string, items: string[], reports: string[] = []): MenuSection =>
  ({ key, name_ro: '', name_ru: '', icon, items, reports })

/**
 * Așezarea implicită: în fiecare secțiune Registre (documentele blocului) și Rapoarte (rapoartele blocului, deschise direct).
 * O funcție poate sta în mai multe locuri (de ex. Formularul MUNCA-1 la Salarii și la Rapoarte). Funcțiile care nu sunt aici
 * rămân în program (favorite, adresă) și administratorul le poate pune în meniu din editor („Funcții neafișate”). Setările nu
 * sunt funcții de meniu: le deschide Administrare → Setări (SETTINGS_NAV).
 */
export const DEFAULT_SECTIONS: MenuSection[] = [
  section('principal', 'home', ['dashboard', 'alerts', 'portal']),
  section('institutia', 'org',
    ['org', 'staffList', 'occupancy'],
    ['repVacancies', 'repStructure']),
  section('angajati', 'crm',
    ['employees', 'contracts', 'employeeRequests'],
    ['repMovement', 'repSeniority', 'repBirthdays', 'repRetirements', 'repWorkwear']),
  section('ordine', 'orders',
    ['orders', 'ordersRegister'],
    ['repOrdersByType', 'repOrdersPayroll']),
  section('concedii', 'calendar',
    ['leave', 'leaveSchedule', 'sickLeave', 'rosters', 'timesheets'],
    ['repLeavePeriod', 'repTimesheetSummary']),
  section('salarii', 'wallet',
    ['payItemChanges', 'payroll', 'payrollPayments', 'itPark'],
    ['repSalaryBook', 'taxReports', 'repMunca1']),
  section('formare', 'training',
    ['training', 'health', 'military'],
    ['repTrainingPeriod', 'repTrainingExpiry', 'repHealthDue', 'repMilitaryRegister', 'repMilitaryMissing', 'repMilitaryChanges', 'repMilitaryRecruits']),
  section('rapoarte', 'reports',
    ['reports'],
    ['repMunca1', 'taxReports']),
  section('administrare', 'admin',
    ['settings', 'online', 'audit', 'excelImport', 'maintenance', 'markedObjects', 'license']),
]

/** Funcțiile de meniu (fără setări). */
export const ALL_ITEMS: NavItem[] = [...NAV, ...ADMIN_NAV, ...REPORT_NAV]
/** Tot ce are pagină: funcțiile de meniu și setările (pentru titlul filei, favorite, fișa de ajutor). */
export const ROUTE_ITEMS: NavItem[] = [...ALL_ITEMS, ...SETTINGS_NAV]

/** Ce ține de modulul Salarizare: dispare din meniu și din Setări când întreprinderea e livrată fără salariu (Constante → Module). */
export const PAYROLL_ITEMS = new Set(['payroll', 'payrollPayments', 'payItemChanges', 'itPark', 'payrollTypes', 'payrollConstants', 'taxSettings', 'taxReports', 'repSalaryBook'])
/** Ce ține de modulul opțional „Evidența militară” (oprit implicit, Constante → Module): registrul și rapoartele lui dispar
 *  singure (serverul nu dă drepturile `military.*`), clasificatoarele lui se ascund aici. */
export const MILITARY_ITEMS = new Set(['military', 'repMilitaryRegister', 'repMilitaryMissing', 'repMilitaryChanges', 'repMilitaryRecruits',
  'dict:military_group', 'dict:military_rank', 'dict:military_center'])

/** Funcția / setarea ține de un modul oprit din Constante → Module (Salarizarea, Evidența militară). */
export function moduleOff(branding: { payroll_enabled?: boolean; military_enabled?: boolean } | null | undefined, key: string): boolean {
  return (branding?.payroll_enabled === false && PAYROLL_ITEMS.has(key)) || (branding?.military_enabled !== true && MILITARY_ITEMS.has(key))
}
const BY_KEY = Object.fromEntries(ALL_ITEMS.map((i) => [i.key, i]))

/** Setarea (sau funcția) cu adresa cea mai lungă care se potrivește cu pagina deschisă. */
export function itemOfPath<T extends NavItem>(items: T[], pathname: string): T | undefined {
  return items.filter((i) => (i.path === '/' ? pathname === '/' : pathname === i.path || pathname.startsWith(`${i.path}/`)))
    .sort((a, b) => b.path.length - a.path.length)[0]
}

/** Setările pe care le vede utilizatorul: are dreptul, rolul nu le-a debifat (Roluri → Meniul principal), modulul Salarizare
 *  e pornit. */
function useVisibleSettings(): NavItem[] {
  const { me, hasPerm, branding } = useApp()
  return useMemo(() => {
    const hidden = new Set(me?.menu_hidden ?? [])
    return SETTINGS_NAV.filter((i) => (!i.perm || hasPerm(i.perm)) && !hidden.has(i.key) && !moduleOff(branding, i.key))
  }, [me, hasPerm, branding])
}

/** Setările utilizatorului în ordine alfabetică (lista Administrare → Setări). */
export function useSettingsItems(): NavItem[] {
  const items = useVisibleSettings()
  const { t, i18n } = useTranslation()
  return useMemo(() => [...items].sort((a, b) => navLabel(t, a).localeCompare(navLabel(t, b), i18n.language)), [items, t, i18n.language])
}

/** Secțiunile salvate, completate: funcțiile din așezarea implicită apărute după salvare intră în grupa lor din secțiunea
 * implicită; dacă meniul salvat n-are secțiunea, ea se adaugă la locul ei. Într-o grupă o funcție stă o singură dată. */
export function completeSections(saved: MenuSection[] | undefined): MenuSection[] {
  const clean = (keys: string[] | undefined) => [...new Set((keys ?? []).filter((k) => BY_KEY[k]))]
  const sections = (saved?.length ? saved : DEFAULT_SECTIONS).map((s) => ({
    key: s.key, name_ro: s.name_ro, name_ru: s.name_ru, icon: s.icon, items: clean(s.items), reports: clean(s.reports),
  }))
  const placed = new Set(sections.flatMap(sectionKeys))
  for (const home of DEFAULT_SECTIONS) {
    for (const group of GROUPS) {
      for (const key of home[group]) {
        if (placed.has(key) || !BY_KEY[key]) continue
        let target = sections.find((s) => s.key === home.key)
        if (!target) {
          target = { ...home, items: [], reports: [] }
          // înaintea primei secțiuni implicite de după ea care e în meniu (altfel la sfârșit)
          const after = DEFAULT_SECTIONS.slice(DEFAULT_SECTIONS.indexOf(home) + 1).map((d) => sections.findIndex((s) => s.key === d.key)).find((i) => i >= 0)
          sections.splice(after ?? sections.length, 0, target)
        }
        target[group].push(key)
        placed.add(key)
      }
    }
  }
  return sections
}

/** Funcțiile din program care nu sunt nicăieri în meniu (editorul le arată la „Funcții neafișate”). */
export function hiddenItems(sections: MenuSection[]): NavItem[] {
  const placed = new Set(sections.flatMap(sectionKeys))
  return ALL_ITEMS.filter((i) => !placed.has(i.key))
}

export function useSectionName() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language
  // aceeași funcție cât nu se schimbă limba: altfel meniul principal (useMainMenu) s-ar reface la fiecare desenare
  return useCallback((s: MenuSection) => (lang === 'ru' ? s.name_ru || s.name_ro : s.name_ro || s.name_ru)
    || t(`menuSections.${s.key}`, { defaultValue: s.key }), [t, lang])
}

/** Unde stau secțiunile meniului principal: sus (grupele secțiunii alese în stânga, ca în 1C) sau în stânga (tot arborele). */
export type MenuSide = 'top' | 'left'

/** Așezarea meniului: a utilizatorului (preferința „menu”), altfel cea pusă de administrator pentru toți (Meniul principal). */
export function useMenuSide(): [MenuSide, (side: MenuSide) => void, MenuSide] {
  const { data } = useFetch<{ layout?: MenuSide }>('/settings/menu/')
  const [mine, save] = useUiPref<{ layout?: MenuSide }>('menu')
  const def: MenuSide = data?.layout === 'left' ? 'left' : 'top'
  const side: MenuSide = mine?.layout === 'left' || mine?.layout === 'top' ? mine.layout : def
  return [side, (s) => save({ layout: s }), def]
}

export interface MenuSectionView extends MenuSection {
  label: string
  iconNode: React.ReactNode
  /** grupele cu funcțiile pe care le are utilizatorul (grupa goală rămâne, ca structura să se vadă) */
  groups: { key: MenuGroup; navItems: NavItem[] }[]
  /** funcțiile secțiunii, în ordinea grupelor, fiecare o singură dată */
  navItems: NavItem[]
}

/** Cheia unui rând de meniu: secțiunea, grupa și adresa (aceeași funcție poate fi în mai multe locuri). */
export const menuKey = (sectionKey: string, group: string, path: string) => `m|${sectionKey}|${group}|${path}`
export const pathOfKey = (key: string) => (key.startsWith('m|') ? key.split('|').slice(3).join('|') : key)

/** Meniul principal al utilizatorului: secțiunile cu funcțiile pe care le are (drepturi + bifele de meniu din roluri). */
export function useMainMenu(): MenuSectionView[] {
  return useMainMenuState().sections
}

/** Meniul principal și dacă a venit meniul salvat de la server (până atunci — așezarea implicită). */
export function useMainMenuState(): { sections: MenuSectionView[]; ready: boolean } {
  const { me, hasPerm, branding } = useApp()
  const { data, error } = useFetch<{ sections?: MenuSection[] }>('/settings/menu/')
  const name = useSectionName()
  const hasSettings = useVisibleSettings().length > 0
  const sections = useMemo(() => {
    const hidden = new Set(me?.menu_hidden ?? [])
    if (!hasSettings) hidden.add('settings')
    // cine are doar cabinetul (rolul „Angajat”) nu are panou de start și termene — totul e în „Cabinetul meu”
    if (!me?.is_admin && hasPerm('portal.view') && !hasPerm('employees.view')) ['dashboard', 'alerts'].forEach((k) => hidden.add(k))
    const visible = (keys: string[]) => keys.map((k) => BY_KEY[k]).filter((i) => i && !hidden.has(i.key) && (!i.perm || hasPerm(i.perm))
      && !moduleOff(branding, i.key))
    return completeSections(data?.sections)
      .filter((s) => !hidden.has(`s:${s.key}`))
      .map((s) => {
        const groups = GROUPS.map((g) => ({ key: g, navItems: visible(s[g]) }))
        const navItems = [...new Set(groups.flatMap((g) => g.navItems))]
        return { ...s, label: name(s), iconNode: SECTION_ICONS[s.icon] ?? SECTION_ICONS.folder, groups, navItems }
      })
      .filter((s) => s.navItems.length > 0)
  }, [data, me, hasPerm, name, branding, hasSettings])
  return { sections, ready: data !== null || !!error }
}

/** Panoul funcțiilor e pornit (Constante → Module) și ecranul e lat: secțiunile stau sus ca file, fiecare cu panoul ei, fără
 *  meniul din stânga. Pe telefon meniul rămâne cel obișnuit (sertarul). */
export function useFunctionPanel(): boolean {
  const { branding } = useApp()
  const screens = Grid.useBreakpoint()
  return !!branding?.function_panel && !!screens.lg
}

export const panelPath = (sectionKey: string) => `/panel/${sectionKey}`

/** Ce arată panoul unei secțiuni. */
export interface SectionPanelView {
  /** blocul de sus: documentele (Schema de lucru), paginile de început, ori — în secțiunea fără documente — registrele */
  top: 'schema' | 'start' | 'items'
  tiles: NavItem[]
  /** săgeata de la iconița i la i+1 (documentul al doilea se face din primul) */
  linked: boolean[]
  registers: NavItem[]
  classifiers: NavItem[]
  reports: NavItem[]
  /** Administrare: funcțiile ca în meniu, neîmpărțite pe blocuri */
  plain: boolean
}

/** Panoul secțiunii, din funcțiile pe care le vede utilizatorul în ea (aceleași drepturi și bife de rol ca meniul) și din
 *  clasificatoarele acestor funcții pe care le vede la Setări. */
export function useSectionPanel(section: MenuSectionView | undefined): SectionPanelView | null {
  const settings = useVisibleSettings()
  const { t, i18n } = useTranslation()
  return useMemo(() => {
    if (!section) return null
    const items = section.groups.find((g) => g.key === 'items')?.navItems ?? []
    const reports = section.groups.find((g) => g.key === 'reports')?.navItems ?? []
    if (section.key === 'administrare') {
      return { top: 'items', tiles: [], linked: [], registers: section.navItems, classifiers: [], reports: [], plain: true }
    }
    let tiles = items.filter((i) => PANEL_KIND[i.key])
    let registers = items.filter((i) => !PANEL_KIND[i.key])
    const top = tiles.some((i) => PANEL_KIND[i.key] === 'doc') ? 'schema' : tiles.length ? 'start' : 'items'
    if (!tiles.length) [tiles, registers] = [registers, []]
    // documentul de bază înaintea celui făcut din el
    for (const [from, to] of PANEL_FLOWS) {
      const a = tiles.findIndex((i) => i.key === from)
      const b = tiles.findIndex((i) => i.key === to)
      if (a > b && b >= 0) tiles.splice(b, 0, ...tiles.splice(a, 1))
    }
    const linked = tiles.slice(0, -1).map((item, n) => PANEL_FLOWS.some(([from, to]) => from === item.key && to === tiles[n + 1].key))
    const wanted = new Set([...items, ...reports].flatMap((i) => PANEL_CLASSIFIERS[i.key] ?? []))
    const classifiers = settings.filter((s) => wanted.has(s.key))
      .sort((a, b) => navLabel(t, a).localeCompare(navLabel(t, b), i18n.language))
    return { top, tiles, linked, registers, classifiers, reports, plain: false }
  }, [section, settings, t, i18n.language])
}

/** Clasificatoarele fiecărei secțiuni (aceleași ca la Clasificatoare din Panoul funcțiilor: ale funcțiilor secțiunii pe
 *  care utilizatorul le vede la Setări), pentru submeniul „Clasificatoare” al barei de meniu clasice. */
export function useSectionClassifiers(sections: MenuSectionView[]): Record<string, NavItem[]> {
  const settings = useVisibleSettings()
  const { t, i18n } = useTranslation()
  return useMemo(() => Object.fromEntries(sections.map((sec) => {
    const wanted = new Set(sec.navItems.flatMap((i) => PANEL_CLASSIFIERS[i.key] ?? []))
    const items = settings.filter((s) => wanted.has(s.key)).sort((a, b) => navLabel(t, a).localeCompare(navLabel(t, b), i18n.language))
    return [sec.key, items]
  })), [sections, settings, t, i18n.language])
}

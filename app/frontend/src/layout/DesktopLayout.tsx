import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Drawer, Grid, Menu, Tooltip } from 'antd'
import type { MenuProps } from 'antd'
import {
  AppstoreOutlined, ArrowLeftOutlined, ArrowRightOutlined, BgColorsOutlined, CloseOutlined, DatabaseOutlined, FileAddOutlined,
  FileExcelOutlined, HomeOutlined, InfoCircleOutlined, LogoutOutlined, MenuOutlined, PrinterOutlined, QuestionCircleOutlined,
  ReloadOutlined, SaveOutlined, SearchOutlined, StarFilled, StarOutlined, TranslationOutlined, UserOutlined,
} from '@ant-design/icons'

import { connectionState } from '../api/client'
import { PageScope, PageScopeContext } from '../api/pageScope'
import { LANG_LABELS } from '../api/types'
import { useApp, useLocalName } from '../auth/AppContext'
import HelpDrawer from '../components/HelpDrawer'
import LicenseBanner from '../components/LicenseBanner'
import NotificationsBell from '../components/NotificationsBell'
import OnlineNow from '../components/OnlineNow'
import { PRODUCT } from '../product'
import { PALETTES, type ThemeChoice, type ThemeName } from '../theme/themes'
import MenuBar, { type MenuDef, type MenuEntry } from './desktop/MenuBar'
import { useFavorites } from './favorites'
import { itemOfPath, panelPath, ROUTE_ITEMS, useSectionClassifiers, type MenuSectionView } from './menu'
import { movedTo, navLabel, type NavItem } from './nav'
import { helpKeyFor, screenTitleOf, useHelpKey, useHistoryNav, usePlatform, useSectionChoice } from './shell'
import { TabsProvider, useTabs } from './tabs'
import WindowKeys, { showOpenWindows } from './windowKeys'

/**
 * Aspectul „Clasic de birou” (temele desktop / desktop_dark): programul arată ca o aplicație de birou, nu ca un site —
 * sus bara de titlu („CAI CADRE — întreprinderea”), bara de meniu (Fișier, secțiunile meniului principal, Ferestre,
 * Ajutor), bara de unelte; dedesubt ferestrele deschise ca file (MDI), fereastra activă și, jos, bara de stare.
 * Meniul vine din același meniu principal (useMainMenu: drepturile, bifele rolurilor, modulele oprite), deci arată exact
 * ce arată și meniul lateral. Pe telefon bara de meniu se strânge în „☰”, iar bara de unelte și cea de stare se reduc.
 */
export default function DesktopLayout() {
  return (
    <TabsProvider>
      <DesktopShell />
    </TabsProvider>
  )
}

const HOME = '/'
const THEMES: ThemeChoice[] = ['desktop', 'desktop_dark', 'green', 'turquoise', 'blue', 'dark', 'onec', 'auto']

type DomCommand = 'new' | 'print' | 'excel' | 'search'

const visible = (el: HTMLElement) => el.getClientRects().length > 0
const usable = (el: HTMLElement | null): el is HTMLElement =>
  !!el && visible(el) && !(el as HTMLButtonElement).disabled && el.getAttribute('aria-disabled') !== 'true'
  && !el.closest('.ant-table-tbody, .ant-table-summary, .ant-btn-loading')

/** Butonul ferestrei care face comanda: întâi cel marcat de componentele comune (data-cmd), apoi cel după iconița lui. */
function findCommand(root: HTMLElement, cmd: DomCommand): HTMLElement | null {
  const marked = Array.from(root.querySelectorAll<HTMLElement>(`[data-cmd="${cmd}"]`)).find(usable)
  if (marked) return marked
  const byIcon = (icon: string, button: string) => Array.from(root.querySelectorAll<HTMLElement>(icon))
    .map((i) => i.closest<HTMLElement>(button)).find(usable) ?? null
  switch (cmd) {
    // „Nou” al ferestrei: butonul principal cu „+” (Angajat nou, Ordin nou, Adaugă …); nu „+” de pe rânduri
    case 'new': return byIcon('.ant-btn-primary .anticon-plus', '.ant-btn')
    // „Tipar” al ferestrei: butonul cu imprimanta (deschide dialogul de tipărire al ferestrei)
    case 'print': return byIcon('.ant-btn .anticon-printer', '.ant-btn')
    case 'excel': return null
    // câmpul de căutare al ferestrei
    case 'search': {
      const fields = [
        ...Array.from(root.querySelectorAll<HTMLElement>('.ant-input-search input')),
        ...Array.from(root.querySelectorAll<HTMLElement>('.ant-input-affix-wrapper .anticon-search'))
          .map((i) => i.closest('.ant-input-affix-wrapper')?.querySelector<HTMLElement>('input')).filter((x): x is HTMLElement => !!x),
      ]
      return fields.find((el) => visible(el) && !(el as HTMLInputElement).disabled && !el.closest('.ant-table-thead')) ?? null
    }
  }
}

/** Ce comenzi ale barei de unelte are fereastra deschisă (se urmăresc schimbările din fereastră). */
function useDomCommands(root: React.RefObject<HTMLElement | null>, routeKey: string) {
  const [has, setHas] = useState<Record<DomCommand, boolean>>({ new: false, print: false, excel: false, search: false })
  useEffect(() => {
    const el = root.current
    if (!el) return
    let frame = 0
    const scan = () => {
      frame = 0
      const next = {
        new: !!findCommand(el, 'new'), print: !!findCommand(el, 'print'), excel: !!findCommand(el, 'excel'), search: !!findCommand(el, 'search'),
      }
      setHas((cur) => (cur.new === next.new && cur.print === next.print && cur.excel === next.excel && cur.search === next.search ? cur : next))
    }
    const later = () => { if (!frame) frame = requestAnimationFrame(scan) }
    scan()
    const observer = new MutationObserver(later)
    observer.observe(el, { subtree: true, childList: true, attributes: true, attributeFilter: ['disabled', 'class', 'style', 'hidden'] })
    return () => {
      observer.disconnect()
      if (frame) cancelAnimationFrame(frame)
    }
  }, [root, routeKey])
  const run = useCallback((cmd: DomCommand) => {
    const el = root.current && findCommand(root.current, cmd)
    if (!el) return
    if (cmd === 'search') {
      el.focus()
      ;(el as HTMLInputElement).select?.()
      return
    }
    // listele derulante deschise la trecerea mouse-ului (Tipar → documentul) se deschid și de aici
    el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
    el.click()
  }, [root])
  return { has, run }
}

function ToolButton({ icon, title, disabled, onClick, className }: {
  icon: ReactNode; title: string; disabled?: boolean; onClick: () => void; className?: string
}) {
  return (
    <Tooltip title={title} mouseEnterDelay={0.5}>
      <span className="dk-tool-wrap">
        <button type="button" className={`dk-tool ${className ?? ''}`} disabled={disabled} onClick={onClick} aria-label={title}>{icon}</button>
      </span>
    </Tooltip>
  )
}

const Sep = () => <span className="dk-tool-sep" aria-hidden />

function DesktopShell() {
  const { t } = useTranslation()
  const { me, logout, companyName, branding, themeName, themeChoice, setThemeChoice, lang, setLang, languages } = useApp()
  const localName = useLocalName()
  const platform = usePlatform()
  const location = useLocation()
  const navigate = useNavigate()
  const screens = Grid.useBreakpoint()
  const mobile = !screens.lg
  const [drawer, setDrawer] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const { canBack, canForward } = useHistoryNav()
  const moved = movedTo(location.pathname, location.search)
  const { tabs, close, closeAll } = useTabs()
  const { favorites, isFavorite, toggle: toggleFavorite } = useFavorites()
  const { sections, fnPanel, current, active } = useSectionChoice()
  const classifiers = useSectionClassifiers(sections)
  useHelpKey(useCallback(() => setHelpOpen(true), []))

  // fereastra activă: comenzile ei (Salvează, Reîmprospătează din mecanismele comune; Nou, Tipar, Excel, Căutare — butoanele ei)
  const scope = useMemo(() => new PageScope(), [])
  const page = useSyncExternalStore(scope.subscribe, scope.snapshot)
  const content = useRef<HTMLElement>(null)
  const { has, run } = useDomCommands(content, location.key)
  // forma își arată singură „Salvat” sau greșelile (ca la butonul ei „Salvează”)
  const save = useCallback(() => {
    if (scope.snapshot().dirty) scope.save()
  }, [scope])
  const refresh = useCallback(() => {
    if (!scope.snapshot().dirty) scope.reload()
  }, [scope])
  // Ctrl+S — salvează fereastra activă (în loc de „Salvează pagina” a browserului)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && e.code === 'KeyS') {
        e.preventDefault()
        save()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [save])

  const screenTitle = screenTitleOf(t, location.pathname, sections, current)
  const windowTitle = `${PRODUCT.name} — ${companyName}`
  useEffect(() => {
    const old = document.title
    document.title = windowTitle
    return () => { document.title = old }
  }, [windowTitle])

  // fila ferestrei deschise (pagina de start nu e filă)
  const activePath = location.pathname === HOME ? HOME : tabs.find((x) => x.path.split('?')[0] === location.pathname)?.path ?? null
  const activeTab = tabs.find((x) => x.path === activePath)
  const starred = !!activeTab && isFavorite(activeTab.path)

  // ---------------------------------------------------------------- bara de meniu
  const go = useCallback((path: string) => navigate(path), [navigate])
  const itemEntry = (i: NavItem, prefix: string): MenuEntry => ({
    kind: 'item', key: `${prefix}:${i.path}`, label: navLabel(t, i), icon: i.icon, onSelect: () => go(i.path),
    disabled: !!i.stage,
  })
  const byKey = useMemo(() => Object.fromEntries(ROUTE_ITEMS.map((i) => [i.key, i])), [])
  const favoriteEntries: MenuEntry[] = favorites.map((f) => {
    const item = (f.key && byKey[f.key]) || (f.title ? undefined : itemOfPath(ROUTE_ITEMS, f.path))
    return { kind: 'item', key: `fav:${f.path}`, label: item ? navLabel(t, item) : f.title || f.path, icon: item?.icon ?? <StarOutlined />,
      onSelect: () => go(f.path) }
  })
  const principal = sections.find((s) => s.key === 'principal')
  const sectionMenus = sections.filter((s) => s !== principal)
  const sep = (key: string): MenuEntry => ({ kind: 'sep', key })
  const sectionItems = (sec: MenuSectionView): MenuEntry[] => {
    const own = sec.groups.find((g) => g.key === 'items')?.navItems ?? []
    const reports = sec.groups.find((g) => g.key === 'reports')?.navItems ?? []
    const dicts = classifiers[sec.key] ?? []
    const out: MenuEntry[] = []
    // cu Panoul funcțiilor: panoul secțiunii e primul rând al meniului ei (în loc de rândul de file de sub antet)
    if (fnPanel) out.push({ kind: 'item', key: `panel:${sec.key}`, label: t('fnPanel.title'), icon: <AppstoreOutlined />,
      onSelect: () => go(panelPath(sec.key)) }, sep(`s0:${sec.key}`))
    out.push(...own.map((i) => itemEntry(i, sec.key)))
    if (reports.length) {
      if (out.length) out.push(sep(`s1:${sec.key}`))
      out.push(...reports.map((i) => itemEntry(i, `${sec.key}:r`)))
    }
    if (dicts.length) {
      out.push(sep(`s2:${sec.key}`), {
        kind: 'sub', key: `dicts:${sec.key}`, label: t('fnPanel.classifiers'), icon: <DatabaseOutlined />,
        items: dicts.map((i) => itemEntry(i, `${sec.key}:d`)),
      })
    }
    return out
  }
  const themeEntries: MenuEntry[] = THEMES.map((v) => ({
    kind: 'item', key: `theme:${v}`, label: t(`themes.${v}`), checked: (themeChoice || '') === v
      || (!themeChoice && v === (branding?.default_theme as ThemeName | undefined)), onSelect: () => setThemeChoice(v),
  }))
  const fileMenu: MenuDef = {
    key: 'file', label: t('desk.menu.file'),
    items: [
      { kind: 'item', key: 'home', label: t('tabs.home'), icon: <HomeOutlined />, onSelect: () => go(HOME) },
      ...(principal?.navItems.filter((i) => i.path !== HOME).map((i) => itemEntry(i, 'principal')) ?? []),
      sep('f1'),
      { kind: 'sub', key: 'favorites', label: t('tabs.favorites'), icon: <StarFilled style={{ color: '#E0A100' }} />,
        items: favoriteEntries.length ? favoriteEntries : [{ kind: 'item', key: 'none', label: t('desk.noFavorites'), disabled: true, onSelect: () => undefined }] },
      { kind: 'item', key: 'star', label: t(starred ? 'tabs.unstar' : 'tabs.star'), icon: starred ? <StarFilled /> : <StarOutlined />,
        disabled: !activeTab, onSelect: () => activeTab && toggleFavorite({ path: activeTab.path.split('?')[0], key: '', title: activeTab.title }) },
      sep('f2'),
      { kind: 'item', key: 'profile', label: t('header.profile'), icon: <UserOutlined />, onSelect: () => go('/profile') },
      { kind: 'sub', key: 'theme', label: t('header.theme'), icon: <BgColorsOutlined />, items: themeEntries },
      ...(languages.length > 1 ? [{ kind: 'sub' as const, key: 'lang', label: t('profile.language'), icon: <TranslationOutlined />,
        items: languages.map((l): MenuEntry => ({ kind: 'item', key: `lang:${l}`, label: LANG_LABELS[l], checked: lang === l, onSelect: () => setLang(l) })) }] : []),
      ...(platform ? [{ kind: 'item' as const, key: 'base', label: t('header.switchBase'), icon: <DatabaseOutlined />,
        onSelect: () => { window.location.href = '/__platform/' } }] : []),
      sep('f3'),
      { kind: 'item', key: 'logout', label: t('header.logout'), icon: <LogoutOutlined />, onSelect: logout },
    ],
  }
  const windowList: MenuEntry[] = [{ path: HOME, title: t('tabs.home') }, ...tabs].map((x, i) => ({
    kind: 'item', key: `win:${x.path}`, label: x.title, checked: x.path === (activePath ?? ''), shortcut: i < 9 ? `${i + 1}` : undefined,
    onSelect: () => go(x.path),
  }))
  const windowsMenu: MenuDef = {
    key: 'windows', label: t('desk.menu.windows'),
    items: [
      { kind: 'item', key: 'list', label: `${t('tabs.windows')}…`, icon: <AppstoreOutlined />, shortcut: 'Alt+`', onSelect: showOpenWindows },
      { kind: 'item', key: 'close', label: t('desk.closeWindow'), icon: <CloseOutlined />, shortcut: 'Esc', disabled: !activeTab,
        onSelect: () => activeTab && close(activeTab.path) },
      { kind: 'item', key: 'closeAll', label: t('tabs.closeAll'), disabled: tabs.length === 0, onSelect: closeAll },
      sep('w1'),
      { kind: 'item', key: 'back', label: t('header.back'), icon: <ArrowLeftOutlined />, shortcut: 'Alt+←', disabled: !canBack, onSelect: () => navigate(-1) },
      { kind: 'item', key: 'forward', label: t('header.forward'), icon: <ArrowRightOutlined />, shortcut: 'Alt+→', disabled: !canForward, onSelect: () => navigate(1) },
      sep('w2'),
      ...windowList,
    ],
  }
  const helpMenu: MenuDef = {
    key: 'help', label: t('desk.menu.help'),
    items: [
      { kind: 'item', key: 'screen', label: t('header.help'), icon: <QuestionCircleOutlined />, shortcut: 'F1', onSelect: () => setHelpOpen(true) },
      sep('h1'),
      { kind: 'item', key: 'about', label: t('about.menu'), icon: <InfoCircleOutlined />, onSelect: () => go('/about') },
    ],
  }
  const menus: MenuDef[] = [
    fileMenu,
    ...sectionMenus.map((sec) => ({ key: sec.key, label: sec.label, items: sectionItems(sec), current: sec.key === current?.key })),
    windowsMenu,
    helpMenu,
  ]

  // ---------------------------------------------------------------- telefonul: meniul „☰”
  const drawerItems: MenuProps['items'] = [
    { key: HOME, icon: <HomeOutlined />, label: t('tabs.home') },
    ...sections.map((sec) => ({
      key: `s:${sec.key}`, icon: sec.iconNode, label: sec.label,
      children: [
        ...(fnPanel ? [{ key: panelPath(sec.key), icon: <AppstoreOutlined />, label: t('fnPanel.title') }] : []),
        ...sec.navItems.filter((i) => i.path !== HOME).map((i) => ({ key: i.path, icon: i.icon, label: navLabel(t, i), disabled: !!i.stage })),
        ...((classifiers[sec.key] ?? []).length ? [{ type: 'group' as const, key: `d:${sec.key}`, label: t('fnPanel.classifiers'),
          children: (classifiers[sec.key] ?? []).map((i) => ({ key: i.path, icon: i.icon, label: navLabel(t, i) })) }] : []),
      ],
    })),
    ...(favorites.length ? [{ key: 's:fav', icon: <StarFilled style={{ color: '#E0A100' }} />, label: t('tabs.favorites'),
      children: favorites.map((f) => {
        const item = (f.key && byKey[f.key]) || (f.title ? undefined : itemOfPath(ROUTE_ITEMS, f.path))
        return { key: f.path, icon: item?.icon ?? <StarOutlined />, label: item ? navLabel(t, item) : f.title || f.path }
      }) }] : []),
    { type: 'divider' },
    { key: '/profile', icon: <UserOutlined />, label: t('header.profile') },
    { key: 's:theme', icon: <BgColorsOutlined />, label: t('header.theme'),
      children: THEMES.map((v) => ({ key: `theme:${v}`, label: `${(themeChoice || '') === v ? '✓ ' : ''}${t(`themes.${v}`)}` })) },
    ...(languages.length > 1 ? [{ key: 's:lang', icon: <TranslationOutlined />, label: t('profile.language'),
      children: languages.map((l) => ({ key: `lang:${l}`, label: `${lang === l ? '✓ ' : ''}${LANG_LABELS[l]}` })) }] : []),
    { key: 'help', icon: <QuestionCircleOutlined />, label: t('header.help') },
    { key: '/about', icon: <InfoCircleOutlined />, label: t('about.menu') },
    { key: 'logout', icon: <LogoutOutlined />, label: t('header.logout'), danger: true },
  ]
  const onDrawerClick: MenuProps['onClick'] = ({ key }) => {
    setDrawer(false)
    if (key === 'logout') logout()
    else if (key === 'help') setHelpOpen(true)
    else if (key.startsWith('theme:')) setThemeChoice(key.slice(6) as ThemeChoice)
    else if (key.startsWith('lang:')) setLang(key.slice(5) as typeof lang)
    else navigate(key)
  }
  const [openKeys, setOpenKeys] = useState<string[]>([])
  // la deschidere — secțiunea paginii curente desfăcută (după cheie: obiectele secțiunilor se refac la fiecare desenare)
  const activeKey = active?.key
  useEffect(() => { if (drawer && activeKey) setOpenKeys([`s:${activeKey}`]) }, [drawer, activeKey])

  // ---------------------------------------------------------------- bara de stare
  const connection = useSyncExternalStore(connectionState.subscribe, connectionState.get)
  const roles = me?.roles.map((r) => localName(r)).filter(Boolean).join(', ') || (me?.is_admin ? t('desk.admin') : '')
  const logo = (PALETTES[themeName].dark && branding?.logo_dark) || branding?.logo_small || '/favicon.svg'

  return (
    <div className={`dk-shell${mobile ? ' is-mobile' : ''}`}>
      <header className="dk-titlebar">
        <img src={logo} alt="" />
        <span className="dk-title-text" title={windowTitle}>{mobile ? companyName : windowTitle}</span>
        {platform && platform.count > 1 && platform.base && <span className="dk-title-base">[{platform.base.name}]</span>}
      </header>
      {!mobile && <MenuBar menus={menus} label={t('desk.menuBar')} />}
      <div className="dk-toolbar" role="toolbar" aria-label={t('desk.toolbar')}>
        {mobile && <><ToolButton icon={<MenuOutlined />} title={t('desk.mobileMenu')} onClick={() => setDrawer(true)} /><Sep /></>}
        <ToolButton icon={<ArrowLeftOutlined />} title={`${t('header.back')} (Alt+←)`} disabled={!canBack} onClick={() => navigate(-1)} />
        {!mobile && <ToolButton icon={<ArrowRightOutlined />} title={`${t('header.forward')} (Alt+→)`} disabled={!canForward} onClick={() => navigate(1)} />}
        <ToolButton icon={<HomeOutlined />} title={t('header.home')} onClick={() => navigate(HOME)} className="tone-home" />
        <Sep />
        <ToolButton icon={<FileAddOutlined />} title={has.new ? t('desk.tool.new') : t('desk.tool.noNew')} disabled={!has.new} onClick={() => run('new')} className="tone-new" />
        <ToolButton icon={<SaveOutlined />} title={page.dirty ? `${t('desk.tool.save')} (Ctrl+S)` : t('desk.tool.noSave')} disabled={!page.dirty} onClick={save} className="tone-save" />
        <Sep />
        <ToolButton icon={<PrinterOutlined />} title={has.print ? t('desk.tool.print') : t('desk.tool.noPrint')} disabled={!has.print} onClick={() => run('print')} className="tone-print" />
        {!mobile && <ToolButton icon={<FileExcelOutlined />} title={has.excel ? t('desk.tool.excel') : t('desk.tool.noExcel')} disabled={!has.excel} onClick={() => run('excel')} className="tone-excel" />}
        <Sep />
        <ToolButton icon={<ReloadOutlined />} disabled={page.loaders === 0 || page.dirty} onClick={refresh} className="tone-refresh"
          title={page.loaders === 0 ? t('desk.tool.noRefresh') : page.dirty ? t('desk.tool.refreshDirty') : t('desk.tool.refresh')} />
        {!mobile && <ToolButton icon={<SearchOutlined />} title={has.search ? t('desk.tool.search') : t('desk.tool.noSearch')} disabled={!has.search} onClick={() => run('search')} />}
        <Sep />
        <ToolButton icon={<AppstoreOutlined />} title={`${t('tabs.windows')} (Alt+\`)`} onClick={showOpenWindows} className="tone-windows" />
        <span className="dk-tool-fill" />
        <ToolButton icon={<QuestionCircleOutlined />} title={`${t('header.help')} (F1)`} onClick={() => setHelpOpen(true)} className="tone-help" />
      </div>
      <MdiTabs />
      <main className="app-content dk-client" ref={content}>
        <LicenseBanner />
        <PageScopeContext.Provider value={scope}>
          {moved ? <Navigate to={moved} replace /> : <Outlet />}
        </PageScopeContext.Provider>
      </main>
      <footer className="dk-statusbar" aria-label={t('desk.statusBar')}>
        <span className={`dk-status-cell dk-conn is-${connection}`} title={t(`desk.status.${connection}`)}>
          <span className="dk-conn-dot" aria-hidden />{!mobile && t(`desk.status.${connection}`)}
        </span>
        <span className="dk-status-cell dk-status-user" title={me?.username}><UserOutlined /> {me?.full_name || me?.username}</span>
        {!mobile && roles && <span className="dk-status-cell" title={t('desk.status.role')}>{roles}</span>}
        <span className="dk-status-cell dk-status-grow" title={screenTitle}>{!mobile && screenTitle}</span>
        <span className="dk-status-cell dk-status-tool"><NotificationsBell /></span>
        <span className="dk-status-cell dk-status-tool dk-status-empty-hide"><OnlineNow /></span>
        {!mobile && <span className="dk-status-cell">{PRODUCT.name}{branding?.version ? ` ${branding.version}` : ''}</span>}
      </footer>
      <WindowKeys />
      <HelpDrawer open={helpOpen} onClose={() => setHelpOpen(false)} helpKey={helpKeyFor(location.pathname)} screen={screenTitle} />
      {mobile && (
        <Drawer open={drawer} onClose={() => setDrawer(false)} placement="left" size={290} title={PRODUCT.name}
          styles={{ body: { padding: 0 } }}>
          <Menu mode="inline" items={drawerItems} selectable={false} openKeys={openKeys} onOpenChange={setOpenKeys} onClick={onDrawerClick}
            style={{ borderInlineEnd: 0 }} />
        </Drawer>
      )}
    </div>
  )
}

/** Ferestrele deschise ca file de program (MDI): Pagina de start mereu prima, ✕ pe fiecare filă, steluța — favorite. */
function MdiTabs() {
  const { t } = useTranslation()
  const { tabs, close } = useTabs()
  const location = useLocation()
  const navigate = useNavigate()
  const strip = useRef<HTMLDivElement>(null)
  const active = location.pathname === HOME ? HOME : tabs.find((x) => x.path.split('?')[0] === location.pathname)?.path
  // fila activă se vede mereu (bara se derulează la ea)
  useEffect(() => {
    strip.current?.querySelector<HTMLElement>('.dk-mdi-tab.is-active')?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [active, tabs.length])
  const items = [{ path: HOME, title: t('tabs.home') }, ...tabs]
  return (
    <div className="dk-mdi" role="tablist" aria-label={t('tabs.windows')} ref={strip}>
      {items.map((x) => {
        const isActive = x.path === active
        return (
          <div key={x.path} role="tab" aria-selected={isActive} tabIndex={-1} title={x.title}
            className={`dk-mdi-tab${isActive ? ' is-active' : ''}`}
            onClick={() => { if (!isActive) navigate(x.path) }}
            onMouseDown={(e) => { if (e.button === 1 && x.path !== HOME) { e.preventDefault(); close(x.path) } }}>
            {x.path === HOME && <HomeOutlined />}
            <span className="dk-mdi-title">{x.title}</span>
            {x.path !== HOME && (
              <button type="button" className="dk-mdi-close" aria-label={`${t('desk.closeWindow')}: ${x.title}`} tabIndex={-1}
                onClick={(e) => { e.stopPropagation(); close(x.path) }}><CloseOutlined /></button>
            )}
          </div>
        )
      })}
    </div>
  )
}

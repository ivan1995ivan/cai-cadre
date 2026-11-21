import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Avatar, Button, Drawer, Dropdown, Grid, Layout, Menu, Segmented, Space, Tag, Tooltip, Typography } from 'antd'
import type { MenuProps } from 'antd'
import {
  ArrowLeftOutlined, ArrowRightOutlined, BgColorsOutlined, DatabaseOutlined, HomeOutlined, InfoCircleOutlined, LogoutOutlined, MenuOutlined, NodeIndexOutlined,
  QuestionCircleOutlined, UserOutlined, StarFilled, StarOutlined,
} from '@ant-design/icons'

import { useApp } from '../auth/AppContext'
import DevelopedBy from '../components/DevelopedBy'
import LicenseBanner from '../components/LicenseBanner'
import HelpDrawer from '../components/HelpDrawer'
import NotificationsBell from '../components/NotificationsBell'
import OnlineNow from '../components/OnlineNow'
import { isDesktopLook, PALETTES, type ThemeChoice } from '../theme/themes'
import type { Lang } from '../api/types'

export { ADMIN_NAV, NAV, SETTINGS_NAV, type NavItem } from './nav'
import { movedTo, navLabel, type NavItem } from './nav'
import { itemOfPath, menuKey, pathOfKey, ROUTE_ITEMS, useMenuSide, type MenuSectionView, type MenuSide } from './menu'
import { useFavorites } from './favorites'
import { OpenTabsBar, TabsProvider } from './tabs'
import WindowKeys from './windowKeys'
import DesktopLayout from './DesktopLayout'

export type { MenuSide } from './menu'
export { helpKeyFor } from './shell'
import { helpKeyFor, screenTitleOf, useHelpKey, useHistoryNav, usePlatform, useSectionChoice } from './shell'

/** Aspectul programului după tema folosită: program clasic de birou (DesktopLayout) sau meniul lateral (WebLayout). */
export default function AppLayout() {
  const { themeName } = useApp()
  return isDesktopLook(themeName) ? <DesktopLayout /> : <WebLayout />
}

function WebLayout() {
  const { t } = useTranslation()
  const { me, logout, companyName, branding, themeName, themeChoice, setThemeChoice, lang, setLang, languages } = useApp()
  const platform = usePlatform()
  const location = useLocation()
  const navigate = useNavigate()
  const screens = Grid.useBreakpoint()
  const mobile = !screens.lg
  const [collapsed, setCollapsed] = useState(false)
  const [drawer, setDrawer] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const dark = PALETTES[themeName].dark
  const { canBack, canForward } = useHistoryNav()
  const moved = movedTo(location.pathname, location.search)
  useHelpKey(useCallback(() => setHelpOpen(true), []))

  // Meniul principal ca în 1C: secțiunile sus și grupele secțiunii alese (Registre / Rapoarte / Setări) în stânga —
  // sau tot arborele în stânga, la alegere. Cu Panoul funcțiilor (Constante → Module): secțiunile sus ca file, fiecare
  // cu panoul ei (/panel/<secțiune>), fără meniul din stânga.
  const { sections, fnPanel, selectedItem, current, active, pickSection } = useSectionChoice()
  const [menuSide, setMenuSide] = useMenuSide()
  const sectionsLeft = !mobile && !fnPanel && menuSide === 'left'
  const { favorites, isFavorite, toggle: toggleFavorite } = useFavorites()
  const itemLabel = (item: NavItem) => {
    const starred = isFavorite(item.path)
    return (
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{navLabel(t, item)}</span>
        {item.stage && <Tag style={{ fontSize: 10, lineHeight: '16px', marginInlineEnd: 0 }}>{t('common.soon')}</Tag>}
        <Tooltip title={t(starred ? 'tabs.unstar' : 'tabs.star')}>
          <span role="button" aria-label="favorite" style={{ opacity: starred ? 1 : 0.3, color: starred ? '#f5a623' : undefined }}
            onClick={(e) => { e.stopPropagation(); toggleFavorite({ path: item.path, key: item.key, title: '' }) }}>
            {starred ? <StarFilled /> : <StarOutlined />}
          </span>
        </Tooltip>
      </span>
    )
  }
  const byKey = Object.fromEntries(ROUTE_ITEMS.map((i) => [i.key, i]))
  const favoritesMenu = favorites.length > 0 && (
    <>
      <Typography.Text type="secondary" style={{ display: 'block', padding: '12px 24px 6px', fontSize: 12, textTransform: 'uppercase' }}>
        <StarFilled style={{ color: '#f5a623' }} /> {t('tabs.favorites')}
      </Typography.Text>
      <Menu mode="inline" selectable={false} style={{ borderInlineEnd: 0 }} onClick={({ key }) => { navigate(key); setDrawer(false) }}
        items={favorites.map((f) => {
          // funcția sau setarea după cheie (serverul ține favoritele pe cheile și adresele de acum); pagina anume — după titlul ei
          const item = (f.key && byKey[f.key]) || (f.title ? undefined : itemOfPath(ROUTE_ITEMS, f.path))
          return { key: f.path, icon: item?.icon ?? <StarOutlined />, label: item ? navLabel(t, item) : f.title || f.path }
        })} />
    </>
  )
  // Panoul funcțiilor n-are meniul din stânga: favoritele sunt sub steluța din antet
  const favoritesDropdown: MenuProps = {
    items: favorites.map((f) => {
      const item = (f.key && byKey[f.key]) || (f.title ? undefined : itemOfPath(ROUTE_ITEMS, f.path))
      return { key: f.path, icon: item?.icon ?? <StarOutlined />, label: item ? navLabel(t, item) : f.title || f.path }
    }),
    onClick: ({ key }) => navigate(key),
  }
  // grupele secțiunii (Registre / Rapoarte / Setări) cu funcțiile lor; grupa fără funcții nu apare
  const groupItems = (sec: MenuSectionView): MenuProps['items'] => sec.groups.filter((g) => g.navItems.length > 0).map((g) => ({
    type: 'group' as const, key: `g:${sec.key}:${g.key}`, label: t(`menuGroups.${g.key}`),
    children: g.navItems.map((i) => ({ key: menuKey(sec.key, g.key, i.path), icon: i.icon, label: itemLabel(i) })),
  }))
  const sectionTree: MenuProps['items'] = sections.map((sec) => ({ key: `s:${sec.key}`, icon: sec.iconNode, label: sec.label, children: groupItems(sec) }))
  // în stânga: toate secțiunile, deschise pe rând (sau grupele secțiunii alese, când secțiunile stau sus)
  const menuItems: MenuProps['items'] = mobile || sectionsLeft ? sectionTree : active ? groupItems(active) : []
  // toate rândurile cu adresa funcției curente (poate fi în mai multe grupe / secțiuni)
  const selected = selectedItem
    ? sections.flatMap((sec) => sec.groups.flatMap((g) => g.navItems.filter((i) => i.path === selectedItem.path).map((i) => menuKey(sec.key, g.key, i.path))))
    : []
  // secțiunea paginii curente stă deschisă; celelalte se deschid / închid cu clic pe denumire
  const [openKeys, setOpenKeys] = useState<string[]>(() => (active ? [`s:${active.key}`] : []))
  const currentKey = current?.key
  useEffect(() => {
    if (currentKey) setOpenKeys((keys) => (keys.includes(`s:${currentKey}`) ? keys : [...keys, `s:${currentKey}`]))
  }, [currentKey])

  const logo = (dark && branding?.logo_dark) || branding?.logo_small || branding?.logo
  const brand = (
    <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '16px 20px', minHeight: 64 }}>
      <img src={logo || '/favicon.svg'} alt="" style={{ height: 32, maxWidth: collapsed && !mobile ? 32 : 160, objectFit: 'contain' }} />
      {(!collapsed || mobile) && !branding?.logo && (
        <Typography.Text strong ellipsis style={{ maxWidth: 150 }}>{companyName}</Typography.Text>
      )}
    </Link>
  )

  const menu = (
    <Menu
      mode="inline"
      items={menuItems}
      selectedKeys={selected}
      openKeys={openKeys}
      onOpenChange={setOpenKeys}
      onClick={({ key }) => {
        navigate(pathOfKey(key))
        setDrawer(false)
      }}
      style={{ borderInlineEnd: 0 }}
    />
  )

  const userMenu: MenuProps = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: t('header.profile') },
      { key: 'about', icon: <InfoCircleOutlined />, label: t('about.menu') },
      ...(platform ? [{ key: 'base', icon: <DatabaseOutlined />, label: t('header.switchBase') }] : []),
      { type: 'divider' },
      { key: 'logout', icon: <LogoutOutlined />, label: t('header.logout'), danger: true },
    ],
    onClick: ({ key }) => {
      if (key === 'logout') logout()
      else if (key === 'base') window.location.href = '/__platform/'
      else navigate(key === 'about' ? '/about' : '/profile')
    },
  }

  const themeMenu: MenuProps = {
    selectable: true,
    selectedKeys: [themeChoice || 'company', `menu:${menuSide}`],
    items: [
      { key: 'green', label: t('themes.green') },
      { key: 'turquoise', label: t('themes.turquoise') },
      { key: 'blue', label: t('themes.blue') },
      { key: 'dark', label: t('themes.dark') },
      { key: 'onec', label: t('themes.onec') },
      { key: 'auto', label: t('themes.auto') },
      ...(mobile || fnPanel ? [] : [
        { type: 'divider' as const },
        { key: 'menu:top', label: t('acc.menuTop') },
        { key: 'menu:left', label: t('acc.menuLeft') },
      ]),
    ],
    onClick: ({ key }) => (key.startsWith('menu:') ? setMenuSide(key.slice(5) as MenuSide) : setThemeChoice(key as ThemeChoice)),
  }

  return (
    <TabsProvider>
    <Layout style={{ minHeight: '100vh' }}>
      {mobile ? (
        <Drawer open={drawer} onClose={() => setDrawer(false)} placement="left" size={280} styles={{ body: { padding: 0 } }} title={null} closable={false}>
          {brand}
          {menu}
          {favoritesMenu}
          <div style={{ padding: '16px 0 20px', textAlign: 'center' }}><DevelopedBy size="small" /></div>
        </Drawer>
      ) : fnPanel ? null : (
        <Layout.Sider width={250} collapsible collapsed={collapsed} onCollapse={setCollapsed} theme={dark ? 'dark' : 'light'}
          style={{ borderInlineEnd: '1px solid var(--ant-color-border-secondary)', position: 'sticky', top: 0, height: '100vh', overflow: 'auto' }}>
          <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100%' }}>
          {brand}
          {!collapsed && active && !sectionsLeft && (
            <Typography.Text type="secondary" style={{ display: 'block', padding: '0 24px 6px', fontSize: 12, textTransform: 'uppercase' }}>
              {active.label}
            </Typography.Text>
          )}
          {menu}
          {!collapsed && favoritesMenu}
          <div style={{ marginTop: 'auto', padding: '16px 0 12px', textAlign: 'center' }}>
            <DevelopedBy size="small" iconOnly={collapsed} />
          </div>
          </div>
        </Layout.Sider>
      )}
      <Layout>
        <Layout.Header style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '0 16px', position: 'sticky', top: 0, zIndex: 10,
          borderBottom: '1px solid var(--ant-color-border-secondary)',
        }}>
          {mobile && <Button type="text" icon={<MenuOutlined />} onClick={() => setDrawer(true)} aria-label="menu" />}
          {fnPanel && (
            <Link to="/" style={{ display: 'flex', alignItems: 'center', marginInlineEnd: 4 }} aria-label={companyName}>
              <img src={logo || '/favicon.svg'} alt="" style={{ height: 30, maxWidth: 140, objectFit: 'contain' }} />
            </Link>
          )}
          <Space.Compact>
            <Tooltip title={t('header.home')}>
              <Button icon={<HomeOutlined />} type={location.pathname === '/' ? 'primary' : 'default'} onClick={() => navigate('/')} aria-label={t('header.home')} />
            </Tooltip>
            <Tooltip title={`${t('header.back')} (Alt+←)`}>
              <Button icon={<ArrowLeftOutlined />} disabled={!canBack} onClick={() => navigate(-1)} aria-label={t('header.back')} />
            </Tooltip>
            <Tooltip title={`${t('header.forward')} (Alt+→)`}>
              <Button icon={<ArrowRightOutlined />} disabled={!canForward} onClick={() => navigate(1)} aria-label={t('header.forward')} />
            </Tooltip>
          </Space.Compact>
          {fnPanel && favorites.length > 0 && (
            <Dropdown menu={favoritesDropdown} trigger={['click']}>
              <Button icon={<StarFilled style={{ color: '#f5a623' }} />}>{t('tabs.favorites')}</Button>
            </Dropdown>
          )}
          {mobile || sectionsLeft || fnPanel ? <div style={{ flex: 1 }} /> : (
            <Menu mode="horizontal" selectedKeys={active ? [active.key] : []} onClick={({ key }) => pickSection(key)}
              style={{ flex: 1, minWidth: 0, borderBottom: 0, background: 'transparent', lineHeight: '62px' }}
              items={sections.map((sec) => ({ key: sec.key, icon: sec.iconNode, label: sec.label }))} />
          )}
          {platform && platform.count > 1 && platform.base && (
            <Tooltip title={t('header.switchBase')}>
              <Tag icon={<DatabaseOutlined />} color="processing" style={{ cursor: 'pointer', marginInlineEnd: 0 }}
                onClick={() => { window.location.href = '/__platform/' }}>{platform.base.name}</Tag>
            </Tooltip>
          )}
          <Tooltip title={`${t('header.help')} (F1)`}>
            <Button type="text" icon={<QuestionCircleOutlined />} onClick={() => setHelpOpen(true)} aria-label={t('header.help')} />
          </Tooltip>
          <OnlineNow />
          <NotificationsBell />
          <Dropdown menu={themeMenu} trigger={['click']}>
            <Tooltip title={t('header.theme')}>
              <Button type="text" icon={<BgColorsOutlined />} aria-label={t('header.theme')} />
            </Tooltip>
          </Dropdown>
          {!mobile && languages.length > 1 && (
            <Segmented<Lang> size="small" value={lang} onChange={setLang} options={languages.map((l) => ({ label: l.toUpperCase(), value: l }))} />
          )}
          <Dropdown menu={userMenu} trigger={['click']}>
            <Button type="text" style={{ paddingInline: 4 }}>
              <Space>
                <Avatar size="small" icon={<UserOutlined />} />
                {!mobile && <span>{me?.full_name}</span>}
              </Space>
            </Button>
          </Dropdown>
        </Layout.Header>
        {fnPanel && (
          <nav className="fn-sections" aria-label={t('fnPanel.sections')}>
            {sections.map((sec) => (
              <button type="button" key={sec.key} className={`fn-section${sec.key === active?.key ? ' is-active' : ''}`}
                aria-current={sec.key === active?.key ? 'page' : undefined} onClick={() => pickSection(sec.key)}>
                {sec.iconNode}<span>{sec.label}</span>
              </button>
            ))}
          </nav>
        )}
        <Layout.Content className="app-content" style={{ padding: mobile ? 12 : 24 }}>
          <LicenseBanner />
          {moved ? <Navigate to={moved} replace /> : <Outlet />}
        </Layout.Content>
        <OpenTabsBar />
        <WindowKeys />
      </Layout>
      <HelpDrawer open={helpOpen} onClose={() => setHelpOpen(false)} helpKey={helpKeyFor(location.pathname)}
        screen={screenTitleOf(t, location.pathname, sections, current)} />
    </Layout>
    </TabsProvider>
  )
}

export function ComingSoon({ stage, title }: { stage?: number; title: string }) {
  const { t } = useTranslation()
  return (
    <div style={{ padding: 48, textAlign: 'center' }}>
      <NodeIndexOutlined style={{ fontSize: 48, opacity: 0.4 }} />
      <Typography.Title level={3}>{title}</Typography.Title>
      <Typography.Paragraph type="secondary">
        {stage !== undefined ? t('common.comingInStage', { stage }) : t('common.soon')}
      </Typography.Paragraph>
    </div>
  )
}

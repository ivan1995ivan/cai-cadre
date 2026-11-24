import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Route, RouterProvider, createBrowserRouter, createRoutesFromElements } from 'react-router-dom'
import { App as AntApp, ConfigProvider, Result, Spin } from 'antd'
import enUS from 'antd/locale/en_US'
import roRO from 'antd/locale/ro_RO'
import ruRU from 'antd/locale/ru_RU'
import axios from 'axios'

import { AppProvider, useApp } from './auth/AppContext'
import AppLayout, { ADMIN_NAV, ComingSoon, NAV, SETTINGS_NAV, type NavItem } from './layout/AppLayout'
import { DICT_KINDS, navLabel } from './layout/nav'
import SectionPanel from './layout/SectionPanel'
import SessionGuards from './components/SessionGuards'
import { buildTheme, isDesktopLook, PALETTES } from './theme/themes'
import Dashboard from './pages/Dashboard'
import AlertsPage, { AlertSettingsPage, SmtpSettingsPage } from './pages/AlertsPage'
import Login from './pages/Login'
import Profile from './pages/Profile'
import AboutPage from './pages/AboutPage'
import SetupWizard from './pages/setup/SetupWizard'
import Users from './pages/admin/Users'
import Roles from './pages/admin/Roles'
import Constants from './pages/admin/Constants'
import Currencies from './pages/admin/Currencies'
import Numbering from './pages/admin/Numbering'
import Audit from './pages/admin/Audit'
import Online from './pages/admin/Online'
import License from './pages/admin/License'
import PrintTemplates from './pages/admin/PrintTemplates'
import Maintenance from './pages/admin/Maintenance'
import MarkedObjects from './pages/admin/MarkedObjects'
import MenuEditor from './pages/admin/MenuEditor'
import SettingsPage from './pages/admin/SettingsPage'
import RequiredFields from './pages/admin/RequiredFields'
import Localities from './pages/admin/Localities'
import Banks from './pages/admin/Banks'
import OrgPage from './pages/org/OrgPage'
import DictionaryPage from './pages/org/DictionariesPage'
import StaffListsPage from './pages/org/StaffListsPage'
import StaffListEditor from './pages/org/StaffListEditor'
import OccupancyPage from './pages/org/OccupancyPage'
import EmployeesList from './pages/staff/EmployeesList'
import EmployeeCard from './pages/staff/EmployeeCard'
import ImportPage from './pages/admin/ImportPage'
import ContractsPage from './pages/staff/ContractsPage'
import OrdersList from './pages/orders/OrdersList'
import OrderEditor from './pages/orders/OrderEditor'
import RegisterPage from './pages/orders/RegisterPage'
import LeavePage, { LeaveSettingsPage } from './pages/leave/LeavePage'
import SchedulesPage from './pages/leave/SchedulesPage'
import ScheduleEditor from './pages/leave/ScheduleEditor'
import SickLeavePage from './pages/leave/SickLeavePage'
import WorktimeSettingsPage from './pages/worktime/WorktimePage'
import RostersPage from './pages/worktime/RostersPage'
import RosterEditor from './pages/worktime/RosterEditor'
import TimesheetsPage from './pages/worktime/TimesheetsPage'
import TimesheetEditor from './pages/worktime/TimesheetEditor'
import PayrollsPage from './pages/payroll/PayrollsPage'
import PayrollEditor from './pages/payroll/PayrollEditor'
import PayrollSettingsPage from './pages/payroll/PayrollSettingsPage'
import PaymentsPage from './pages/payroll/PaymentsPage'
import PaymentEditor from './pages/payroll/PaymentEditor'
import PayItemChangesPage, { PayItemChangeEditor } from './pages/payroll/PayItemChangesPage'
import MealVouchersPage, { MealVoucherEditor } from './pages/payroll/MealVouchersPage'
import TripsPage, { TripEditor } from './pages/transport/TripsPage'
import TransportSettingsPage from './pages/transport/TransportSettings'
import TachographPage from './pages/transport/TachographPage'
import TaxReportsPage, { TaxSettingsPage } from './pages/payroll/TaxReportsPage'
import ItParkPage, { ItParkMonthEditor } from './pages/payroll/ItParkPage'
import ProductionReportsPage, { ProductionReportEditor } from './pages/production/ProductionReportsPage'
import ProductionSettingsPage from './pages/production/ProductionSettings'
import ReportsPage from './pages/reports/ReportsPage'
import ReportView from './pages/reports/ReportView'
import TrainingPage from './pages/training/TrainingPage'
import HealthPage from './pages/health/HealthPage'
import MilitaryPage from './pages/military/MilitaryPage'
import PortalPage from './pages/portal/PortalPage'
import RequestsInbox from './pages/portal/RequestsInbox'

const ADMIN_PAGES: Record<string, React.ComponentType> = {
  settings: SettingsPage, audit: Audit, online: Online, license: License, maintenance: Maintenance, excelImport: ImportPage,
  markedObjects: MarkedObjects,
}

/** Pagina fiecărei setări (Administrare → Setări), după cheia din SETTINGS_NAV; `title` — denumirea din lista Setări. */
const SETTING_PAGES: Record<string, (title: string) => React.ReactNode> = {
  users: () => <Users />, roles: () => <Roles />, constants: () => <Constants />, currencies: () => <Currencies />,
  numbering: () => <Numbering />, printTemplates: () => <PrintTemplates />, mainMenu: () => <MenuEditor />,
  requiredFields: () => <RequiredFields />, localities: () => <Localities />, banks: () => <Banks />,
  occupations: (title) => <DictionaryPage dict="occupations" title={title} />,
  specialties: (title) => <DictionaryPage dict="specialties" title={title} />,
  legalBases: (title) => <DictionaryPage dict="legal" title={title} />,
  orderTypes: (title) => <DictionaryPage dict="order-types" title={title} />,
  ...Object.fromEntries(DICT_KINDS.map((kind) => [`dict:${kind}`, (title: string) => <DictionaryPage dict={kind} title={title} />])),
  workSchedules: (title) => <WorktimeSettingsPage part="schedules" title={title} />,
  shiftTypes: (title) => <WorktimeSettingsPage part="shifts" title={title} />,
  hourTypes: (title) => <WorktimeSettingsPage part="hourTypes" title={title} />,
  productionCalendar: (title) => <WorktimeSettingsPage part="calendar" title={title} />,
  worktimeSettings: (title) => <WorktimeSettingsPage part="settings" title={title} />,
  leaveSettings: (title) => <LeaveSettingsPage title={title} />,
  payrollTypes: (title) => <PayrollSettingsPage part="types" title={title} />,
  payrollConstants: (title) => <PayrollSettingsPage part="constants" title={title} />,
  taxSettings: (title) => <TaxSettingsPage title={title} />,
  tariffGrids: (title) => <ProductionSettingsPage part="grids" title={title} />,
  operations: (title) => <ProductionSettingsPage part="operations" title={title} />,
  brigades: (title) => <ProductionSettingsPage part="brigades" title={title} />,
  vehicles: (title) => <TransportSettingsPage part="vehicles" title={title} />,
  kmRates: (title) => <TransportSettingsPage part="kmRates" title={title} />,
  countries: (title) => <TransportSettingsPage part="countries" title={title} />,
  alertSettings: (title) => <AlertSettingsPage title={title} />,
  smtpSettings: (title) => <SmtpSettingsPage title={title} />,
}

/** O setare: pagina ei, cu denumirea din lista Setări ca titlu; o setare din SETTINGS_NAV fără pagină aici — „nu există”. */
function SettingRoute({ item }: { item: NavItem }) {
  const { t } = useTranslation()
  const page = SETTING_PAGES[item.key]
  return page ? <>{page(navLabel(t, item))}</> : <Result status="404" title={t('common.notFound')} />
}

// Modulele care au deja pagini proprii (restul arată „în curând”, cu etapa din PLAN.md).
const MODULE_ROUTES: { path: string; perm?: string; element: React.ReactNode }[] = [
  { path: 'org', perm: 'org.view', element: <OrgPage /> },
  { path: 'staff-list', perm: 'org.view', element: <StaffListsPage /> },
  { path: 'staff-list/occupancy', perm: 'org.view', element: <OccupancyPage /> },
  { path: 'staff-list/:id', perm: 'org.view', element: <StaffListEditor /> },
  { path: 'employees', perm: 'employees.view', element: <EmployeesList /> },
  { path: 'employees/:id', perm: 'employees.view', element: <EmployeeCard /> },
  { path: 'contracts', perm: 'employees.view', element: <ContractsPage /> },
  { path: 'orders', perm: 'orders.view', element: <OrdersList /> },
  { path: 'orders/register', perm: 'orders.view', element: <RegisterPage /> },
  { path: 'orders/:id', perm: 'orders.view', element: <OrderEditor /> },
  { path: 'leave', perm: 'leave.view', element: <LeavePage /> },
  { path: 'leave/schedule', perm: 'leave.view', element: <SchedulesPage /> },
  { path: 'leave/schedule/:id', perm: 'leave.view', element: <ScheduleEditor /> },
  { path: 'sick-leave', perm: 'sick_leave.view', element: <SickLeavePage /> },
  { path: 'worktime/rosters', perm: 'worktime.view', element: <RostersPage /> },
  { path: 'worktime/rosters/:id', perm: 'worktime.view', element: <RosterEditor /> },
  { path: 'timesheets', perm: 'worktime.view', element: <TimesheetsPage /> },
  { path: 'timesheets/:id', perm: 'worktime.view', element: <TimesheetEditor /> },
  { path: 'payroll', perm: 'payroll.view', element: <PayrollsPage /> },
  { path: 'payroll/payments', perm: 'payroll.view', element: <PaymentsPage /> },
  { path: 'payroll/payments/:id', perm: 'payroll.view', element: <PaymentEditor /> },
  { path: 'payroll/item-changes', perm: 'payroll.view', element: <PayItemChangesPage /> },
  { path: 'payroll/item-changes/:id', perm: 'payroll.view', element: <PayItemChangeEditor /> },
  { path: 'payroll/meal-vouchers', perm: 'payroll.view', element: <MealVouchersPage /> },
  { path: 'payroll/meal-vouchers/:id', perm: 'payroll.view', element: <MealVoucherEditor /> },
  { path: 'transport/trips', perm: 'transport.view', element: <TripsPage /> },
  { path: 'transport/trips/:id', perm: 'transport.view', element: <TripEditor /> },
  { path: 'transport/tachograph', perm: 'transport.view', element: <TachographPage /> },
  { path: 'production/reports', perm: 'production.view', element: <ProductionReportsPage /> },
  { path: 'production/reports/:id', perm: 'production.view', element: <ProductionReportEditor /> },
  { path: 'tax-reports', perm: 'tax_reports.view', element: <TaxReportsPage /> },
  { path: 'payroll/it-park', perm: 'tax_reports.view', element: <ItParkPage /> },
  { path: 'payroll/it-park/:year/:month', perm: 'tax_reports.view', element: <ItParkMonthEditor /> },
  { path: 'reports', perm: 'reports.view', element: <ReportsPage /> },
  // fără drept pe rută: fiecare raport are dreptul lui (evidența militară — military.view), verificat de server
  { path: 'reports/:key', element: <ReportView /> },
  { path: 'training', perm: 'training.view', element: <TrainingPage /> },
  { path: 'health', perm: 'health.view', element: <HealthPage /> },
  { path: 'military', perm: 'military.view', element: <MilitaryPage /> },
  { path: 'portal', perm: 'portal.view', element: <PortalPage /> },
  { path: 'employee-requests', perm: 'employees.view', element: <RequestsInbox /> },
  { path: 'payroll/:id', perm: 'payroll.view', element: <PayrollEditor /> },
]

const ANTD_LOCALES = { ro: roRO, ru: ruRU, en: enUS }

function Themed({ children }: { children: React.ReactNode }) {
  const { themeName, density, buttons, branding, lang } = useApp()
  const theme = buildTheme(themeName, density, branding?.primary_color || undefined, buttons)
  useEffect(() => {
    document.documentElement.dataset.theme = themeName // tema „Ca în 1C” are și reguli în styles.css
    // aspectul (program clasic de birou sau meniul lateral) și culorile (luminoase / întunecate), pentru regulile din styles.css
    document.documentElement.dataset.look = isDesktopLook(themeName) ? 'desktop' : 'web'
    document.documentElement.dataset.scheme = PALETTES[themeName].dark ? 'dark' : 'light'
    document.body.style.background = PALETTES[themeName].bg
    document.body.style.colorScheme = PALETTES[themeName].dark ? 'dark' : 'light'
    document.documentElement.dataset.buttons = buttons
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', String(theme.token?.colorPrimary))
    const button = theme.components?.Button as { colorPrimary?: string; colorPrimaryHover?: string } | undefined
    document.documentElement.style.setProperty('--crm-link-btn', String(button?.colorPrimary ?? theme.token?.colorPrimary))
    document.documentElement.style.setProperty('--crm-link-btn-hover', String(button?.colorPrimaryHover ?? theme.token?.colorPrimary))
  }, [themeName, buttons, theme.token?.colorPrimary, theme.components?.Button])
  return (
    <ConfigProvider theme={{ ...theme, cssVar: { prefix: 'ant' } }} locale={ANTD_LOCALES[lang] ?? roRO}>
      <AntApp>{children}</AntApp>
    </ConfigProvider>
  )
}

function Guarded({ perm, children }: { perm?: string; children: React.ReactNode }) {
  const { hasPerm } = useApp()
  const { t } = useTranslation()
  if (perm && !hasPerm(perm)) return <Result status="403" title={t('common.notAllowed')} />
  return <>{children}</>
}

/** Modulul care apare într-o etapă viitoare; titlul se traduce la afișare (rutele se fac o singură dată). */
function Soon({ item }: { item: NavItem }) {
  const { t } = useTranslation()
  return <ComingSoon stage={item.stage} title={t(`menu.${item.key}`)} />
}

/** Rutele aplicației. Routerul cu date (createBrowserRouter) e cerut de întrebarea „Salvați modificările?” din forme
 *  (useBlocker, vezi UnsavedGuard); se face o singură dată, drepturile se verifică la afișare (Guarded). */
function makeRouter() {
  return createBrowserRouter(createRoutesFromElements(
    <Route element={<><SessionGuards /><AppLayout /></>}>
      <Route index element={<Dashboard />} />
      <Route path="profile" element={<Profile />} />
      <Route path="alerts" element={<AlertsPage />} />
      <Route path="about" element={<AboutPage />} />
      <Route path="panel/:key" element={<SectionPanel />} />
      {MODULE_ROUTES.map((r) => (
        <Route key={r.path} path={r.path} element={<Guarded perm={r.perm}>{r.element}</Guarded>} />
      ))}
      {NAV.filter((n) => n.path !== '/' && n.stage).map((n) => (
        <Route key={n.path} path={`${n.path.slice(1)}/*`} element={<Guarded perm={n.perm}><Soon item={n} /></Guarded>} />
      ))}
      {SETTINGS_NAV.map((n) => (
        <Route key={n.path} path={n.path.slice(1)} element={<Guarded perm={n.perm}><SettingRoute key={n.path} item={n} /></Guarded>} />
      ))}
      {ADMIN_NAV.map((n) => {
        const Page = ADMIN_PAGES[n.key]
        return <Route key={n.path} path={n.path.slice(1)} element={<Guarded perm={n.perm}>{Page ? <Page /> : <Soon item={n} />}</Guarded>} />
      })}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>,
  ))
}

function Shell() {
  const { ready, me } = useApp()
  const router = useMemo(makeRouter, [])
  if (!ready) return <div style={{ display: 'grid', placeItems: 'center', height: '100vh' }}><Spin size="large" /></div>
  if (!me) return <Login />
  return <RouterProvider router={router} />
}

/** Primul pas: sistemul e instalat? Dacă nu, se deschide asistentul de instalare. */
function Root() {
  const [installed, setInstalled] = useState<boolean | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    axios
      .get('/api/setup/status/')
      .then((r) => setInstalled(r.data.installed))
      .catch(() => setFailed(true))
  }, [])
  if (failed) return <Result status="500" title="Serverul nu răspunde / Сервер не отвечает / Server not responding" />
  if (installed === null) return <div style={{ display: 'grid', placeItems: 'center', height: '100vh' }}><Spin size="large" /></div>
  return installed ? <Shell /> : <SetupWizard />
}

export default function App() {
  return (
    <AppProvider>
      <Themed>
        <Root />
      </Themed>
    </AppProvider>
  )
}

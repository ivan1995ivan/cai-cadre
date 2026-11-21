import type { ReactNode } from 'react'
import {
  ApartmentOutlined, AuditOutlined, BankOutlined, BarChartOutlined, BellOutlined, BookOutlined, CalendarOutlined, CheckSquareOutlined,
  ClearOutlined, ClockCircleOutlined, CloudServerOutlined, CloudUploadOutlined, DashboardOutlined, DollarOutlined, EnvironmentOutlined,
  FieldNumberOutlined, FileDoneOutlined, FileProtectOutlined, FileTextOutlined, HomeOutlined, IdcardOutlined, KeyOutlined, MailOutlined,
  MedicineBoxOutlined, MenuOutlined, OrderedListOutlined, PrinterOutlined, ProfileOutlined, ReadOutlined,
  SafetyCertificateOutlined, SafetyOutlined, ScheduleOutlined, SettingOutlined, SolutionOutlined, TableOutlined, TagsOutlined,
  TeamOutlined, UserOutlined, WalletOutlined, WifiOutlined,
} from '@ant-design/icons'

export interface NavItem {
  path: string
  key: string
  icon: ReactNode
  perm?: string
  stage?: number // modul care apare într-o etapă viitoare (PLAN.md)
  roofing?: boolean // (din CAI ERP) — nefolosit în CAI CADRE
  adminGroup?: boolean
  label?: string // cheia denumirii, dacă nu e `menu.<key>` (clasificatoarele mici: `org.dictKinds.<tip>`)
}

/** Denumirea funcției sau a setării, în limba interfeței. */
export const navLabel = (t: (key: string) => string, item: NavItem) => t(item.label ?? `menu.${item.key}`)

export const NAV: NavItem[] = [
  { path: '/', key: 'dashboard', icon: <DashboardOutlined /> },
  { path: '/alerts', key: 'alerts', icon: <BellOutlined /> },
  // Etapa 1: întreprinderea, subdiviziunile, statele de personal
  { path: '/org', key: 'org', icon: <ApartmentOutlined />, perm: 'org.view' },
  { path: '/staff-list', key: 'staffList', icon: <TableOutlined />, perm: 'org.view' },
  { path: '/staff-list/occupancy', key: 'occupancy', icon: <TeamOutlined />, perm: 'org.view' },
  // Etapa 2: angajații
  { path: '/employees', key: 'employees', icon: <TeamOutlined />, perm: 'employees.view' },
  { path: '/contracts', key: 'contracts', icon: <FileProtectOutlined />, perm: 'employees.view' },
  { path: '/employee-requests', key: 'employeeRequests', icon: <SolutionOutlined />, perm: 'employees.view' },
  // Etapa 3: ordinele
  { path: '/orders', key: 'orders', icon: <FileTextOutlined />, perm: 'orders.view' },
  { path: '/orders/register', key: 'ordersRegister', icon: <BookOutlined />, perm: 'orders.view' },
  // Etapa 4: concedii și timp de muncă
  { path: '/leave', key: 'leave', icon: <CalendarOutlined />, perm: 'leave.view' },
  { path: '/leave/schedule', key: 'leaveSchedule', icon: <ScheduleOutlined />, perm: 'leave.view' },
  { path: '/sick-leave', key: 'sickLeave', icon: <MedicineBoxOutlined />, perm: 'sick_leave.view' },
  { path: '/worktime/rosters', key: 'rosters', icon: <ScheduleOutlined />, perm: 'worktime.view' },
  { path: '/timesheets', key: 'timesheets', icon: <TableOutlined />, perm: 'worktime.view' },
  // Etapa 4b: salarizarea
  { path: '/payroll', key: 'payroll', icon: <WalletOutlined />, perm: 'payroll.view' },
  { path: '/payroll/payments', key: 'payrollPayments', icon: <DollarOutlined />, perm: 'payroll.view' },
  { path: '/payroll/item-changes', key: 'payItemChanges', icon: <ProfileOutlined />, perm: 'payroll.view' },
  { path: '/tax-reports', key: 'taxReports', icon: <FileDoneOutlined />, perm: 'tax_reports.view' },
  // Etapa 6: formare, sănătate, evidență militară
  { path: '/training', key: 'training', icon: <ReadOutlined />, perm: 'training.view' },
  { path: '/health', key: 'health', icon: <SafetyOutlined />, perm: 'health.view' },
  { path: '/military', key: 'military', icon: <SolutionOutlined />, perm: 'military.view' },
  // Rapoarte și cabinetul personal
  { path: '/reports', key: 'reports', icon: <BarChartOutlined />, perm: 'reports.view' },
  { path: '/portal', key: 'portal', icon: <IdcardOutlined />, perm: 'portal.view' },
]

export const ADMIN_NAV: NavItem[] = [
  { path: '/settings', key: 'settings', icon: <SettingOutlined /> },
  { path: '/admin/online', key: 'online', icon: <WifiOutlined />, perm: 'users.view' },
  { path: '/admin/import', key: 'excelImport', icon: <CloudUploadOutlined />, perm: 'imports.view' },
  { path: '/admin/audit', key: 'audit', icon: <AuditOutlined />, perm: 'audit.view' },
  { path: '/admin/maintenance', key: 'maintenance', icon: <CloudServerOutlined />, perm: 'settings.view' },
  { path: '/admin/marked', key: 'markedObjects', icon: <ClearOutlined />, perm: 'settings.view' },
  { path: '/admin/license', key: 'license', icon: <KeyOutlined />, perm: 'settings.view' },
]

/** Clasificatoarele mici (apps/org DictItem.KINDS), fiecare cu setarea lui; în adresă `_` devine `-`. */
export const DICT_KINDS = [
  'staff_category', 'education', 'education_form', 'document', 'family', 'marital', 'nationality', 'termination',
  'sanction', 'incentive', 'employment', 'military_group', 'military_rank', 'military_center', 'checklist',
]
export const dictPath = (kind: string) => `/dictionaries/${kind.replace(/_/g, '-')}`

/**
 * Setările, toate într-un singur loc (Administrare → Setări): nu stau în meniu, ci în lista paginii Setări, în ordine alfabetică
 * și cu căutare. Fiecare setare are pagina ei; paginile care aveau file cu setări (clasificatoarele, timpul de muncă,
 * salarizarea, concediile) s-au desfăcut în setări separate.
 */
export const SETTINGS_NAV: NavItem[] = [
  { path: '/admin/users', key: 'users', icon: <UserOutlined />, perm: 'users.view' },
  { path: '/admin/roles', key: 'roles', icon: <SafetyCertificateOutlined />, perm: 'roles.view' },
  { path: '/admin/constants', key: 'constants', icon: <HomeOutlined />, perm: 'settings.view' },
  { path: '/admin/currencies', key: 'currencies', icon: <DollarOutlined />, perm: 'settings.view' },
  { path: '/admin/numbering', key: 'numbering', icon: <FieldNumberOutlined />, perm: 'settings.view' },
  { path: '/admin/print-templates', key: 'printTemplates', icon: <PrinterOutlined />, perm: 'settings.view' },
  { path: '/admin/main-menu', key: 'mainMenu', icon: <MenuOutlined />, perm: 'settings.edit' },
  { path: '/admin/localities', key: 'localities', icon: <EnvironmentOutlined />, perm: 'settings.view' },
  { path: '/admin/banks', key: 'banks', icon: <BankOutlined />, perm: 'settings.view' },
  { path: '/admin/required-fields', key: 'requiredFields', icon: <CheckSquareOutlined />, perm: 'settings.view' },
  { path: '/dictionaries/occupations', key: 'occupations', icon: <TagsOutlined />, perm: 'dictionaries.view' },
  { path: '/dictionaries/specialties', key: 'specialties', icon: <TagsOutlined />, perm: 'dictionaries.view' },
  { path: '/dictionaries/legal', key: 'legalBases', icon: <TagsOutlined />, perm: 'dictionaries.view' },
  { path: '/dictionaries/order-types', key: 'orderTypes', icon: <TagsOutlined />, perm: 'dictionaries.view' },
  ...DICT_KINDS.map((kind) => ({ path: dictPath(kind), key: `dict:${kind}`, label: `org.dictKinds.${kind}`, icon: <TagsOutlined />,
    perm: 'dictionaries.view' })),
  { path: '/worktime/schedules', key: 'workSchedules', icon: <ScheduleOutlined />, perm: 'worktime.view' },
  { path: '/worktime/shifts', key: 'shiftTypes', icon: <ClockCircleOutlined />, perm: 'worktime.view' },
  { path: '/worktime/calendar', key: 'productionCalendar', icon: <CalendarOutlined />, perm: 'worktime.view' },
  { path: '/worktime/settings', key: 'worktimeSettings', icon: <ClockCircleOutlined />, perm: 'settings.edit' },
  { path: '/leave/settings', key: 'leaveSettings', icon: <CalendarOutlined />, perm: 'settings.edit' },
  { path: '/payroll/settings/types', key: 'payrollTypes', icon: <OrderedListOutlined />, perm: 'payroll_settings.view' },
  { path: '/payroll/settings/constants', key: 'payrollConstants', icon: <OrderedListOutlined />, perm: 'payroll_settings.view' },
  { path: '/tax-reports/settings', key: 'taxSettings', icon: <FileDoneOutlined />, perm: 'payroll_settings.edit' },
  { path: '/alerts/settings', key: 'alertSettings', icon: <BellOutlined />, perm: 'settings.edit' },
  { path: '/alerts/email', key: 'smtpSettings', icon: <MailOutlined />, perm: 'settings.edit' },
]

/**
 * Panoul funcțiilor (Constante → Module, ca în 1C). Funcțiile grupei Registre a unei secțiuni se împart: documentele
 * (`doc`) sunt iconițele „Schemei de lucru”, iar paginile de început (`start`, secțiunea Principal) iconițele „Începutului
 * lucrului”; restul (catalogul angajaților, registrul ordinelor, evidențele) stau la Registre. Ce nu e aici e registru.
 */
export const PANEL_KIND: Record<string, 'start' | 'doc'> = {
  dashboard: 'start', alerts: 'start', portal: 'start',
  staffList: 'doc', contracts: 'doc', employeeRequests: 'doc', orders: 'doc',
  leaveSchedule: 'doc', leave: 'doc', sickLeave: 'doc', rosters: 'doc', timesheets: 'doc',
  payroll: 'doc', payrollPayments: 'doc', payItemChanges: 'doc',
}

/** Legăturile dintre documente în schema de lucru (din primul se face al doilea): săgeata între iconițe, iar documentul de
 *  bază stă înaintea celui făcut din el. */
export const PANEL_FLOWS: [string, string][] = [
  ['leaveSchedule', 'leave'], // concediul din graficul concediilor
  ['rosters', 'timesheets'], // pontajul din graficul de ture
  ['payroll', 'payrollPayments'], // îndreptarea spre plată din calcul
  ['payItemChanges', 'payroll'], // acumulările planificate intră în calculul lunii
]

/** Clasificatoarele (setările-cataloage din SETTINGS_NAV) pe care le folosește fiecare funcție: panoul secțiunii le arată
 *  la Clasificatoare, cu dreptul și bifa de rol ale setării. Setările-reguli (concediile, alertele, constantele) rămân doar
 *  la Administrare → Setări. */
export const PANEL_CLASSIFIERS: Record<string, string[]> = {
  staffList: ['occupations', 'specialties'],
  occupancy: ['occupations'],
  employees: ['dict:education', 'dict:education_form', 'dict:document', 'dict:family',
    'dict:marital', 'dict:nationality', 'dict:checklist', 'localities', 'banks'],
  contracts: ['dict:employment', 'workSchedules'],
  orders: ['orderTypes', 'legalBases', 'dict:termination', 'dict:sanction', 'dict:incentive'],
  ordersRegister: ['orderTypes'],
  leaveSchedule: ['productionCalendar'],
  leave: ['productionCalendar'],
  rosters: ['workSchedules', 'shiftTypes', 'productionCalendar'],
  timesheets: ['workSchedules', 'shiftTypes', 'productionCalendar'],
  payroll: ['payrollTypes'],
  payItemChanges: ['payrollTypes'],
  payrollPayments: ['banks'],
  military: ['dict:military_group', 'dict:military_rank', 'dict:military_center'],
}

/**
 * Adresele de dinainte de Administrare → Setări (favorite, file deschise, legături vechi) → adresa setării noi; null — adresa
 * e la locul ei. Redirecționarea o face AppLayout, iar bara ferestrelor deschise nu păstrează file pentru adresele vechi.
 */
export function movedTo(pathname: string, search = ''): string | null {
  const tab = new URLSearchParams(search).get('tab')
  switch (pathname.replace(/\/$/, '')) {
    case '/dictionaries':
    case '/dictionaries/other':
      return '/settings'
    case '/worktime':
      return `/worktime/${tab && ['shifts', 'calendar', 'settings'].includes(tab) ? tab : 'schedules'}`
    case '/payroll/settings':
      return `/payroll/settings/${tab === 'constants' ? 'constants' : 'types'}`
    case '/leave':
      return tab === 'settings' ? '/leave/settings' : null
    case '/alerts':
      return tab === 'settings' ? '/alerts/settings' : tab === 'email' ? '/alerts/email' : null
    case '/tax-reports':
      return tab === 'settings' ? '/tax-reports/settings' : null
    default:
      return null
  }
}

/** Rapoartele din catalog (apps/reports) ca funcții de meniu, ca să stea la grupa Rapoarte a secțiunii lor; dreptul e cel al
 *  raportului (serverul îl verifică oricum la deschidere). */
const report = (key: string, slug: string, perm = 'reports.view'): NavItem =>
  ({ path: `/reports/${slug}`, key, icon: <BarChartOutlined />, perm })

export const REPORT_NAV: NavItem[] = [
  report('repMovement', 'movement'), report('repStructure', 'structure'), report('repSeniority', 'seniority'),
  report('repBirthdays', 'birthdays'), report('repRetirements', 'retirements'), report('repVacancies', 'vacancies'),
  report('repMunca1', 'munca1'),
  report('repLeavePeriod', 'leave_period'), report('repTimesheetSummary', 'timesheet_summary'),
  report('repOrdersPayroll', 'orders_payroll'), report('repOrdersByType', 'orders_by_type'),
  report('repTrainingPeriod', 'training_period'), report('repTrainingExpiry', 'training_expiry'), report('repHealthDue', 'health_due'),
  report('repMilitaryRegister', 'military_register', 'military.view'), report('repMilitaryMissing', 'military_missing', 'military.view'),
  report('repMilitaryChanges', 'military_changes', 'military.view'), report('repMilitaryRecruits', 'military_recruits', 'military.view'),
  report('repSalaryBook', 'salary_book', 'payroll.view'), report('repWorkwear', 'workwear_sizes'),
]

// păstrat pentru compatibilitate cu componentele din CAI ERP care îl importă
export const PROFILE_ICON = <ProfileOutlined />

import type { ButtonStyle, ThemeChoice, ThemeName } from '../theme/themes'

export type Lang = 'ro' | 'ru' | 'en'

export interface Role {
  id: number
  code: string
  name_ro: string
  name_ru: string
  description: string
  is_admin: boolean
  is_system: boolean
  permissions: string[]
  data_scopes: Record<string, 'own' | 'team' | 'all'>
  max_discount: string
  min_margin: string | null
  hidden_fields: string[]
  menu_hidden: string[]
  user_count?: number
}

export interface Me {
  id: number
  username: string
  first_name: string
  last_name: string
  middle_name: string
  full_name: string
  email: string
  phone: string
  position: string
  language: Lang
  theme: ThemeChoice
  density: 'normal' | 'compact'
  buttons: ButtonStyle
  roles: Role[]
  permissions: string[]
  is_admin: boolean
  hidden_fields: string[]
  menu_hidden: string[]
  favorites: { path: string; key: string; title: string }[]
  max_discount: string
  min_margin: string
  can_see_margin: boolean
  scopes: Record<string, 'own' | 'team' | 'all'>
  must_change_password: boolean
  last_seen_version: string
  license: LicenseSummary
  tours_done: string[]
  /** Profilul produsului: 'trade' (comerț alimentar / nealimentar) sau 'roofing' (acoperișuri și garduri). */
  profile?: 'trade' | 'roofing'
}

export interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  middle_name: string
  full_name: string
  email: string
  phone: string
  position: string
  language: Lang
  theme: ThemeChoice
  is_active: boolean
  roles: number[]
  subdivisions?: number[]
  must_change_password: boolean
  last_login: string | null
  date_joined: string
  password?: string
}

export interface Branding {
  name_ro: string
  name_ru: string
  logo: string | null
  logo_small: string | null
  logo_dark: string | null
  default_theme: ThemeName
  primary_color: string
  version: string
  name_en?: string
  payroll_enabled?: boolean
  function_panel?: boolean
  languages?: Lang[]
}

export interface BankAccount {
  id: number
  iban: string
  bank_name: string
  bic: string
  currency: string
  is_default: boolean
}

export interface Company {
  id: number
  name_ro: string
  name_ru: string
  name_en: string
  legal_form: string
  idno: string
  caem: string
  legal_address: string
  postal_address: string
  phone: string
  email: string
  website: string
  director: string
  director_position_ro: string
  director_position_ru: string
  chief_accountant: string
  chief_accountant_position_ro: string
  chief_accountant_position_ru: string
  hr_head: string
  hr_head_position_ro: string
  hr_head_position_ru: string
  logo: string | null
  logo_small: string | null
  logo_dark: string | null
  signature: string | null
  stamp: string | null
  default_theme: ThemeName
  primary_color: string
  bank_accounts: BankAccount[]
  payroll_enabled: boolean
  function_panel: boolean
  languages: Lang[]
}

export interface Currency {
  id: number
  code: string
  name_ro: string
  name_ru: string
  symbol: string
  is_base: boolean
  is_active: boolean
  auto_rate: boolean
  last_rate: { date: string; rate: string; nominal: number } | null
}

export interface ExchangeRate {
  id: number
  currency: number
  currency_code: string
  date: string
  rate: string
  nominal: number
  source: string
}

export interface VatRate {
  id: number
  name: string
  rate: string
  is_default: boolean
  is_active: boolean
}

export interface NumberSeries {
  id: number
  doc_type: string
  name_ro: string
  name_ru: string
  prefix: string
  include_year: boolean
  padding: number
  reset_yearly: boolean
  next_value: number
  preview: string
}

export interface AuditEntry {
  id: number
  timestamp: string
  user: number | null
  username: string
  action: string
  model: string
  object_id: string
  object_repr: string
  changes: Record<string, unknown>
  ip: string | null
}

export interface Notification {
  id: number
  level: 'info' | 'task' | 'warning' | 'success'
  kind: string
  title: string
  message: string
  link: string
  is_read: boolean
  created_at: string
}

export interface LicenseSummary {
  mode: 'trial' | 'licensed' | 'invalid'
  valid: boolean
  read_only: boolean
  error: string
  valid_until: string | null
  days_left: number | null
  warn: boolean
  modules: string[]
}

export interface LicenseStatus {
  mode: 'trial' | 'licensed' | 'invalid'
  valid: boolean
  error: string
  company?: string
  idno?: string
  max_users: number
  modules: string[]
  valid_until: string | null
  expired?: boolean
  days_left?: number
  plan?: string
  plan_name?: string
  active_users?: number
  over_limit?: boolean
  plans?: { key: string; name: string; min: number; max: number }[]
}

export interface PermissionCatalog {
  modules: { code: string; name_ro: string; name_ru: string; actions: string[]; scoped: boolean }[]
  actions: Record<string, { ro: string; ru: string }>
  scopes: Record<string, { ro: string; ru: string }>
  sensitive_fields: Record<string, { ro: string; ru: string }>
}

export interface DashboardTab {
  key: 'offers' | 'orders' | 'clients' | 'managers'
  scope: 'own' | 'team' | 'all'
  ready: boolean
  data: unknown
}

export const LANG_LABELS: Record<Lang, string> = { ro: 'Română', ru: 'Русский', en: 'English' }

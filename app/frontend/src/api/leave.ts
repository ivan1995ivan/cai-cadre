// Concediile (Etapa 4): soldurile, graficul anual, cererile, foile de boală.

export interface OrderRef { id: number; label: string; status: string }

export interface WorkYear {
  from: string
  to: string
  base: number
  extra: number
  personal: number
  entitled: number
  accrued: number
  used: number
  adjusted: number
  remaining: number
  available: number
  skipped: number
  closed: boolean
  absences: number[]
}

export interface Balance {
  employee: number
  on_date: string
  start: string | null
  years: WorkYear[]
  opening: number
  remaining: number
  available: number
  current: { from: string; to: string; entitled: number } | null
}

export interface BalanceRow {
  id: number
  tab_number: string
  full_name: string
  status: string
  subdivision: string
  occupation: string
  hired: string | null
  year_from: string | null
  year_to: string | null
  entitled: number
  accrued: number
  used: number
  remaining: number
  available: number
}

export interface LeaveRight {
  id: number
  employee: number
  reason: string
  reason_label: string
  days: number
  date_from: string | null
  date_to: string | null
  note: string
}

export interface LeaveAdjustment {
  id: number
  employee: number
  kind: string
  kind_label: string
  date: string
  work_year_from: string | null
  days: string
  note: string
  order: OrderRef | null
}

export interface LeaveSchedule {
  id: number
  deletion_mark?: boolean
  year: number
  subdivision: number
  subdivision_name: string
  status: 'draft' | 'submitted' | 'approved'
  status_label: string
  approved_by: string
  approved_at: string | null
  note: string
  lines_count: number
  planned_count: number
}

export interface ScheduleRow {
  id: number
  employee: number
  name: string
  short_name: string
  tab_number: string
  occupation: string
  category: string
  date_from: string | null
  days: number
  date_to: string | null
  moved_to: string | null
  note: string
  sort: number
  available: number
  remaining: number
  state: 'planned' | 'taken' | 'moved' | 'missed'
  actual: { id: number; from: string; to: string; days: number }[]
  other_jobs: string[] // celelalte raporturi ale angajatului (cumul, prestări servicii)
}

/** Cei care lucrează în secție prin cumul / suplinire, cu concediul planificat în graficul secției de bază. */
export interface ScheduleGuest {
  id: string
  employee: number
  name: string
  kind: string
  rate: number
  occupation: string
  home: string
  date_from: string | null
  days: number
  date_to: string | null
  moved_to: string | null
}

export interface ScheduleWarning {
  kind: 'balance' | 'occupation' | 'physicians'
  name?: string
  label?: string
  days?: number
  available?: number
  count?: number
  from?: string
  to?: string
}

export interface ScheduleReport extends LeaveSchedule {
  rows: ScheduleRow[]
  guests: ScheduleGuest[]
  warnings: ScheduleWarning[]
}

export interface LeaveRequest {
  id: number
  employee: number
  employee_name: string
  employee_tab: string
  subdivision: string
  kind: string
  kind_label: string
  date_from: string
  days: number
  date_to: string
  work_year_from: string | null
  work_year_to: string | null
  reason: string
  status: 'new' | 'approved' | 'rejected' | 'ordered' | 'withdrawn'
  status_label: string
  decided_by_name: string
  decided_at: string | null
  decision_note: string
  order: OrderRef | null
  created_at: string
}

export interface SickLeave {
  id: number
  deletion_mark?: boolean
  employee: number
  employee_name: string
  employee_tab: string
  subdivision: string
  series: string
  number: string
  issued_on: string | null
  issued_by: string
  kind: string
  kind_label: string
  date_from: string
  date_to: string
  days: number
  continuation_of: number | null
  continuation_label: string
  continued_by: string // certificatul care îl continuă: cel continuat e încheiat, chiar fără data prezentării
  return_date: string | null
  file: string | null
  note: string
  absence: number | null
  warnings?: string[]
}

export const REQUEST_KINDS = ['annual', 'extra', 'unpaid', 'maternity', 'paternity', 'childcare', 'childcare_unpaid', 'study', 'days_off']
export const RIGHT_REASONS = ['children', 'disability', 'collective', 'seniority', 'conditions', 'other']
export const ADJUSTMENT_KINDS = ['opening', 'compensated', 'correction']
export const SICK_KINDS = ['illness', 'household_injury', 'work_accident', 'pregnancy', 'child_care', 'family_care', 'quarantine',
  'prosthesis', 'other']

export const REQUEST_STATUS_COLOR: Record<string, string> = {
  new: 'blue', approved: 'green', rejected: 'red', ordered: 'purple', withdrawn: 'default',
}
export const SCHEDULE_STATUS_COLOR: Record<string, string> = { draft: 'gold', submitted: 'blue', approved: 'green' }
export const PLAN_STATE_COLOR: Record<string, string> = { planned: 'default', taken: 'green', moved: 'orange', missed: 'red' }

/** Zilele (pot fi cu zecimale la acumulare): „14” sau „14,38”. */
export const fmtDays = (v: number | string | null | undefined) =>
  v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('ro-MD', { maximumFractionDigits: 2 })

// Timpul de muncă (Etapa 4, partea 2): turele, graficele de lucru, graficul lunar (gărzi), tabela de pontaj.

export interface ShiftType {
  id: number
  code: string
  name: string
  hours: string
  night_hours: string
  start: string | null
  is_duty: boolean
  color: string
  sort: number
  is_active: boolean
}

export interface WorkSchedule {
  id: number
  code: string
  name: string
  kind: 'week' | 'cycle'
  kind_label: string
  weekly_hours: string
  week: string[]
  cycle: string[]
  cycle_start: string | null
  holidays_off: boolean
  note: string
  is_active: boolean
  jobs_count: number
}

export interface JobSchedule {
  id: number
  employment: number
  schedule: number
  schedule_name: string
  date_from: string
  cycle_offset: number
}

export interface MonthNorm {
  month: number
  working_days: number
  calendar_days: number
  holidays: string[]
  norm_40: number
  norm_35: number
  norm_30: number
}

export interface DayHeader { day: number; weekday: number; holiday: boolean; working: boolean }

export interface MonthDoc {
  id: number
  deletion_mark?: boolean
  subdivision: number
  subdivision_name: string
  year: number
  month: number
  status: 'draft' | 'submitted' | 'approved' | 'closed'
  status_label: string
  note: string
  lines_count: number
  created_at: string
}

interface LineLabel {
  id: number
  employment: number
  employee: number
  name: string
  short_name: string
  tab_number: string
  kind: string
  kind_label: string
  occupation: string
  subdivision: string
  rate: number
  note: string
}

export interface RosterRow extends LineLabel {
  days: Record<string, string>
  absences: Record<string, string>
  hours: number
  night: number
  duties: number
  norm: number
  diff: number
}

export interface RosterWarning {
  kind: 'rest' | 'absence' | 'norm' | 'duties'
  employment: number
  name: string
  day?: number
  rest?: number
  code?: string
  hours?: number
  norm?: number
  duties?: number
  max?: number
}

export interface RosterReport extends MonthDoc {
  days: DayHeader[]
  rows: RosterRow[]
  warnings: RosterWarning[]
}

/** Celula pontajului: codul (tura, orele sau absența), orele, orele de noapte, scrisă de mână, zi de sărbătoare. */
export interface TimesheetCell { c: string; h?: number; n?: number; m?: number; hol?: number }

export interface TimesheetTotals {
  days: number
  hours: number
  night: number
  holiday: number
  norm: number
  overtime: number
  missing: number
  codes: Record<string, number>
}

export interface TimesheetRow extends LineLabel {
  days: Record<string, TimesheetCell>
  totals: TimesheetTotals
}

export interface TimesheetReport extends MonthDoc {
  days: DayHeader[]
  rows: TimesheetRow[]
  codes: Record<string, string>
  manual_codes: string[]
}

export const MONTH_STATUS_COLOR: Record<string, string> = { draft: 'gold', submitted: 'blue', approved: 'green', closed: 'green' }

/** Luna curentă pentru documentele lunare: până pe 5 se lucrează încă la luna trecută. */
export function defaultMonth(): { year: number; month: number } {
  const now = new Date()
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() <= 5 ? 0 : 1)
  return { year: d.getFullYear(), month: d.getMonth() + 1 }
}

export const fmtH = (v: number | string | null | undefined) =>
  v === null || v === undefined || v === '' || Number(v) === 0 ? '' : Number(v).toLocaleString('ro-MD', { maximumFractionDigits: 2 })

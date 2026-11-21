// Timpul de muncă (Etapa 4, partea 2): turele, graficele de lucru, graficul de ture, tabela de pontaj.

export interface ShiftType {
  id: number
  code: string
  name: string
  hours: string
  night_hours: string
  start: string | null
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
  nights: number
  norm: number
  diff: number
}

export interface RosterWarning {
  kind: 'rest' | 'consecutive' | 'absence' | 'norm' | 'nights'
  employment: number
  name: string
  day?: number
  rest?: number
  need?: number
  code?: string
  hours?: number
  norm?: number
  nights?: number
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
  // pe zile (CM art. 157, 158): suplimentarele — primele 2 ore / restul; sărbătorile și zilele de repaus — în limita normei / peste
  rest_work?: number
  regular?: number
  overtime_2?: number
  overtime_over?: number
  overtime_period?: number
  overtime_days?: Record<string, [number, number]>
  holiday_in_norm?: number
  holiday_over_norm?: number
}

/** Tipul de ore (instruire, examinare, zbor…): coloana din pontaj și `Ore.COD` în formule. */
export interface HourType {
  id: number
  code: string
  name_ro: string
  name_ru: string
  name_en: string
  group: string
  work_time: 'within' | 'added' | 'none'
  entry: 'day' | 'month'
  profile: string
  in_all_timesheets: boolean
  pay_type: number | null
  sort: number
  is_active: boolean
  is_system: boolean
}
export const HOUR_GROUPS = ['worked', 'training', 'exam', 'flight', 'reserve', 'standby', 'driving', 'availability', 'other']
export const HOUR_PROFILES = ['general', 'factory', 'aviation', 'transport']

/** Orele unui tip pe linie: pe zile sau totalul pe lună. */
export interface TypedEntry { days: Record<string, number>; month: number | null }

/** Rezumatul orelor unui tip pe raport (apps.worktime.hour_types.summarize). */
export interface HourSummary {
  code: string
  name: string
  work_time: string
  hours: number
  by_day: boolean
  paid: number
  amount: number
  guaranteed: number | null
  guaranteed_full: number | null
  available_days: number | null
  total_days: number
  rate: number | null
  unrated_hours: number
  note: string
  rows: { id: number; rate: number; from: string; to: string | null; hours: number; guaranteed: number | null;
    guaranteed_full: number | null; available_days: number | null; paid: number; amount: number }[]
}

export interface HourColumn { code: string; name_ro: string; name_ru: string; name_en: string; entry: 'day' | 'month'; work_time: string; is_active: boolean }

export interface TimesheetRow extends LineLabel {
  days: Record<string, TimesheetCell>
  totals: TimesheetTotals
  typed: Record<string, TypedEntry>
  hour_types: Record<string, HourSummary>
  hour_warnings: string[]
  pay_mode: string
  rate_codes: string[]
  combinations: { kind: string; occupation: string; pay_mode: string; value: number; text: string }[]
}

export interface TimesheetReport extends MonthDoc {
  days: DayHeader[]
  rows: TimesheetRow[]
  codes: Record<string, string>
  manual_codes: string[]
  hour_types: HourColumn[]
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

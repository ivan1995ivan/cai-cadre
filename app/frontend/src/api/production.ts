/** Producția — salarizarea în acord (S5a): grila tarifară, lucrările, brigăzile, rapoartele de producție. */

export const UNITS = ['buc', 'set', 'kg', 't', 'm', 'm2', 'm3', 'l', 'op', 'other'] as const

export interface TariffRank { id?: number; rank: number; coefficient: string | number; rate: string | number | null; hourly?: string | number | null }

export interface TariffGrid {
  id: number
  deletion_mark: boolean
  code: string
  name: string
  date_from: string
  base_rate: string
  document: string
  note: string
  ranks: TariffRank[]
}

export interface OperationRate {
  id: number
  operation: number
  date_from: string
  norm_kind: 'time' | 'output'
  norm_kind_label: string
  norm_value: string
  grid_code: string
  rank: number | null
  piece_rate: string | null
  document: string
  price: { rate: string | null; how: string }
}

export interface Operation {
  id: number
  deletion_mark: boolean
  code: string
  name_ro: string
  name_ru: string
  name_en: string
  unit: string
  unit_label: string
  subdivision: number | null
  subdivision_name: string
  progressive: boolean
  note: string
  sort: number
  is_active: boolean
  current: { date_from: string; norm_kind: string; norm_value: string; rate: string | null; how: string } | null
}

export interface BrigadeMember {
  id?: number
  employment: number | null
  employee?: number | null
  employee_name?: string
  tab_number?: string
  employment_label?: string
  coefficient: string | number
  date_from: string | null
  date_to: string | null
}

export interface Brigade {
  id: number
  deletion_mark: boolean
  code: string
  name: string
  subdivision: number | null
  subdivision_name: string
  distribution: 'hours' | 'tariff'
  distribution_label: string
  leader: number | null
  leader_name: string
  note: string
  is_active: boolean
  members: BrigadeMember[]
}

export interface ProductionLine {
  id?: number
  employment: number | null
  employee?: number | null
  employee_name?: string
  tab_number?: string
  employment_label?: string
  operation: number | null
  operation_code?: string
  operation_name?: string
  unit_label?: string
  progressive?: boolean
  quantity: string | number
  defect_nofault: string | number
  defect_partial: string | number
  defect_partial_pct: string | number | null
  defect_worker: string | number
  hours: string | number | null
  note: string
  rate?: string | null
  norm_time?: string | null
  amount?: string
  normed_hours?: string
  how?: string
}

export interface ProductionMember {
  id?: number
  employment: number | null
  employee?: number | null
  employee_name?: string
  tab_number?: string
  employment_label?: string
  hours: string | number
  coefficient: string | number
  hourly?: string | null
  amount?: string
  progressive_amount?: string
  normed_hours?: string
}

export interface ProductionReport {
  id: number
  deletion_mark: boolean
  number: string
  date: string
  kind: 'individual' | 'brigade'
  kind_label: string
  subdivision: number | null
  subdivision_name: string
  brigade: number | null
  brigade_name: string
  status: 'draft' | 'approved'
  status_label: string
  shortfall_cause: '' | 'employer' | 'nobody'
  note: string
  created_at: string
  approved_at: string | null
  lines: ProductionLine[]
  members: ProductionMember[]
  totals: { amount: number; normed_hours: number; hours: number; lines: number }
  problems: string[]
  who: string
}

export const blankLine = (): ProductionLine => ({
  employment: null, operation: null, quantity: '', defect_nofault: 0, defect_partial: 0, defect_partial_pct: null, defect_worker: 0,
  hours: null, note: '',
})

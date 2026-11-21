// Întreprinderea, clasificatoarele și statele de personal (Etapa 1).

export interface NamedItem {
  id: number
  code: string
  name_ro: string
  name_ru: string
  name_en: string
  sort: number
  is_active: boolean
  deletion_mark?: boolean
}

export interface Occupation extends NamedItem {
  /** Categoria de personal (clasificatorul „Categoriile de personal”, grupele CORM); null — fără categorie. */
  category: number | null
  category_name: string
  isco_code: string
  weekly_hours: string
  base_leave_days: number
  extra_leave_days: number
  harmful: boolean
  notes: string
}

export interface Specialty extends NamedItem {
  kind: string
  isced: string
}

export interface Subdivision extends NamedItem {
  parent: number | null
  parent_name: string
  kind: string
  harmful: boolean
  extra_leave_days: number
  reduced_hours: string | null
  head_name: string
  children?: Subdivision[]
}

export interface StaffList {
  id: number
  deletion_mark?: boolean
  number: string
  date: string
  effective_from: string
  approved_by: string
  basis: string
  status: 'draft' | 'approved' | 'cancelled'
  status_label: string
  previous: number | null
  previous_label: string
  notes: string
  created_at: string
  approved_at: string | null
  lines_count: number | null
}

export interface StaffListLine {
  id: number
  staff_list: number
  subdivision: number
  subdivision_name: string
  occupation: number
  occupation_code: string
  occupation_name: string
  category: number | null
  effective_category: number | null
  effective_category_name: string
  units: string
  base_salary: string
  allowance_pct: string
  note: string
  sort: number
  monthly_fund: string
}

export interface Totals {
  categories: { id: number | null; code: string; name: string; units: string; fund: string }[]
  subdivisions: { id: number; name: string; units: string; fund: string }[]
  units: string
  fund: string
}

export interface DiffRow {
  subdivision: string
  occupation_code: string
  occupation: string
  change: 'added' | 'removed' | 'changed'
  units_before: string
  units_after: string
  salary_before: string
  salary_after: string
}

export interface OccupancyRow {
  subdivision_id: number
  subdivision: string
  occupation_id: number
  occupation_code: string
  occupation: string
  category: number | null
  category_name: string
  approved: string
  occupied: string
  temporary: string
  vacant: string
  over: boolean
  holders: { name: string; units: string; kind: string }[]
}

export interface Occupancy {
  staff_list: { id: number; number: string; effective_from: string } | null
  on_date?: string
  rows: OccupancyRow[]
  employees_module?: boolean
  totals: { approved: string; occupied: string; temporary: string; vacant: string } | null
}

export interface OrgMeta {
  order_groups: string[]
  order_registers: string[]
  order_effects: string[]
  dict_kinds: string[]
  subdivision_kinds: string[]
  specialty_kinds: string[]
  imports: { code: string; title: string }[]
}

export interface ImportResult {
  ok: boolean
  detail?: string
  created: number
  updated: number
  skipped: number
  rows: number
  dry_run?: boolean
  saved?: boolean
  errors: { row: number; error: string }[]
  preview?: { row: number; status: string; text: string }[]
}

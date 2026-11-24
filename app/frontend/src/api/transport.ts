// S6b: transportul — vehiculele, tarifele pe km, țările cu normele diurnei, cursele (foile de parcurs).

export const VEHICLE_KINDS = ['tractor', 'truck', 'trailer', 'bus', 'minibus', 'van', 'car', 'other'] as const
export const TRIP_KINDS = ['goods', 'passengers'] as const
export const SCOPES = ['domestic', 'international'] as const

export interface Vehicle {
  id: number
  deletion_mark: boolean
  plate: string
  kind: string
  kind_label: string
  brand: string
  model: string
  category: string
  tachograph: boolean
  fuel_norm: string | null
  subdivision: number | null
  subdivision_name: string
  note: string
  is_active: boolean
}

export interface Country {
  id: number
  code: string
  name_ro: string
  name_ru: string
  name_en: string
  sort: number
  is_active: boolean
  current: { amount: number; currency: string; date_from: string } | null
}

export interface PerDiemNorm {
  id: number
  country: number
  country_code: string
  country_name: string
  date_from: string
  currency: string
  amount: string
  document: string
}

export interface TripLeg {
  id?: number
  country: number | null
  country_code?: string
  country_name?: string
  entered: string | null
  left: string | null
  loading: boolean
  unloading: boolean
  meals: boolean
  km: string | number | null
  note?: string
}

export interface TripDiem {
  id: number
  employment: number
  employee_name: string
  day: string
  country: number | null
  country_code: string
  hours: string
  pct: string
  norm: string
  currency: string
  fx_rate: string
  amount: string
  taxable: string
  how: string
}

export interface Trip {
  id: number
  deletion_mark: boolean
  number: string
  driver: number
  driver_label: string
  co_driver: number | null
  co_driver_label: string
  vehicle: number
  vehicle_plate: string
  trailer: number | null
  trailer_plate: string
  kind: string
  kind_label: string
  scope: string
  scope_label: string
  departure: string
  arrival: string
  route: string
  odometer_out: number | null
  odometer_in: number | null
  km: string
  adr: boolean
  meals_provided: boolean
  per_diem_pct: string | null
  status: 'draft' | 'approved'
  status_label: string
  note: string
  km_rate: string | null
  km_amount: string
  how: string
  legs: TripLeg[]
  diems: TripDiem[]
  totals: { km: number; km_amount: number; per_diem: number; per_diem_taxable: number }
  problems: string[]
  warnings: string[]
}

export const blankLeg = (): TripLeg => ({ country: null, entered: null, left: null, loading: false, unloading: false, meals: false, km: null })

// S6b (pasul b): tahograful — descărcările cardului de conducător, zilele cu activitățile, constatările.
export const ACTIVITY_COLOR: Record<string, string> = { D: '#d4380d', W: '#1677ff', A: '#faad14', R: '#52c41a', U: '#bfbfbf' }

/** Minutele ca „9:05”. */
export const hm = (minutes: number) => `${Math.floor(minutes / 60)}:${String(Math.round(minutes % 60)).padStart(2, '0')}`

export interface TachoFile {
  id: number
  name: string
  size: number
  generation: number
  version: number
  card_number: string
  card_nation: string
  authority: string
  card_issue: string | null
  card_expiry: string | null
  holder: string
  holder_surname: string
  holder_first_names: string
  birth_date: string | null
  licence_number: string
  downloaded_at: string | null
  first_day: string | null
  last_day: string | null
  days: number
  employee: number | null
  employee_name: string
  matched_by: string
  uploaded_at: string
}

export interface TachoUpload { name: string; status: 'created' | 'duplicate' | 'error'; file?: number; employee?: number | null; employee_name?: string; message: string }

export interface TachoFinding { code: string; title: string; start: string; end: string; value: number; limit: number; text: string; level: 'error' | 'info' }

export interface TachoDayRow {
  day: string
  has_data: boolean
  spans: [number, number, string, number][]
  driving: number
  work: number
  availability: number
  rest: number
  unknown: number
  km: number
  countries: string[]
  vehicles: string[]
  findings: TachoFinding[]
}

export interface TripTacho {
  any_files: boolean
  people: { employee: number; name: string; has_data: boolean; covered: boolean; borders: number
    totals: { driving: number; work: number; availability: number; rest: number; unknown: number }; findings: TachoFinding[] }[]
}

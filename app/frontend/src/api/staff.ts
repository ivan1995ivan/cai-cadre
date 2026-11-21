// Dosarul angajatului (Etapa 2).
import { useMemo } from 'react'

import { useFetch } from './hooks'
import { useLocalName } from '../auth/AppContext'

export type EmploymentKind = 'main' | 'main_student' | 'internal' | 'external' | 'substitute' | 'contractor'
export const EMPLOYMENT_KINDS: EmploymentKind[] = ['main', 'main_student', 'internal', 'external', 'substitute', 'contractor']

export interface EmployeeRow {
  id: number
  tab_number: string
  full_name: string
  last_name: string
  first_name: string
  patronymic: string
  idnp: string | null
  birth_date: string | null
  sex: string
  phone: string | null
  email: string | null
  status: 'active' | 'suspended' | 'dismissed' | 'candidate'
  status_label: string
  is_archived: boolean
  subdivision: string
  occupation: string
  category: number | null
  category_name: string
  kind: EmploymentKind | ''
  rate: string
  date_from: string | null
  jobs: number
}

export interface SeniorityPart { years: number; months: number; days: number; total_days: number; text: string }

export interface Employee {
  id: number
  deletion_mark?: boolean
  tab_number: string
  full_name: string
  last_name: string
  first_name: string
  patronymic: string
  previous_names: string
  idnp: string | null
  birth_date: string | null
  birth_place: string | null
  sex: string
  citizenship: string
  nationality: number | null
  nationality_name: string
  marital_status: number | null
  marital_status_name: string
  photo: string | null
  phone: string | null
  phone2: string | null
  email: string | null
  address: string | null
  address_actual: string | null
  cnam_code: string | null
  cpas: string | null
  iban: string | null
  bank_name: string | null
  emergency_contact: string | null
  disability: string | null
  clothing_size: string
  shoe_size: string
  height: number | null
  status: EmployeeRow['status']
  status_label: string
  is_archived: boolean
  checklist: Record<string, { hire?: string | null; exit?: string | null }>
  notes: string
  user: number | null
  created_at: string
  seniority: Record<'total' | 'specialty' | 'institution', SeniorityPart> | null
}

export interface HistoryRow {
  id: number
  event: string
  event_label: string
  date: string
  subdivision: number
  subdivision_name: string
  occupation: number
  occupation_name: string
  rate: string
  base_salary: string | null
  allowance_pct: string | null
  pay_mode?: PayMode
  hourly_rate?: string | null
  order: string
  note: string
}

/** Modalitatea de remunerare a raportului de muncă (pe funcție); tarifele pe tipuri de ore se plătesc la „hour_types” și „mixed”. */
export const PAY_MODES = ['salary', 'hourly', 'hour_types', 'mixed'] as const
export type PayMode = (typeof PAY_MODES)[number]
export const RATE_MODES: PayMode[] = ['hour_types', 'mixed']

export interface DocSource { kind: 'order' | 'change' | 'manual'; id: number | null; label: string; status: string }

/** Tariful pe tipul de ore al raportului, cu orele garantate pe lună. */
export interface JobHourRate {
  id: number
  employment: number
  hour_type: number
  hour_type_code: string
  hour_type_name: string
  rate: string
  guaranteed_hours: string | null
  date_from: string
  date_to: string | null
  document: string
  source: DocSource
}

/** Cumularea funcțiilor / suplinirea / interimatul pe același contract (CM art. 156). */
export const COMBINATION_KINDS = ['combination', 'substitution', 'acting'] as const
export const COMBINATION_PAY = ['pct_own', 'pct_other', 'fixed', 'hourly'] as const
export interface FunctionCombination {
  id: number
  employment: number
  kind: (typeof COMBINATION_KINDS)[number]
  kind_label: string
  occupation: number
  occupation_name: string
  subdivision: number | null
  subdivision_name: string
  substitutes: number | null
  substituted_name: string
  pay_mode: (typeof COMBINATION_PAY)[number]
  pay_mode_label: string
  value: string
  value_text: string
  other_salary: string | null
  hour_type: number | null
  hour_type_code: string
  date_from: string
  date_to: string | null
  order: string
  note: string
  source: DocSource
}

export interface Employment {
  id: number
  employee: number
  warnings?: string[]
  kind: EmploymentKind
  kind_label: string
  subdivision: number
  subdivision_name: string
  occupation: number
  occupation_name: string
  occupation_code: string
  category: number | null
  category_name: string
  rate: string
  base_salary: string | null
  allowance_pct: string | null
  pay_mode: PayMode
  pay_mode_label: string
  hourly_rate: string | null
  hour_rates: JobHourRate[] | null
  combinations: FunctionCombination[] | null
  date_from: string
  date_to: string | null
  probation_until: string | null
  contract_number: string
  contract_date: string | null
  substitutes: number | null
  status: 'active' | 'suspended' | 'ended'
  status_label: string
  suspended_from: string | null
  suspension_reason: string
  end_date: string | null
  termination_reason: number | null
  termination_reason_name: string
  hire_order: string
  end_order: string
  note: string
  history: HistoryRow[]
}

export interface AccessEntry { id: number; user_name: string; action: string; action_label: string; detail: string; at: string }

export interface DictOption { value: number; label: string; code: string; extra?: Record<string, unknown> }

/** Elementele unui clasificator (tip) ca opțiuni pentru Select, în limba curentă. */
export function useDict(kind: string): DictOption[] {
  const localName = useLocalName()
  const { data } = useFetch<{ id: number; code: string; name_ro: string; name_ru: string; name_en: string; is_active: boolean; extra: Record<string, unknown> }[]>(
    '/org/dict-items/', { kind })
  return useMemo(() => (data ?? []).filter((d) => d.is_active).map((d) => ({ value: d.id, label: localName(d), code: d.code, extra: d.extra })),
    [data, localName])
}

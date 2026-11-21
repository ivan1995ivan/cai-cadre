// Ordinele (Etapa 3).

export interface OrderItem {
  id: number
  order: number
  employee: number | null
  employee_name: string
  employee_tab: string
  employment: number | null
  params: Record<string, unknown>
  text: string
  text_edited: boolean
  sort: number
  acknowledged_on: string | null
  result: Record<string, unknown>
  warnings?: string[]
}

export interface Approval { name: string; position: string }

export interface Order {
  id: number
  deletion_mark?: boolean
  order_type: number
  type_code: string
  type_name: string
  effect: string
  collective: boolean
  group: string
  register: string
  year: number
  seq: number | null
  number: string
  date: string
  title: string
  preamble: string
  basis: string
  /** temeiurile legale (unul sau mai multe); legal_bases_ref — textul lor, pe acte */
  legal_bases: number[]
  legal_bases_ref: string
  footer: string
  signer_name: string
  signer_position: string
  approvals: Approval[]
  status: 'draft' | 'signed' | 'cancelled'
  status_label: string
  cancelled_by: number | null
  cancelled_by_label: string
  notes: string
  created_at: string
  signed_at: string | null
  items?: OrderItem[]
  employees: string
}

export interface OrderTypeLite {
  id: number
  code: string
  name_ro: string
  name_ru: string
  name_en: string
  group: string
  register: string
  effect: string
  collective: boolean
  needs_employee: boolean
  is_active: boolean
}

export interface Absence {
  id: number
  kind: string
  kind_label: string
  date_from: string
  date_to: string
  days: number
  destination: string
  note: string
  recalled_on: string | null
  days_returned: number
  order: { id: number; label: string } | null
}

export interface SanctionRec {
  id: number
  kind_name: string
  date: string
  misconduct: string
  valid_until: string
  lifted_on: string | null
  order: { id: number; label: string } | null
}

export interface IncentiveRec {
  id: number
  kind_name: string
  date: string
  amount: string | null
  percent: string | null
  note: string
  order: { id: number; label: string } | null
}

export const ORDER_STATUS_COLOR: Record<string, string> = { draft: 'gold', signed: 'green', cancelled: 'red' }

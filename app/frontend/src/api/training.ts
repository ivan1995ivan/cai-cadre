export const TRAINING_KINDS = ['course', 'thematic', 'conference', 'seminar', 'internship', 'online', 'publication', 'other']
export const ATT_STATUSES = ['planned', 'submitted', 'awarded', 'confirmed', 'refused', 'postponed']
export const CREDIT_STATUS_COLOR: Record<string, string> = { risk: 'red', behind: 'orange', ok: 'blue', done: 'green' }
export const ATT_STATUS_COLOR: Record<string, string> = {
  planned: 'default', submitted: 'blue', awarded: 'green', confirmed: 'green', refused: 'red', postponed: 'orange',
}

export interface TrainingRecord {
  id: number
  deletion_mark?: boolean
  employee: number
  employee_name: string
  tab_number: string
  kind: string
  kind_label: string
  title: string
  provider: string
  specialty: number | null
  specialty_name: string
  date_from: string
  date_to: string | null
  hours: string
  credits: string
  certificate_number: string
  certificate_date: string | null
  order_item: number | null
  order_ref: string
  note: string
}

export interface CreditRow {
  employee: number
  tab: string
  name: string
  subdivision: string
  occupation: string
  staff_category: string
  category: string
  specialty: string
  awarded_on: string | null
  expiry: string | null
  period_from: string
  credits: number
  required: number
  expected: number
  missing: number
  pct: number
  status: 'risk' | 'behind' | 'ok' | 'done'
  expired?: boolean
  in_list?: boolean
}

export interface Attestation {
  id: number
  deletion_mark?: boolean
  employee: number
  employee_name: string
  tab_number: string
  subdivision: string
  specialty: number | null
  specialty_name: string
  current_category_name: string
  due_date: string | null
  requested_category: number
  requested_category_name: string
  session_date: string | null
  submitted_on: string | null
  status: string
  status_label: string
  result_category: number | null
  result_category_name: string
  result_date: string | null
  decision: string
  order_item: number | null
  order_ref: string
  order_id: number | null
  note: string
}

export interface TrainingPlan {
  id: number
  deletion_mark?: boolean
  year: number
  number: string
  date: string
  status: 'draft' | 'approved'
  note: string
  lines_count: number
  done_count: number
  credits_total: string | null
}

export const TRAINING_KINDS = ['course', 'thematic', 'internal', 'conference', 'seminar', 'internship', 'online', 'other']

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
  certificate_number: string
  certificate_date: string | null
  valid_until: string | null
  order_item: number | null
  order_ref: string
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
  hours_total: string | null
}

// Salarizarea (Etapa 4b): constantele, tipurile de calcul, scutirile, calculul lunar.

export interface PayConstant {
  id: number
  code: string
  name: string
  value: string
  date_from: string
  source: string
  unit: string
}

export interface PayType {
  id: number
  code: string
  name_ro: string
  name_ru: string
  name_en: string
  category: 'accrual' | 'deduction' | 'employer'
  category_label: string
  formula: 'auto' | 'fixed' | 'pct_salary' | 'pct_base' | 'hourly' | 'scale' | 'expr'
  formula_label: string
  auto: string
  expression: string
  applies_to: 'row' | 'all'
  applies_to_label: string
  how: { ro: string; ru: string; en: string }
  percent: string
  base_codes: string[]
  scale: { from: number; pct: number }[]
  taxable: boolean
  cas: boolean
  cnam: boolean
  exempt_month: string
  exempt_year: string
  exempt_avg_pct: string
  in_average: boolean
  ipc_code: string
  account: string
  on_payslip: boolean
  sort: number
  is_active: boolean
  is_system: boolean
  deletion_mark?: boolean
}

export interface EmployeePayItem {
  id: number
  employee: number
  employment: number | null
  employment_label: string
  pay_type: number
  pay_type_name: string
  pay_type_code: string
  formula: string
  category: string
  amount: string | null
  percent: string | null
  quantity: string | null
  date_from: string
  date_to: string | null
  document: string
  note: string
  source: PayItemSource
}

/** De unde vine rândul din fila „Salariu”: ordinul, documentul „Modificarea acumulărilor planificate” sau de mână. */
/** De unde vine rândul; `number` / `date` — pentru denumirea în limba interfeței (`label` e în română). */
export interface PayItemSource { kind: 'order' | 'change' | 'manual'; id: number | null; label: string; status: string; number?: string; date?: string }

export type PayAction = 'add' | 'modify' | 'stop'
export const PAY_ACTIONS: PayAction[] = ['add', 'modify', 'stop']

/** Un rând al tabelului „Acumulări și rețineri” (în parametrii punctului de ordin: `params.pay_items`). */
export interface PlannedRow {
  pay_type: number | null
  action: PayAction
  target?: number | null
  amount?: string | number | null
  percent?: string | number | null
  quantity?: string | number | null
  date_from?: string | null
  date_to?: string | null
  document?: string
}

export interface PayItemChangeLine extends PlannedRow {
  id?: number
  employee: number | null
  employee_name?: string
  tab_number?: string
  employment: number | null
  employment_label?: string
  pay_type_code?: string
  pay_type_name?: string
  action_label?: string
}

export interface PayItemChange {
  id: number
  number: string
  date: string
  status: 'draft' | 'approved'
  status_label: string
  note: string
  deletion_mark?: boolean
  approved_at: string | null
  lines: PayItemChangeLine[]
  employees: string
}

export interface OccupationPayItem { id: number; occupation: number; pay_type: number; pay_type_code: string; pay_type_name: string;
  amount: string | null; percent: string | null; quantity: string | null; sort: number }

export interface FormulaVariable { name: string; ro: string; ru: string; en: string }
export interface FormulaCatalog { variables: FormulaVariable[]; functions: FormulaVariable[]; constants: { code: string; name: string }[]
  hour_variables?: FormulaVariable[]; hour_types?: { code: string; name_ro: string; name_ru: string; name_en: string }[] }
export interface FormulaCheck { ok: boolean; error?: string; position?: number; variables?: string[]; constants?: string[]; refs?: string[] }
export interface TryTrace { code: string; name: string; expression: string; error: string; result: string | null; note: string;
  variables: { name: string; value: string; description: string }[]; negative?: boolean }
export interface TryLine { employment: number; employment_label: string; result: string; notes: string[]; traces: TryTrace[]; error: string;
  items: { code: string; name: string; category: string; amount: string; note: string }[]; gross: string; deductions: string }
export interface TryResult { employee?: number; employee_name?: string; lines: TryLine[]; errors: string[] }

export interface Dependent {
  id?: number
  family_member: number | null
  name: string
  idnp: string
  birth_date: string | null
  relation: 'child' | 'parent' | 'sibling' | 'other'
  disability: '' | 'childhood' | 'severe' | 'accentuated' | 'medium'
  date_from: string | null
  date_to: string | null
  document: string
  income_ok: boolean
  note?: string
  code?: 'N' | 'H'
}

export interface ExemptionRequest {
  id: number
  employee: number
  number: string
  date: string
  date_from: string | null
  date_to: string | null
  kind: 'none' | 'personal' | 'major'
  major_category: string
  major_document: string
  spouse_major: boolean
  spouse_name: string
  spouse_idnp: string
  spouse_category: string
  spouse_document: string
  waiver_date: string | null
  place: 'main' | 'secondary'
  place_label: string
  documents: string
  needs_review: boolean
  review_note: string
  is_active: boolean
  dependents: Dependent[]
  code: string
  code_now: string
  warnings: string[]
}

export interface PayrollItem {
  id: number
  line: number
  pay_type: number
  code: string
  name: string
  category: 'accrual' | 'deduction' | 'employer'
  quantity: string | null
  base: string | null
  percent: string | null
  amount: string
  taxable_part: string
  manual: boolean
  note: string
}

export interface PayrollLine {
  id: number
  employee: number
  employee_name: string
  employment: number
  info: {
    occupation: string; subdivision: string; kind: string; kind_label: string; rate: number; base_salary: number; salary_full: number
    hourly: number; tab_number: string; name: string; is_main: boolean
    timesheet: { days: number; hours: number; night: number; holiday: number; norm: number; overtime: number; codes: Record<string, number>; assumed?: boolean }
  }
  /** brutul, bazele impozitului și CNAM (impozitul și CNAM se rețin la plată), CAS, celelalte rețineri și restul înainte de impozit */
  gross: string
  taxable: string
  cnam_base: string
  cas: string
  deductions: string
  net: string
  /** IT Park: salariul din CIM e impozitat final (fără impozit, CNAM, CAS) */
  it_park?: boolean
  note: string
  items: PayrollItem[]
}

export interface Payroll {
  id: number
  deletion_mark?: boolean
  number: string
  date: string
  year: number
  month: number
  subdivision: number | null
  subdivision_name: string
  status: 'draft' | 'checked' | 'approved'
  status_label: string
  totals: Record<string, number>
  note: string
  lines_count: number
  calculated_at: string | null
  approved_at: string | null
  /** luna calculului e în regimul IT Park */
  it_park?: boolean
}

/** O îndreptare spre plată făcută în baza calculului (legătura Calcul → Îndreptare). */
export interface PayrollPaymentRef { id: number; number: string; date: string; status: Payment['status']; status_label: string }

export interface PayrollReport extends Payroll {
  lines: PayrollLine[]
  types: PayType[]
  payments: PayrollPaymentRef[]
}

/** Tipurile care se rețin la plată, nu în calcul: nu se corectează în calcul. */
export const AT_PAYMENT_AUTOS = ['advance', 'income_tax', 'cnam']

export const PAYROLL_STATUS_COLOR: Record<string, string> = { draft: 'gold', checked: 'blue', approved: 'green' }
export const FORMULAS = ['auto', 'fixed', 'pct_salary', 'pct_base', 'hourly', 'scale', 'expr']
/** Formulele care se pot calcula și fără rândul angajatului („pentru toți angajații”). */
export const GENERAL_FORMULAS = ['expr', 'scale', 'pct_salary', 'pct_base']
export const AUTO_KEYS = ['none', 'salary', 'allowance', 'combination', 'hour_types', 'piece', 'piece_prog', 'night', 'holiday', 'overtime', 'leave', 'leave_comp', 'sick', 'sick_accident',
  'min_wage', 'bonus', 'aid', 'income_tax', 'cnam', 'cas', 'cas_min']

export const money = (v: string | number | null | undefined) =>
  v === null || v === undefined || v === '' || Number(v) === 0 ? '' : Number(v).toLocaleString('ro-MD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export interface Payment {
  id: number
  deletion_mark?: boolean
  number: string
  date: string
  year: number
  month: number
  kind: 'salary' | 'advance'
  kind_label: string
  /** calculul de bază (doar la salariu); null — pe sold: restul lunii din toate calculele aprobate */
  payroll: number | null
  payroll_number: string
  method: 'all' | 'card' | 'cash'
  method_label: string
  status: 'draft' | 'approved' | 'paid'
  status_label: string
  paid_on: string | null
  reference: string
  note: string
  totals: { card: number; cash: number; total: number; gross: number; exemption: number; cnam: number; income_tax: number; deductions: number; count: number }
  /** luna pentru care se plătește e în regimul IT Park */
  it_park?: boolean
}

export interface PaymentLine {
  id: number
  payment: number
  employee: number
  employee_name: string
  tab_number: string
  method: 'card' | 'cash'
  iban: string
  /** impozitul se reține aici: brutul, scutirea, CNAM, impozitul, alte rețineri și netul (amount) */
  gross: string
  exemption: string
  cnam: string
  income_tax: string
  deductions: string
  amount: string
  /** partea impozitată final (IT Park) din venitul achitat */
  final_gross?: string
  manual: boolean
  note: string
}

/** Trimiterea fluturașilor pe e-mail: cine poate primi (are e-mail și IDNP) și ultima trimitere. */
export interface PayslipMailRow {
  employee: number
  name: string
  email: string
  problem: string
  last: { status: 'sent' | 'skipped' | 'error'; message: string; email: string; sent_at: string } | null
}
export interface PayslipMailSummary { rows: PayslipMailRow[]; ready: number; smtp: boolean }
export interface PayslipMailResult { employee: number; name: string; email: string; status: 'sent' | 'skipped' | 'error'; message: string }

export interface DebtRow { employee: number; name: string; tab_number: string; owed: number; paid: number; debt: number }

export const PAYMENT_STATUS_COLOR: Record<string, string> = { draft: 'gold', approved: 'blue', paid: 'green' }

/** Descarcă un fișier de la API cu sesiunea curentă (Excel, CSV pentru bancă). */
export async function downloadFile(url: string, params: Record<string, unknown>, filename: string) {
  const { api } = await import('./client')
  const r = await api.get(url, { params, responseType: 'blob' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(r.data as Blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

/** Regimul fiscal al întreprinderii pe luni (Setări → Constantele salarizării). */
export interface FiscalRegime {
  id: number
  regime: 'general' | 'it_park'
  regime_label: string
  date_from: string
  status_date: string | null
  document: string
  note: string
}

/** Un angajat la numărul din IU17 (rd. 020): cel puțin o zi lucrată sub CIM. */
export interface ItParkPerson {
  employee: number; name: string; tab_number: string; idnp: string; worked_days: number; maternity: boolean; jobs: string[]
  job_list: { kind: string; occupation: string; rate: number }[]
  source: 'timesheet' | 'calendar'; counted: boolean; reason: string; reason_code: 'worked' | 'maternity' | 'none'
}
export interface ItParkRow { code: string; label: string; base: number | null; rate: string; amount: number; basis: string }
/** Calculul impozitului unic al lunii (IU17). */
export interface ItParkMonthData {
  year: number; month: number; it_park: boolean; sales_income: number | null; sales_entered: boolean; submitted_on: string | null
  note: string; employees: number; persons: number; per_employee: number; tax_pct: number; min_pct: number; avg_salary: number
  by_sales: number; minimum: number; due: number; rule: 'sales' | 'minimum'; deadline: string; rows: ItParkRow[]; people?: ItParkPerson[]
}
export interface ItParkYear { year: number; regime: 'general' | 'it_park'; regimes: FiscalRegime[]; months: ItParkMonthData[] }

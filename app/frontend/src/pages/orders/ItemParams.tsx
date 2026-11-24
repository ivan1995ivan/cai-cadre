import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Col, DatePicker, Form, Input, InputNumber, Row, Select, Typography, type FormInstance } from 'antd'
import dayjs from 'dayjs'

import { api } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { StaffList } from '../../api/org'
import { fmtDays, type Balance, type LeaveSchedule } from '../../api/leave'
import { RateInput, fmtRate, rateProps } from '../../components/RateInput'
import type { Absence, SanctionRec } from '../../api/orders'
import { EMPLOYMENT_KINDS, PAY_MODES, type Employment, type PayMode } from '../../api/staff'
import RefSelect from '../../components/RefSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import type { OccupationPayItem, PlannedRow } from '../../api/payroll'
import { useApp } from '../../auth/AppContext'
import PlannedRowsInput from '../payroll/PlannedRows'
import { CombinationFields, HourRatesInput, combinationPay, type HourRateRow } from '../worktime/HourRates'

export const DATE_KEYS = ['date_from', 'date_to', 'probation_until', 'contract_date', 'work_year_from', 'work_year_to']

/** Ordinele cu tabelul „Acumulări și rețineri” (apps.orders.effects.has_pay_items): angajarea, transferul, condițiile,
 *  salariul, sporurile, cumulul / suplinirea și reținerea din salariu. */
export const hasPayItems = (effect: string, code: string) => ['hire', 'change', 'salary', 'substitution'].includes(effect) || code === 'deduction'
/** Ordinele cu tabelul „Tarife pe tipuri de ore” (apps.orders.effects.has_hour_rates); la cumulare pe același contract — nu. */
export const hasHourRates = (effect: string) => ['hire', 'change', 'salary', 'substitution'].includes(effect)

const LEAVE_KIND: Record<string, string> = {
  leave_annual: 'annual', leave_extra: 'extra', leave_unpaid: 'unpaid', leave_maternity: 'maternity', leave_paternity: 'paternity',
  leave_childcare: 'childcare', leave_childcare_unpaid: 'childcare_unpaid', leave_study: 'study', days_off_paid: 'days_off',
  travel: 'travel', training: 'training', idle: 'idle', tech_unemployment: 'tech_unemployment',
}

/** Parametrii unui punct al ordinului, după efectul tipului (angajare, modificare, concediu, sancțiune...). */
export default function ItemParams({ form, effect, code, employee, disabled, onChange }: {
  form: FormInstance
  /** valorile puse de program (nu de om): `setFieldValue` nu declanșează `onValuesChange` — ordinul trebuie să știe că s-a schimbat */
  onChange?: () => void
  effect: string
  code: string
  employee: number | null
  disabled: boolean
}) {
  const { t } = useTranslation()
  const { data: jobs } = useFetch<Employment[]>(employee ? '/staff/employments/' : null, { employee })
  const needAbsences = code === 'leave_recall' || code === 'leave_postpone'
  const { data: absences } = useFetch<Absence[]>(needAbsences && employee ? '/orders/absences/' : null, { employee })
  const { data: sanctions } = useFetch<SanctionRec[]>(code === 'sanction_lift' && employee ? '/orders/sanctions/' : null, { employee })
  const { data: drafts } = useFetch<{ results: StaffList[] }>(effect === 'staff_list' ? '/org/staff-lists/' : null, { status: 'draft' })
  const { data: bal } = useFetch<Balance>((code === 'leave_annual' || code === 'leave_compensation') && employee && !disabled
    ? `/leave/balance/${employee}/` : null)
  const childLeave = code === 'leave_childcare' || code === 'leave_childcare_unpaid'
  const { data: family } = useFetch<{ id: number; full_name: string; birth_date: string | null }[]>(
    childLeave && employee && !disabled ? '/staff/family/' : null, { employee })
  const { data: schedules } = useFetch<{ results: LeaveSchedule[] }>(code === 'leave_schedule' && !disabled ? '/leave/schedules/' : null,
    { status: 'submitted', page_size: 500 })
  const jobOptions = (jobs ?? []).filter((j) => j.status !== 'ended')
    .map((j) => ({ value: j.id, label: `${j.kind_label}: ${j.occupation_name}, ${j.subdivision_name} (${fmtRate(j.rate)})` }))
  const leaveKind = LEAVE_KIND[code]
  const { branding } = useApp()
  const payItems = hasPayItems(effect, code) && branding?.payroll_enabled !== false
  // la angajare: tabelul se completează din acumulările-tip ale funcției (cât e gol), apoi se corectează de mână
  const occupation = Form.useWatch('occupation', form)
  const fromOccupation = (force: boolean) => {
    const occ = form.getFieldValue('occupation')
    if (!occ) return
    const current = form.getFieldValue('pay_items') as PlannedRow[] | undefined
    if (!force && current && current.length) return
    api.get<OccupationPayItem[]>('/payroll/occupation-items/', { params: { occupation: occ } }).then((r) => {
      const rows: PlannedRow[] = r.data.map((x) => ({ pay_type: x.pay_type, action: 'add', amount: x.amount, percent: x.percent,
        quantity: x.quantity, date_from: null, date_to: null, document: '' }))
      if (force || rows.length) {
        form.setFieldValue('pay_items', rows)
        onChange?.()
      }
    }).catch(() => {})
  }
  // tarifele pe tipuri de ore: la angajare — din tarifele-tip ale funcției (cât tabelul e gol)
  const ratesFromOccupation = (force: boolean) => {
    const occ = form.getFieldValue('occupation')
    if (!occ) return
    const current = form.getFieldValue('hour_rates') as HourRateRow[] | undefined
    if (!force && current && current.length) return
    api.get<{ hour_type: number; rate: string; guaranteed_hours: string | null }[]>('/worktime/occupation-hour-rates/', { params: { occupation: occ } })
      .then((r) => {
        const rows: HourRateRow[] = r.data.map((x) => ({ hour_type: x.hour_type, action: 'add', rate: x.rate, guaranteed_hours: x.guaranteed_hours,
          date_from: null, date_to: null, document: '' }))
        if (force || rows.length) {
          form.setFieldValue('hour_rates', rows)
          onChange?.()
        }
      }).catch(() => {})
  }
  useEffect(() => {
    if (effect === 'hire' && payItems && !disabled && occupation) fromOccupation(false)
    if (effect === 'hire' && !disabled && occupation) ratesFromOccupation(false)
  }, [occupation]) // eslint-disable-line react-hooks/exhaustive-deps
  const combMode = Form.useWatch('mode', form) as string | undefined
  const combAction = Form.useWatch('action', form) as string | undefined
  const combPay = Form.useWatch('pay_mode', form) as string | undefined
  const chosenJob = Form.useWatch('employment', form) as number | undefined
  const allJobs = jobs ?? []
  const baseJob = allJobs.find((j) => j.id === chosenJob) ?? allJobs.find((j) => j.status !== 'ended' && ['main', 'main_student'].includes(j.kind))
    ?? allJobs.find((j) => j.status !== 'ended')
  // modalitatea care decide dacă tarifele se plătesc: cea din ordin; la modificare, dacă nu se schimbă, — cea a raportului
  const rateMode = (effect === 'hire' || (effect === 'substitution' && combMode === 'separate') ? combPay || 'salary'
    : combPay || baseJob?.pay_mode) as PayMode | undefined
  const showRates = hasHourRates(effect) && !(effect === 'substitution' && combMode !== 'separate')
  const [calc, setCalc] = useState<{ to: string; days: number; holidays: string[] } | null>(null)

  // concediul: zilele ↔ data de sfârșit, fără sărbători (calculat pe server)
  const from = Form.useWatch('date_from', form)
  const days = Form.useWatch('days', form)
  const to = Form.useWatch('date_to', form)
  useEffect(() => {
    if (!leaveKind || !from || disabled) return
    const params: Record<string, string | number> = { from: from.format('YYYY-MM-DD'), kind: leaveKind }
    if (days) params.days = days
    else if (to) params.to = to.format('YYYY-MM-DD')
    else return
    api.get('/orders/leave-days/', { params }).then((r) => {
      setCalc(r.data)
      if (days && (!to || to.format('YYYY-MM-DD') !== String(r.data.to).slice(0, 10))) form.setFieldValue('date_to', dayjs(r.data.to))
    }).catch(() => setCalc(null))
  }, [leaveKind, from, days, to, disabled, form])

  // concediile sociale: zilele legale (maternitate 126, paternal 14) și perioada după vârsta copilului
  useEffect(() => {
    if (disabled || !from || form.getFieldValue('days') || form.getFieldValue('date_to')) return
    if (code === 'leave_maternity') form.setFieldValue('days', 126)
    if (code === 'leave_paternity') form.setFieldValue('days', 14)
  }, [code, from, disabled, form])
  const pickChild = (child: number) => {
    const kind = code === 'leave_childcare' ? 'childcare' : 'childcare_unpaid'
    const start = form.getFieldValue('date_from')
    api.get('/leave/social-dates/', { params: { kind, child, from: start ? start.format('YYYY-MM-DD') : undefined } }).then((r) => {
      form.setFieldsValue({ date_from: dayjs(r.data.from), date_to: dayjs(r.data.to), days: undefined })
    }).catch(() => {})
  }
  const oldestYear = () => {
    const y = (bal?.years ?? []).find((x) => x.available > 0) ?? bal?.years[bal.years.length - 1]
    if (y) form.setFieldsValue({ work_year_from: dayjs(y.from), work_year_to: dayjs(y.to) })
  }

  const date = (name: string, label: string, required = false) => (
    <Form.Item name={name} label={label} rules={required ? [{ required: true }] : []}>
      <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
    </Form.Item>
  )
  const num = (name: string, label: string, max?: number) => (
    <Form.Item name={name} label={label}><InputNumber min={0} max={max} style={{ width: '100%' }} /></Form.Item>
  )
  const rate = <Form.Item name="rate" label={t('staff.rate')} {...rateProps}><RateInput /></Form.Item>
  const job = <Form.Item name="employment" label={t('ord.p.employment')} extra={t('ord.p.employmentHint')}>
    <Select allowClear options={jobOptions} /></Form.Item>
  const post = (withKind: boolean) => (
    <>
      {withKind && <Col xs={24} md={12}><Form.Item name="kind" label={t('staff.kind')}>
        <Select options={EMPLOYMENT_KINDS.map((k) => ({ value: k, label: t(`staff.kinds.${k}`) }))} /></Form.Item></Col>}
      <Col xs={24} md={12}><Form.Item name="subdivision" label={t('org.subdivision')}><SubdivisionSelect /></Form.Item></Col>
      <Col xs={24} md={12}><Form.Item name="occupation" label={t('org.sl.position')}><RefSelect spec="occupation" /></Form.Item></Col>
      <Col xs={24} md={12}>{rate}</Col>
      <Col xs={24} md={12}>{num('base_salary', t('org.sl.salary'))}</Col>
      <Col xs={24} md={12}>{num('allowance_pct', t('org.sl.allowance'), 500)}</Col>
      <Col xs={24} md={12}><Form.Item name="pay_mode" label={t('ht.payMode')} tooltip={t('ht.payModeHint')}>
        <Select allowClear options={PAY_MODES.map((k) => ({ value: k, label: t(`ht.payModes.${k}`) }))} /></Form.Item></Col>
      <Col xs={24} md={12}>{num('hourly_rate', t('ht.hourlyRate'))}</Col>
    </>
  )

  let body: React.ReactNode = null
  if (effect === 'hire') {
    body = <Row gutter={24}>{post(true)}
      <Col xs={24} md={12}>{date('date_from', t('staff.hiredOn'), true)}</Col>
      <Col xs={24} md={12}>{date('date_to', t('staff.job.dateTo'))}</Col>
      <Col xs={24} md={12}>{date('probation_until', t('staff.job.probation'))}</Col>
      <Col xs={24} md={12}><Form.Item name="contract_number" label={t('staff.job.contractNo')}><Input /></Form.Item></Col>
      <Col xs={24} md={12}>{date('contract_date', t('staff.job.contractDate'))}</Col>
    </Row>
  } else if (effect === 'change' || effect === 'salary') {
    body = <Row gutter={24}>
      <Col xs={24}>{job}</Col>
      <Col xs={24} md={12}>{date('date_from', t('staff.job.from'), code !== 'extend_contract')}</Col>
      {code === 'extend_contract' && <Col xs={24} md={12}>{date('date_to', t('ord.p.newTerm'), true)}</Col>}
      {code !== 'extend_contract' && code !== 'change_terms' && post(false)}
      {(code === 'change_terms' || code === 'hours_change') && <Col xs={24}><Form.Item name="text" label={t('ord.p.whatChanges')}><Input.TextArea rows={2} /></Form.Item></Col>}
    </Row>
  } else if (effect === 'substitution') {
    const existing = allJobs.flatMap((j) => (j.combinations ?? []).map((c) => ({ ...c, job: j })))
    body = <Row gutter={24}>
      <Col xs={24}><Form.Item name="mode" label={t('ht.comb.how')} extra={t(combMode === 'separate' ? 'ht.comb.separateHint' : 'ht.comb.onBaseHint')}>
        <Select options={[{ value: 'on_base', label: t('ht.comb.modes.on_base') }, { value: 'separate', label: t('ht.comb.modes.separate') }]}
          placeholder={t('ht.comb.modes.on_base')} /></Form.Item></Col>
      {combMode !== 'separate' && <Col xs={24} md={12}><Form.Item name="action" label={t('ht.comb.action')}>
        <Select options={[{ value: 'add', label: t('ht.comb.actions.add') }, { value: 'stop', label: t('ht.comb.actions.stop') }]}
          placeholder={t('ht.comb.actions.add')} /></Form.Item></Col>}
      {combMode !== 'separate' && <Col xs={24} md={12}>{job}</Col>}
      {combMode !== 'separate' && combAction === 'stop' ? <>
        <Col xs={24}><Form.Item name="combination" label={t('ht.comb.title')} rules={[{ required: true }]}>
          <Select options={existing.filter((c) => !c.date_to || c.date_to >= dayjs().format('YYYY-MM-DD')).map((c) => ({ value: c.id,
            label: `${t(`ht.comb.kinds.${c.kind}`)}: ${c.occupation_name} — ${combinationPay(t, c)} (${dayjs(c.date_from).format('DD.MM.YYYY')} – ${c.date_to ? dayjs(c.date_to).format('DD.MM.YYYY') : '…'})` }))} />
        </Form.Item></Col>
        <Col xs={24} md={12}>{date('date_to', t('ht.comb.lastDay'), true)}</Col>
      </> : combMode !== 'separate' ? <>
        <Col xs={24}><CombinationFields form={form} payMode={combPay} withKind={false} /></Col>
      </> : <>
        <Col xs={24} md={12}><Form.Item name="kind" label={t('staff.kind')}><Select allowClear options={['substitute', 'internal'].map((k) => ({ value: k, label: t(`staff.kinds.${k}`) }))} /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="subdivision" label={t('org.subdivision')}><SubdivisionSelect /></Form.Item></Col>
        <Col xs={24}><Form.Item name="occupation" label={t('ord.p.postTaken')}><RefSelect spec="occupation" /></Form.Item></Col>
        <Col xs={24} md={12}>{rate}</Col>
        <Col xs={24} md={12}>{num('base_salary', t('org.sl.salary'))}</Col>
        <Col xs={24} md={12}><Form.Item name="pay_mode" label={t('ht.payMode')}>
          <Select allowClear options={PAY_MODES.map((k) => ({ value: k, label: t(`ht.payModes.${k}`) }))} /></Form.Item></Col>
        <Col xs={24} md={12}>{num('hourly_rate', t('ht.hourlyRate'))}</Col>
        <Col xs={24} md={12}><Form.Item name="substituted_name" label={t('ord.p.substituted')}><Input /></Form.Item></Col>
        <Col xs={24} md={12}>{date('date_from', t('staff.sen.from'), true)}</Col>
        <Col xs={24} md={12}>{date('date_to', t('staff.sen.to'))}</Col>
      </>}
    </Row>
  } else if (effect === 'suspend' || effect === 'resume') {
    body = <Row gutter={24}>
      <Col xs={24}>{job}</Col>
      <Col xs={24} md={12}>{date('date_from', t('staff.job.from'), true)}</Col>
      {effect === 'suspend' && <Col xs={24}><Form.Item name="reason" label={t('staff.job.suspensionReason')} rules={[{ required: true }]}>
        <Input placeholder={t('staff.job.suspensionPlaceholder')} /></Form.Item></Col>}
    </Row>
  } else if (effect === 'terminate') {
    body = <Row gutter={24}>
      <Col xs={24}>{job}</Col>
      <Col xs={24} md={12}>{date('date_from', t('staff.job.endDate'), true)}</Col>
      <Col xs={24} md={12}>{num('compensation_days', t('ord.p.compensation'))}</Col>
      <Col xs={24}><Form.Item name="reason" label={t('staff.job.reason')} rules={[{ required: true }]}><RefSelect spec={{ dict: 'termination' }} /></Form.Item></Col>
    </Row>
  } else if (code === 'leave_postpone') {
    body = <Row gutter={24}>
      <Col xs={24}><Form.Item name="absence" label={t('ord.p.absence')} extra={t('lv.ord.postponeHint')}>
        <Select allowClear options={(absences ?? []).filter((a) => !a.recalled_on && ['annual', 'extra'].includes(a.kind)
          && a.date_from > dayjs().format('YYYY-MM-DD')).map((a) => ({ value: a.id,
          label: `${a.kind_label} ${dayjs(a.date_from).format('DD.MM.YYYY')} – ${dayjs(a.date_to).format('DD.MM.YYYY')}` }))} /></Form.Item></Col>
      <Col xs={24} md={12}>{date('date_from', t('lv.ord.newStart'), true)}</Col>
      <Col xs={24} md={12}>{num('days', t('ord.p.days'), 120)}</Col>
      <Col xs={24}><Form.Item name="note" label={t('ord.p.note')}><Input /></Form.Item></Col>
    </Row>
  } else if (code === 'leave_compensation') {
    body = <Row gutter={24}>
      <Col xs={24} md={12}><Form.Item name="days" label={t('ord.p.days')} rules={[{ required: true }]}>
        <InputNumber min={0.01} step={0.5} style={{ width: '100%' }} /></Form.Item></Col>
      <Col xs={24} md={12}>{date('work_year_from', t('ord.p.workYearFrom'))}</Col>
      {bal && <Col xs={24}><Typography.Paragraph type="secondary">{t('lv.ord.balance', { available: fmtDays(bal.available), remaining: fmtDays(bal.remaining) })}</Typography.Paragraph></Col>}
    </Row>
  } else if (code === 'leave_schedule') {
    body = <Row gutter={24}>
      <Col xs={24}><Form.Item name="schedules" label={t('menu.leaveSchedule')} extra={t('lv.ord.scheduleHint')}>
        <Select mode="multiple" allowClear options={(schedules?.results ?? []).map((x) => ({ value: x.id, label: `${x.year} · ${x.subdivision_name}` }))} />
      </Form.Item></Col>
      <Col xs={24} md={12}>{num('year', t('lv.sch.year'))}</Col>
    </Row>
  } else if (effect === 'leave' || effect === 'travel' || code === 'training' || effect === 'idle') {
    body = <Row gutter={24}>
      {effect !== 'travel' && code !== 'training' && <Col xs={24}>{job}</Col>}
      <Col xs={24} md={12}>{date('date_from', t('staff.sen.from'), true)}</Col>
      <Col xs={24} md={12}><Form.Item name="days" label={t('ord.p.days')}><InputNumber min={1} max={1500} style={{ width: '100%' }} /></Form.Item></Col>
      <Col xs={24} md={12}>{date('date_to', t('staff.sen.to'))}</Col>
      {childLeave && <Col xs={24}><Form.Item name="child" label={t('lv.ord.child')} extra={t('lv.ord.childHint')}>
        <Select allowClear onChange={(v) => v && pickChild(v)} options={(family ?? []).filter((m) => m.birth_date)
          .map((m) => ({ value: m.id, label: `${m.full_name} (${dayjs(m.birth_date).format('DD.MM.YYYY')})` }))} /></Form.Item></Col>}
      {code === 'leave_annual' && <><Col xs={24} md={12}>{date('work_year_from', t('ord.p.workYearFrom'))}</Col><Col xs={24} md={12}>{date('work_year_to', t('ord.p.workYearTo'))}</Col>
        {bal && <Col xs={24}><Typography.Paragraph type="secondary">
          {t('lv.ord.balance', { available: fmtDays(bal.available), remaining: fmtDays(bal.remaining) })}{' '}
          {!disabled && <Button size="small" type="link" onClick={oldestYear}>{t('lv.ord.oldestYear')}</Button>}
          {t('lv.ord.yearAuto')}</Typography.Paragraph></Col>}</>}
      {(effect === 'travel' || code === 'training') && <>
        <Col xs={24}><Form.Item name="destination" label={t('ord.p.destination')} rules={[{ required: true }]}><Input /></Form.Item></Col>
        <Col xs={24}><Form.Item name="purpose" label={t('ord.p.purpose')}><Input /></Form.Item></Col></>}
      {code === 'idle' && <Col xs={24} md={12}><Form.Item name="cause" label={t('ord.p.idleCause')} rules={[{ required: true }]}
        initialValue="nobody" extra={t('ord.p.idleCauseHint')}>
        <Select options={['employer', 'nobody', 'worker'].map((k) => ({ value: k, label: t(`ord.p.idleCauses.${k}`) }))} /></Form.Item></Col>}
      {effect === 'idle' && <Col xs={24} md={12}><Form.Item name="pay_pct" label={t('ord.p.idlePct')}
        extra={t(code === 'idle' ? 'ord.p.idlePctHint' : 'ord.p.techPctHint')}>
        <InputNumber min={0} max={100} step={1} style={{ width: '100%' }} suffix="%" /></Form.Item></Col>}
      {effect === 'idle' && <Col xs={24}><Alert type="info" showIcon title={t('ord.p.idleHint')} /></Col>}
      {(effect === 'leave' || effect === 'idle') && code !== 'leave_annual' && <Col xs={24}><Form.Item name="note" label={t('ord.p.note')}><Input /></Form.Item></Col>}
      {calc && !disabled && <Col xs={24}><Alert type="info" showIcon title={t('ord.p.calc', {
        days: calc.days, to: dayjs(calc.to).format('DD.MM.YYYY'), holidays: calc.holidays.length })} /></Col>}
    </Row>
  } else if (effect === 'leave_recall') {
    body = <Row gutter={24}>
      <Col xs={24}><Form.Item name="absence" label={t('ord.p.absence')} rules={[{ required: true }]}>
        <Select options={(absences ?? []).filter((a) => !a.recalled_on).map((a) => ({ value: a.id,
          label: `${a.kind_label} ${dayjs(a.date_from).format('DD.MM.YYYY')} – ${dayjs(a.date_to).format('DD.MM.YYYY')}` }))} /></Form.Item></Col>
      <Col xs={24} md={12}>{date('date_from', t('ord.p.returnDate'), true)}</Col>
    </Row>
  } else if (effect === 'incentive') {
    body = <Row gutter={24}>
      <Col xs={24} md={12}>{num('amount', t('ord.p.amount'))}</Col>
      {code === 'bonus' && <Col xs={24} md={12}>{num('percent', t('ord.p.percent'), 500)}</Col>}
      <Col xs={24} md={12}>{date('date_from', t('ord.date'))}</Col>
      <Col xs={24}><Form.Item name="note" label={t('ord.p.forWhat')}><Input /></Form.Item></Col>
    </Row>
  } else if (effect === 'sanction') {
    body = code === 'sanction_lift' ? <Row gutter={24}>
      <Col xs={24}><Form.Item name="sanction_record" label={t('ord.p.sanctionRecord')} rules={[{ required: true }]}>
        <Select options={(sanctions ?? []).filter((s) => !s.lifted_on).map((s) => ({ value: s.id, label: `${s.kind_name} ${dayjs(s.date).format('DD.MM.YYYY')}` }))} /></Form.Item></Col>
      <Col xs={24} md={12}>{date('date_from', t('ord.date'))}</Col>
      <Col xs={24}><Form.Item name="note" label={t('ord.p.note')}><Input /></Form.Item></Col>
    </Row> : <Row gutter={24}>
      <Col xs={24} md={12}><Form.Item name="sanction" label={t('ord.p.sanction')} rules={[{ required: true }]}><RefSelect spec={{ dict: 'sanction' }} /></Form.Item></Col>
      <Col xs={24} md={12}>{date('date_from', t('ord.date'))}</Col>
      <Col xs={24}><Form.Item name="misconduct" label={t('ord.p.misconduct')} rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item></Col>
    </Row>
  } else if (code === 'deduction') {
    body = <Row gutter={24}>
      <Col xs={24} md={12}>{num('amount', t('ord.p.amount'))}</Col>
      <Col xs={24} md={12}>{num('percent', t('ord.p.deductionPercent'), 100)}</Col>
      <Col xs={24} md={12}>{date('date_from', t('ord.p.fromDate'), true)}</Col>
      <Col xs={24}><Form.Item name="note" label={t('ord.p.deductionBasis')} extra={t('ord.p.deductionHint')}><Input /></Form.Item></Col>
    </Row>
  } else if (code === 'medical_exam') {
    body = <Row gutter={24}>
      <Col xs={24} md={12}>{date('date_to', t('ord.p.until'), true)}</Col>
      <Col xs={24}><Form.Item name="note" label={t('ord.p.note')}><Input /></Form.Item></Col>
    </Row>
  } else if (effect === 'qualification') {  // grupa „formare” (cursuri, alte trimiteri): perioada și specialitatea
    body = <Row gutter={24}>
      <Col xs={24} md={12}><Form.Item name="specialty" label={t('staff.edu.specialty')}>
        <RefSelect spec="specialty" /></Form.Item></Col>
      <Col xs={24} md={12}>{date('date_from', t('ord.date'))}</Col>
      <Col xs={24} md={12}>{date('date_to', t('ord.p.until'))}</Col>
    </Row>
  } else if (effect === 'staff_list') {
    body = <Form.Item name="staff_list" label={t('menu.staffList')} rules={[{ required: true }]} extra={t('ord.p.staffListHint')}>
      <Select options={(drafts?.results ?? []).map((s) => ({ value: s.id, label: `${dayjs(s.effective_from).format('DD.MM.YYYY')}${s.number ? ' · nr. ' + s.number : ''}` }))} />
    </Form.Item>
  } else if (effect === 'cancel') {
    body = <Typography.Text>{t('ord.p.cancels')}: <b>{String(form.getFieldValue('cancelled_label') ?? '')}</b></Typography.Text>
  } else {
    body = <Row gutter={24}>
      {effect === 'worktime' && <><Col xs={24} md={12}>{date('date_from', t('ord.date'))}</Col><Col xs={24} md={12}>{num('hours', t('ord.p.hours'), 24)}</Col></>}
    </Row>
  }

  return (
    <>
      {body}
      {showRates && <Form.Item name="hour_rates" label={t('ht.rates.title')}>
        <HourRatesInput existing={effect === 'hire' || effect === 'substitution' ? [] : baseJob?.hour_rates ?? []} disabled={disabled}
          mode={rateMode ?? null} onFromOccupation={effect === 'hire' ? () => ratesFromOccupation(true) : undefined} />
      </Form.Item>}
      {payItems && <Form.Item name="pay_items" label={t('pay.pl.title')}>
        <PlannedRowsInput employee={employee} disabled={disabled} onFromOccupation={effect === 'hire' ? () => fromOccupation(true) : undefined} />
      </Form.Item>}
      {effect !== 'cancel' && (effect === 'none' || effect === 'worktime' || code === 'schedule' || code === 'appoint_responsible'
        || code === 'leave_schedule' || code === 'staff_list') && (
        <Form.Item name="text" label={t('ord.p.text')}><Input.TextArea rows={3} /></Form.Item>
      )}
      <Form.Item name="cancelled_label" hidden><Input /></Form.Item>
      <Form.Item name="order" hidden><Input /></Form.Item>
    </>
  )
}

/** Parametrii din formular → JSON pentru server (datele ca AAAA-LL-ZZ, câmpurile goale scoase). */
export function paramsOut(values: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(values)) {
    if (v === undefined || v === null || v === '') continue
    out[k] = dayjs.isDayjs(v) ? v.format('YYYY-MM-DD') : v
  }
  return out
}

export function paramsIn(params: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(params ?? {}).map(([k, v]) => [k, DATE_KEYS.includes(k) && v ? dayjs(String(v)) : v]))
}

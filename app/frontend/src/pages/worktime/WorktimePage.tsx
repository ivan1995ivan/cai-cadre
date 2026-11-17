import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, Form, InputNumber, Select, Space, Table, Tag, TimePicker, Typography, message } from 'antd'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { MonthNorm, ShiftType } from '../../api/worktime'
import { useApp } from '../../auth/AppContext'
import { useEditGuard } from '../../components/UnsavedGuard'

const WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const OFF = '-' // „liber” în editoarele de ture (pe server — șir gol)

/** Turele active (pentru alegerea din grafice și pontaj). */
export function useShifts() {
  const { data } = useFetch<ShiftType[]>('/worktime/shifts/', { active: 1 })
  return data ?? []
}

export function shiftOptions(shifts: ShiftType[], t: (k: string) => string, withOff = true) {
  return [
    ...(withOff ? [{ value: OFF, label: t('wt.off') }] : []),
    ...shifts.map((s) => ({ value: s.code, label: `${s.code} — ${s.name}` })),
  ]
}

/** Turele pe zilele săptămânii (valoarea: 7 coduri; gol = liber). */
function WeekInput({ value, onChange, shifts }: { value?: string[]; onChange?: (v: string[]) => void; shifts: ShiftType[] }) {
  const { t } = useTranslation()
  const week = value && value.length === 7 ? value : ['', '', '', '', '', '', '']
  return (
    <Space wrap>
      {WEEKDAYS.map((d, i) => (
        <Space key={d} orientation="vertical" size={0}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t(`wt.weekdays.${d}`)}</Typography.Text>
          <Select size="small" style={{ width: 110 }} value={week[i] || OFF} options={shiftOptions(shifts, t)}
            onChange={(v) => { const next = [...week]; next[i] = v === OFF ? '' : v; onChange?.(next) }} />
        </Space>
      ))}
    </Space>
  )
}

/** Turele ciclului, la rând („Z12, N12, liber, liber”). */
function CycleInput({ value, onChange, shifts }: { value?: string[]; onChange?: (v: string[]) => void; shifts: ShiftType[] }) {
  const { t } = useTranslation()
  return (
    <Select mode="multiple" style={{ width: '100%' }} value={(value ?? []).map((c) => c || OFF)} options={shiftOptions(shifts, t)}
      onChange={(v: string[]) => onChange?.(v.map((c) => (c === OFF ? '' : c)))} placeholder={t('wt.cycleHint')} />
  )
}

export type WorktimePart = 'schedules' | 'shifts' | 'calendar' | 'settings'

/** O setare a timpului de muncă (Administrare → Setări): graficele de lucru, turele, calendarul de producție sau regulile. */
export default function WorktimeSettingsPage({ part, title }: { part: WorktimePart; title: string }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('worktime.edit') || hasPerm('dictionaries.edit')
  const shifts = useShifts()

  const shiftFields: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 80 },
    { key: 'name', label: t('wt.shift.name'), required: true },
    { key: 'hours', label: t('wt.shift.hours'), type: 'number', required: true, width: 70 },
    { key: 'night_hours', label: t('wt.shift.night'), type: 'number', width: 90 },
    { key: 'start', label: t('wt.shift.start'), width: 90, input: () => <TimePicker format="HH:mm" minuteStep={30} style={{ width: '100%' }} />,
      render: (v) => (v ? String(v).slice(0, 5) : '') },
    { key: 'is_duty', label: t('wt.shift.duty'), type: 'bool', width: 70 },
    { key: 'color', label: t('wt.shift.color'), type: 'color', width: 90 },
    { key: 'sort', label: t('org.sort'), type: 'number', inTable: false },
  ]
  const scheduleFields: CrudField[] = [
    { key: 'code', label: t('common.code'), width: 80 },
    { key: 'name', label: t('wt.sch.name'), required: true },
    { key: 'kind', label: t('wt.sch.kind'), type: 'select', required: true, width: 170,
      options: [{ value: 'week', label: t('wt.sch.kinds.week') }, { value: 'cycle', label: t('wt.sch.kinds.cycle') }],
      render: (_v, r) => String(r.kind_label ?? '') },
    { key: 'weekly_hours', label: t('wt.sch.weeklyHours'), type: 'number', required: true, width: 90 },
    { key: 'week', label: t('wt.sch.week'), input: () => <WeekInput shifts={shifts} />,
      render: (v) => (Array.isArray(v) && v.some(Boolean) ? v.map((c) => c || '–').join(' ') : '') },
    { key: 'cycle', label: t('wt.sch.cycle'), input: () => <CycleInput shifts={shifts} />, extra: t('wt.sch.cycleExtra'),
      render: (v) => (Array.isArray(v) && v.length ? v.map((c) => c || '–').join(' ') : '') },
    { key: 'cycle_start', label: t('wt.sch.cycleStart'), type: 'date', inTable: false },
    { key: 'holidays_off', label: t('wt.sch.holidaysOff'), type: 'bool', width: 110 },
    { key: 'note', label: t('org.notes'), inTable: false },
    { key: 'jobs_count', label: t('wt.sch.jobs'), type: 'number', width: 90, render: (v) => String(v ?? 0) },
  ]

  const parts: Record<WorktimePart, React.ReactNode> = {
    schedules: (
      <CrudTable endpoint="/worktime/schedules/" fields={scheduleFields} canEdit={canEdit}
        defaults={{ kind: 'week', weekly_hours: 40, week: ['8', '8', '8', '8', '8', '', ''], cycle: [], holidays_off: true }}
        title={<Typography.Text type="secondary">{t('wt.sch.hint')}</Typography.Text>} />
    ),
    shifts: (
      <CrudTable endpoint="/worktime/shifts/" fields={shiftFields} canEdit={canEdit} defaults={{ hours: 8, night_hours: 0, is_duty: false }}
        title={<Typography.Text type="secondary">{t('wt.shift.hint')}</Typography.Text>} />
    ),
    calendar: <CalendarTab canEdit={canEdit} />,
    settings: <SettingsTab />,
  }
  return <Card title={title}>{parts[part]}</Card>
}

function CalendarTab({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation()
  const [year, setYear] = useState(dayjs().year())
  const [tick, setTick] = useState(0)
  const { data } = useFetch<{ months: MonthNorm[] }>('/worktime/calendar/', { year, tick })
  const fields: CrudField[] = [
    { key: 'date', label: t('ord.date'), type: 'date', required: true, width: 120 },
    { key: 'working', label: t('wt.cal.working'), type: 'bool', width: 110 },
    { key: 'hours_less', label: t('wt.cal.hoursLess'), type: 'number', width: 130 },
    { key: 'note', label: t('wt.cal.note') },
  ]
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={16}>
      <Space>
        <Select style={{ width: 110 }} value={year} onChange={setYear}
          options={Array.from({ length: 5 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />
        <Typography.Text type="secondary">{t('wt.cal.hint')}</Typography.Text>
      </Space>
      <Table<MonthNorm> size="small" rowKey="month" pagination={false} dataSource={data?.months ?? []} columns={[
        { title: t('wt.cal.month'), dataIndex: 'month', width: 130, render: (m: number) => dayjs().month(m - 1).format('MMMM') },
        { title: t('wt.cal.calendarDays'), dataIndex: 'calendar_days', width: 110, align: 'right' },
        { title: t('wt.cal.workingDays'), dataIndex: 'working_days', width: 110, align: 'right' },
        { title: '40 h', dataIndex: 'norm_40', width: 80, align: 'right' },
        { title: '35 h', dataIndex: 'norm_35', width: 80, align: 'right' },
        { title: '30 h', dataIndex: 'norm_30', width: 80, align: 'right' },
        { title: t('wt.cal.holidays'), dataIndex: 'holidays', render: (v: string[]) => v.map((d) => <Tag key={d}>{dayjs(d).format('DD.MM')}</Tag>) },
      ]} />
      <CrudTable key={year} endpoint="/worktime/calendar-days/" params={{ year }} fields={fields} canEdit={canEdit}
        defaults={{ working: true, hours_less: 0 }} onChanged={() => setTick((n) => n + 1)}
        title={<Typography.Text strong>{t('wt.cal.overrides')}</Typography.Text>} />
    </Space>
  )
}

function SettingsTab() {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const { data } = useFetch<{ min_rest_hours: number; max_duties: number }>('/worktime/settings/')
  useEffect(() => { if (data) form.setFieldsValue(data) }, [data, form])
  const { touch, clean } = useEditGuard(() => save())
  const save = async () => {
    try {
      await api.put('/worktime/settings/', await form.validateFields())
      message.success(t('common.saved'))
      clean()
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  return (
    <Form form={form} layout="vertical" style={{ maxWidth: 520 }} onValuesChange={touch}>
      <Form.Item name="min_rest_hours" label={t('wt.set.minRest')} extra={t('wt.set.minRestHint')}><InputNumber min={0} max={48} /></Form.Item>
      <Form.Item name="max_duties" label={t('wt.set.maxDuties')} extra={t('wt.set.maxDutiesHint')}><InputNumber min={0} max={31} /></Form.Item>
      <Button type="primary" onClick={save}>{t('common.save')}</Button>
    </Form>
  )
}

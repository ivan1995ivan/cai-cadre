import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Col, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import { api, errorText, fieldErrors } from '../../api/client'
import { useFetch } from '../../api/hooks'
import {
  COMBINATION_KINDS, COMBINATION_PAY, RATE_MODES, type Employment, type FunctionCombination, type JobHourRate, type PayMode,
} from '../../api/staff'
import type { HourType } from '../../api/worktime'
import { useLocalName } from '../../auth/AppContext'
import RefSelect from '../../components/RefSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'

const d = (v: string | null | undefined) => (v ? dayjs(v).format('DD.MM.YYYY') : '')
const num = (v: string | number | null | undefined) =>
  v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('ro-MD', { maximumFractionDigits: 2 })
const iso = (v: unknown) => (dayjs.isDayjs(v) ? (v as Dayjs).format('YYYY-MM-DD') : v ?? null)

/** Tipurile de ore (toate sau doar cele active) și opțiunile lor „COD — denumire”. */
export function useHourTypes(activeOnly = true) {
  const localName = useLocalName()
  const { data } = useFetch<HourType[]>('/worktime/hour-types/', activeOnly ? { active: 1 } : {})
  const types = data ?? []
  return { types, options: types.map((h) => ({ value: h.id, label: `${h.code} — ${localName(h)}` })) }
}

/** Rândul tabelului „Tarife pe tipuri de ore” din ordin (`params.hour_rates`). */
export interface HourRateRow {
  hour_type: number | null
  action: 'add' | 'modify' | 'stop'
  target?: number | null
  rate?: string | number | null
  guaranteed_hours?: string | number | null
  date_from?: string | null
  date_to?: string | null
  document?: string
}

const ACTION_COLOR: Record<string, string> = { add: 'green', modify: 'blue', stop: 'red' }

/** Tabelul „Tarife pe tipuri de ore” al punctului de ordin: la semnare rândurile intră pe raportul de muncă. */
export function HourRatesInput({ value, onChange, existing, disabled, onFromOccupation, mode }: {
  value?: HourRateRow[]
  onChange?: (v: HourRateRow[]) => void
  existing: JobHourRate[]
  disabled?: boolean
  onFromOccupation?: () => void
  mode?: PayMode | null
}) {
  const { t } = useTranslation()
  const { options } = useHourTypes()
  const rows = value ?? []
  const set = (i: number, patch: Partial<HourRateRow>) => onChange?.(rows.map((r, k) => (k === i ? { ...r, ...patch } : r)))
  const pays = !mode || RATE_MODES.includes(mode)
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={6}>
      {!pays && rows.some((r) => r.action !== 'stop') && <Alert type="warning" showIcon title={t('ht.rates.modeWarning')} />}
      {rows.map((r, i) => {
        const mine = existing.filter((x) => x.hour_type === r.hour_type)
        return (
          <Space key={i} wrap size={4} style={{ padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6 }}>
            <Tag color={ACTION_COLOR[r.action]}>{t(`pay.pl.actions.${r.action}`)}</Tag>
            <Select showSearch optionFilterProp="label" style={{ width: 240 }} placeholder={t('ht.type')} value={r.hour_type ?? undefined}
              disabled={disabled} onChange={(v) => set(i, { hour_type: v, target: null })} options={options} />
            <Select style={{ width: 120 }} value={r.action} disabled={disabled} onChange={(v) => set(i, { action: v })}
              options={['add', 'modify', 'stop'].map((a) => ({ value: a, label: t(`pay.pl.actions.${a}`) }))} />
            {r.action !== 'add' && mine.length > 0 && <Select allowClear style={{ width: 220 }} placeholder={t('pay.pl.target')} disabled={disabled}
              value={r.target ?? undefined} onChange={(v) => set(i, { target: v ?? null })}
              options={mine.map((x) => ({ value: x.id, label: `${d(x.date_from)} – ${d(x.date_to) || '…'}: ${num(x.rate)} lei` }))} />}
            {r.action !== 'stop' && <>
              <InputNumber style={{ width: 120 }} min={0} placeholder={t('ht.rates.rate')} suffix="lei" disabled={disabled}
                value={r.rate as number | null} onChange={(v) => set(i, { rate: v })} />
              <InputNumber style={{ width: 130 }} min={0} max={744} placeholder={t('ht.rates.guaranteed')} disabled={disabled}
                value={r.guaranteed_hours as number | null} onChange={(v) => set(i, { guaranteed_hours: v })} />
            </>}
            <DatePicker style={{ width: 130 }} format="DD.MM.YYYY" disabled={disabled}
              placeholder={r.action === 'stop' ? t('pay.pl.stopFrom') : t('pay.pl.fromOrder')}
              value={r.date_from ? dayjs(r.date_from) : null} onChange={(v) => set(i, { date_from: v ? v.format('YYYY-MM-DD') : null })} />
            <DatePicker style={{ width: 130 }} format="DD.MM.YYYY" disabled={disabled}
              placeholder={r.action === 'stop' ? t('pay.pl.lastDay') : t('staff.sen.to')}
              value={r.date_to ? dayjs(r.date_to) : null} onChange={(v) => set(i, { date_to: v ? v.format('YYYY-MM-DD') : null })} />
            <Input style={{ width: 200 }} placeholder={t('pay.pl.basis')} disabled={disabled} value={r.document ?? ''}
              onChange={(e) => set(i, { document: e.target.value })} />
            {!disabled && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange?.(rows.filter((_x, k) => k !== i))} />}
          </Space>
        )
      })}
      {!disabled && <Space wrap>
        <Button size="small" icon={<PlusOutlined />} onClick={() => onChange?.([...rows, { hour_type: null, action: 'add' }])}>{t('pay.pl.addRow')}</Button>
        {onFromOccupation && <Button size="small" onClick={onFromOccupation}>{t('pay.pl.fromOccupation')}</Button>}
      </Space>}
      <Typography.Text type="secondary">{t('ht.rates.orderHint')}</Typography.Text>
    </Space>
  )
}

/** „salariu + tarife”, „tarif orar” … — modalitatea de remunerare pe scurt. */
export function payShort(t: (k: string, o?: Record<string, unknown>) => string, mode: string | null | undefined) {
  return t(`ht.payShort.${mode || 'salary'}`)
}

/** „De bază: Pilot — salariu + tarife” / „Cumulare: Instructor — 30 %” — un rând pentru fișă și pontaj. */
export function combinationShort(t: (k: string, o?: Record<string, unknown>) => string, c: { kind: string; occupation?: string | number;
  occupation_name?: string; pay_mode: string; value: string | number }) {
  const unit = c.pay_mode === 'fixed' ? ' lei' : c.pay_mode === 'hourly' ? ` ${t('ht.perHour')}` : ' %'
  const name = c.occupation_name ?? (typeof c.occupation === 'string' ? c.occupation : '')
  return `${t(`ht.comb.kindsShort.${c.kind}`)}: ${name} — ${num(c.value)}${unit}`
}

/**
 * Remunerarea raportului de muncă în fișă (fila „Raporturi de muncă”): modalitatea, tarifele pe tipuri de ore cu orele
 * garantate și funcțiile exercitate în plus pe același contract (cumulare / suplinire / interimat). Rândurile din ordine se văd cu
 * ordinul; cele puse de mână se pot corecta aici.
 */
export function RemunerationBox({ job, canEdit, onChanged }: { job: Employment; canEdit: boolean; onChanged: () => void }) {
  const { t } = useTranslation()
  const { options: typeOptions } = useHourTypes()
  const [rateEdit, setRateEdit] = useState<Partial<JobHourRate> | null>(null)
  const [combEdit, setCombEdit] = useState<Partial<FunctionCombination> | null>(null)
  const [rateForm] = Form.useForm()
  const [combForm] = Form.useForm()
  const rates = job.hour_rates ?? []
  const combos = job.combinations ?? []
  const editable = canEdit && job.status !== 'ended'
  const pays = RATE_MODES.includes(job.pay_mode)
  const combPay = Form.useWatch('pay_mode', combForm)

  const openRate = (r?: JobHourRate) => {
    setRateEdit(r ?? {})
    rateForm.resetFields()
    rateForm.setFieldsValue(r ? { ...r, rate: Number(r.rate), guaranteed_hours: r.guaranteed_hours === null ? undefined : Number(r.guaranteed_hours),
      date_from: dayjs(r.date_from), date_to: r.date_to ? dayjs(r.date_to) : null } : { date_from: dayjs(job.date_from) })
  }
  const openComb = (c?: FunctionCombination) => {
    setCombEdit(c ?? {})
    combForm.resetFields()
    combForm.setFieldsValue(c ? { ...c, value: Number(c.value), other_salary: c.other_salary === null ? undefined : Number(c.other_salary),
      date_from: dayjs(c.date_from), date_to: c.date_to ? dayjs(c.date_to) : null } : { kind: 'combination', pay_mode: 'pct_own', date_from: dayjs() })
  }
  const save = async (url: string, id: number | undefined, form: typeof rateForm, close: () => void) => {
    const v = Object.fromEntries(Object.entries(await form.validateFields()).map(([k, x]) => [k, iso(x)]))
    try {
      if (id) await api.patch(`${url}${id}/`, v)
      else await api.post(url, { ...v, employment: job.id })
      message.success(t('common.saved'))
      close()
      onChanged()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }
  const remove = async (url: string, id: number) => {
    try {
      await api.delete(`${url}${id}/`)
      onChanged()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const source = (s: { kind: string; label: string }) => (s.kind === 'order' ? <Tag color="blue">{s.label}</Tag> : <Tag>{t('pay.pl.manual')}</Tag>)

  return (
    <div className="remuneration-box" style={{ marginTop: 8 }}>
      <Space wrap size={4} style={{ marginBottom: 4 }}>
        <Typography.Text strong>{t('ht.remuneration')}:</Typography.Text>
        <Tag color="geekblue">{job.pay_mode_label}</Tag>
        {job.pay_mode === 'hourly' && <span>{t('ht.hourlyRate')}: <b>{num(job.hourly_rate)} lei</b></span>}
        {(job.pay_mode === 'salary' || job.pay_mode === 'mixed') && job.base_salary !== null && <span>{t('org.sl.salary')}: <b>{num(job.base_salary)} lei</b></span>}
      </Space>
      {(rates.length > 0 || pays) && <Table<JobHourRate> size="small" rowKey="id" pagination={false} dataSource={rates}
        title={() => <Space>
          <Typography.Text type="secondary">{t('ht.rates.title')}</Typography.Text>
          {editable && pays && <Button size="small" icon={<PlusOutlined />} onClick={() => openRate()}>{t('common.add')}</Button>}
        </Space>}
        columns={[
          { title: t('ht.type'), key: 'type', render: (_v, r) => <Tooltip title={r.hour_type_name}><b>{r.hour_type_code}</b> {r.hour_type_name}</Tooltip> },
          { title: t('ht.rates.rate'), dataIndex: 'rate', width: 110, align: 'right', render: (v) => `${num(v)} lei` },
          { title: t('ht.rates.guaranteed'), dataIndex: 'guaranteed_hours', width: 120, align: 'right', render: (v) => (v === null ? '—' : num(v)) },
          { title: t('staff.sen.from'), dataIndex: 'date_from', width: 100, render: d },
          { title: t('staff.sen.to'), dataIndex: 'date_to', width: 100, render: (v) => d(v) || '…' },
          { title: t('pay.pl.source'), key: 'src', width: 190, render: (_v, r) => source(r.source) },
          { title: '', key: 'act', width: 70, render: (_v, r) => editable && r.source.kind === 'manual' && <Space size={0}>
            <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openRate(r)} />
            <Popconfirm title={t('ht.deleteConfirm')} onConfirm={() => remove('/worktime/job-hour-rates/', r.id)}>
              <Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>
          </Space> },
        ]} />}
      {!pays && rates.length > 0 && <Alert type="warning" showIcon style={{ marginTop: 4 }} title={t('ht.rates.modeWarning')} />}
      {job.kind !== 'contractor' && <Table<FunctionCombination> size="small" rowKey="id" pagination={false} dataSource={combos} style={{ marginTop: 6 }}
        title={() => <Space>
          <Typography.Text type="secondary">{t('ht.comb.title')}</Typography.Text>
          {editable && <Button size="small" icon={<PlusOutlined />} onClick={() => openComb()}>{t('common.add')}</Button>}
        </Space>}
        locale={{ emptyText: t('ht.comb.none') }}
        columns={[
          { title: t('ht.comb.kind'), dataIndex: 'kind_label', width: 190 },
          { title: t('ht.comb.occupation'), dataIndex: 'occupation_name', render: (v, r) => <>{v}{r.substituted_name ? <Typography.Text type="secondary"> · {t('ht.comb.for', { name: r.substituted_name })}</Typography.Text> : null}</> },
          { title: t('ht.comb.pay'), dataIndex: 'value_text', width: 210 },
          { title: t('staff.sen.from'), dataIndex: 'date_from', width: 100, render: d },
          { title: t('staff.sen.to'), dataIndex: 'date_to', width: 100, render: (v) => d(v) || '…' },
          { title: t('pay.pl.source'), key: 'src', width: 190, render: (_v, r) => source(r.source) },
          { title: '', key: 'act', width: 70, render: (_v, r) => editable && r.source.kind === 'manual' && <Space size={0}>
            <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openComb(r)} />
            <Popconfirm title={t('ht.deleteConfirm')} onConfirm={() => remove('/staff/combinations/', r.id)}>
              <Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>
          </Space> },
        ]} />}

      <Modal open={!!rateEdit} width={620} title={t('ht.rates.title')} onCancel={() => setRateEdit(null)}
        onOk={() => save('/worktime/job-hour-rates/', rateEdit?.id, rateForm, () => setRateEdit(null))}>
        <Form form={rateForm} layout="vertical">
          <Row gutter={12}>
            <Col xs={24}><Form.Item name="hour_type" label={t('ht.type')} rules={[{ required: true }]}><Select showSearch optionFilterProp="label" options={typeOptions} /></Form.Item></Col>
            <Col xs={12}><Form.Item name="rate" label={t('ht.rates.rate')} rules={[{ required: true }]}><InputNumber min={0} suffix="lei" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={12}><Form.Item name="guaranteed_hours" label={t('ht.rates.guaranteed')} extra={t('ht.rates.guaranteedHint')}><InputNumber min={0} max={744} style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={12}><Form.Item name="date_from" label={t('staff.sen.from')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={12}><Form.Item name="date_to" label={t('staff.sen.to')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24}><Form.Item name="document" label={t('pay.pl.basis')}><Input /></Form.Item></Col>
          </Row>
          <Typography.Text type="secondary">{t('ht.rates.manualHint')}</Typography.Text>
        </Form>
      </Modal>
      <Modal open={!!combEdit} width={720} title={t('ht.comb.title')} onCancel={() => setCombEdit(null)}
        onOk={() => save('/staff/combinations/', combEdit?.id, combForm, () => setCombEdit(null))}>
        <Form form={combForm} layout="vertical">
          <CombinationFields form={combForm} payMode={combPay} />
          <Form.Item name="note" label={t('org.notes')}><Input /></Form.Item>
          <Typography.Text type="secondary">{t('ht.comb.manualHint')}</Typography.Text>
        </Form>
      </Modal>
    </div>
  )
}

/** Câmpurile cumulării: felul, funcția, pe cine suplinește, modalitatea plății, valoarea, perioada (fișa și ordinul). */
export function CombinationFields({ payMode, withKind = true }: { form: ReturnType<typeof Form.useForm>[0]; payMode?: string; withKind?: boolean }) {
  const { t } = useTranslation()
  const { options: typeOptions } = useHourTypes()
  const mode = payMode || 'pct_own'
  return (
    <Row gutter={12}>
      {withKind && <Col xs={24} md={12}><Form.Item name="kind" label={t('ht.comb.kind')} rules={[{ required: true }]}>
        <Select options={COMBINATION_KINDS.map((k) => ({ value: k, label: t(`ht.comb.kinds.${k}`) }))} /></Form.Item></Col>}
      <Col xs={24} md={12}><Form.Item name="occupation" label={t('ht.comb.occupation')} rules={[{ required: true }]}><RefSelect spec="occupation" /></Form.Item></Col>
      <Col xs={24} md={12}><Form.Item name="subdivision" label={t('org.subdivision')}><SubdivisionSelect /></Form.Item></Col>
      <Col xs={24} md={12}><Form.Item name="substituted_name" label={t('ht.comb.substituted')}><Input /></Form.Item></Col>
      <Col xs={24} md={12}><Form.Item name="pay_mode" label={t('ht.comb.payMode')} rules={[{ required: true }]}>
        <Select options={COMBINATION_PAY.map((k) => ({ value: k, label: t(`ht.comb.payModes.${k}`) }))} /></Form.Item></Col>
      <Col xs={12} md={6}><Form.Item name="value" label={t(`ht.comb.valueLabel.${mode}`)} rules={[{ required: true }]}>
        <InputNumber min={0} max={mode === 'pct_own' || mode === 'pct_other' ? 200 : undefined}
          suffix={mode === 'fixed' ? 'lei' : mode === 'hourly' ? 'lei/h' : '%'} style={{ width: '100%' }} /></Form.Item></Col>
      {mode === 'pct_other' && <Col xs={12} md={6}><Form.Item name="other_salary" label={t('ht.comb.otherSalary')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>}
      {mode === 'hourly' && <Col xs={12} md={6}><Form.Item name="hour_type" label={t('ht.type')} rules={[{ required: true }]}><Select options={typeOptions} /></Form.Item></Col>}
      <Col xs={12} md={6}><Form.Item name="date_from" label={t('staff.sen.from')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
      <Col xs={12} md={6}><Form.Item name="date_to" label={t('staff.sen.to')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
    </Row>
  )
}

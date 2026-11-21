import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Button, Card, Col, DatePicker, Form, Input, InputNumber, Modal, Row, Select, Space, Tabs, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, PrinterOutlined, ThunderboltOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import AppTable from '../../components/AppTable'
import CrudTable from '../../components/CrudTable'
import PeriodPicker, { periodParams, type Period } from '../../components/PeriodPicker'
import PrintDialog from '../../components/PrintDialog'
import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { TRAINING_KINDS, type TrainingPlan, type TrainingRecord } from '../../api/training'
import { useApp } from '../../auth/AppContext'
import { d } from '../leave/LeavePage'
import RefSelect from '../../components/RefSelect'
import EmployeeSelect from '../../components/EmployeeSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'

const num = (v: number | string | null | undefined) => (v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('ro-RO'))

/** Formarea profesională: registrul cursurilor / instruirilor (cu certificatul și termenul lui) și planul anual de formare. */
export default function TrainingPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'plans' ? 'plans' : 'records'
  return (
    <Card title={t('menu.training')}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden items={[
        { key: 'records', label: t('tr.tabs.records'), children: <Records /> },
        { key: 'plans', label: t('tr.tabs.plans'), children: <Plans /> },
      ]} />
    </Card>
  )
}

// --- registrul formării -------------------------------------------------------------------------------------------------
export function RecordModal({ open, record, employee, onClose, onSaved }: {
  open: boolean
  record: TrainingRecord | null
  employee?: number
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const afterOpen = (v: boolean) => {
    if (!v) return
    form.resetFields()
    const dt = (x: string | null) => (x ? dayjs(x) : null)
    if (record) form.setFieldsValue({ ...record, date_from: dayjs(record.date_from), date_to: dt(record.date_to),
      certificate_date: dt(record.certificate_date), valid_until: dt(record.valid_until) })
    else form.setFieldsValue({ kind: 'course', employee })
  }
  const save = async () => {
    const v = await form.validateFields()
    const fmt = (x: Dayjs | null | undefined) => (x ? x.format('YYYY-MM-DD') : null)
    const body = { ...v, employee: employee ?? v.employee ?? record?.employee, date_from: fmt(v.date_from), date_to: fmt(v.date_to),
      certificate_date: fmt(v.certificate_date), valid_until: fmt(v.valid_until) }
    try {
      if (record) await api.patch(`/training/records/${record.id}/`, body)
      else await api.post('/training/records/', body)
      message.success(t('common.saved'))
      onSaved()
      onClose()
    } catch (e) {
      form.setFields(fieldErrors(e))
      message.error(errorText(e))
    }
  }
  return (
    <Modal open={open} title={record ? record.title : t('tr.rec.new')} onCancel={onClose} onOk={save} width={720}
      afterOpenChange={afterOpen} destroyOnHidden>
      <Form form={form} layout="vertical">
        <FormLayout formKey="training-record"><Row gutter={12}>
          {!employee && !record && <Col xs={24}><Form.Item name="employee" label={t('ord.employeeOne')} rules={[{ required: true }]}>
            <EmployeeSelect />
          </Form.Item></Col>}
          <Col xs={24} md={8}><Form.Item name="kind" label={t('tr.kind')}>
            <Select options={TRAINING_KINDS.map((k) => ({ value: k, label: t(`tr.kinds.${k}`) }))} /></Form.Item></Col>
          <Col xs={24} md={16}><Form.Item name="title" label={t('tr.title')} rules={[{ required: true }]}><Input /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="provider" label={t('tr.provider')}><Input /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="specialty" label={t('staff.edu.specialty')}>
            <RefSelect spec="specialty" />
          </Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="date_from" label={t('staff.sen.from')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="date_to" label={t('staff.sen.to')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="hours" label={t('tr.hours')}><InputNumber min={0} max={5000} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="certificate_number" label={t('tr.certificate')}><Input /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="certificate_date" label={t('tr.certificateDate')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="valid_until" label={t('tr.validUntil')} extra={t('tr.validUntilHint')}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row></FormLayout>
      </Form>
    </Modal>
  )
}

export function Records({ employee }: { employee?: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [period, setPeriod] = useState<Period>(employee ? null : [dayjs().startOf('year'), dayjs().endOf('year')])
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({})
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<TrainingRecord | null | undefined>()
  const query = { ...filters, ...periodParams(period), ...(employee ? { employee } : { page, page_size: 50 }) }
  const { data, loading, reload } = useFetch<Paged<TrainingRecord> | TrainingRecord[]>('/training/records/', query)
  const { data: sum, reload: reloadSum } = useFetch<{ hours: number; people: number }>(employee ? null : '/training/records/summary/', query)
  const rows = Array.isArray(data) ? data : data?.results ?? []
  const set = (k: string, v: string | number | undefined) => { setFilters({ ...filters, [k]: v }); setPage(1) }
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        {hasPerm('training.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing(null)}>{t('tr.rec.new')}</Button>}
        {!employee && <>
          <Input.Search allowClear placeholder={t('tr.searchHint')} style={{ width: 240 }} onSearch={(v) => set('q', v || undefined)} />
          <SubdivisionSelect style={{ width: 280 }} placeholder={t('org.subdivision')} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />
          <Select allowClear style={{ width: 200 }} placeholder={t('tr.kind')} onChange={(v) => set('kind', v)}
            options={TRAINING_KINDS.map((k) => ({ value: k, label: t(`tr.kinds.${k}`) }))} />
          <PeriodPicker value={period} onChange={(p) => { setPeriod(p); setPage(1) }} />
        </>}
        {sum && <Typography.Text type="secondary">{t('tr.summary', { people: sum.people, hours: num(sum.hours) })}</Typography.Text>}
      </Space>
      <AppTable<TrainingRecord> rowKey="id" size="small" loading={loading} dataSource={rows} exportName={t('tr.tabs.records')}
        pagination={employee ? false : { current: page, pageSize: 50, total: (data as Paged<TrainingRecord>)?.count ?? 0, onChange: setPage, showSizeChanger: false }}
        onRow={(r) => ({ onDoubleClick: () => hasPerm('training.edit') && setEditing(r) })}
        columns={[
          { title: t('staff.sen.from'), dataIndex: 'date_from', width: 100, render: d },
          { title: t('staff.sen.to'), dataIndex: 'date_to', width: 100, render: d },
          ...(employee ? [] : [{ title: t('staff.fullName'), dataIndex: 'employee_name',
            render: (v: string, r: TrainingRecord) => <a onClick={() => navigate(`/employees/${r.employee}?tab=education`)}>{v}</a> }]),
          { title: t('tr.kind'), dataIndex: 'kind_label', width: 170 },
          { title: t('tr.title'), dataIndex: 'title' },
          { title: t('tr.provider'), dataIndex: 'provider' },
          { title: t('tr.hours'), dataIndex: 'hours', width: 70, align: 'right', render: num },
          { title: t('tr.certificate'), dataIndex: 'certificate_number', width: 120 },
          { title: t('tr.validUntil'), dataIndex: 'valid_until', width: 110, render: (v: string | null) => v
            ? <Tag color={dayjs(v).isBefore(dayjs(), 'day') ? 'red' : dayjs(v).diff(dayjs(), 'day') <= 60 ? 'orange' : 'default'}>{d(v)}</Tag> : '' },
          { title: t('tr.order'), dataIndex: 'order_ref', width: 140 },
          { title: '', key: 'x', width: 90, render: (_: unknown, r: TrainingRecord) => <Space size={0}>
            {hasPerm('training.edit') && <Button size="small" type="link" onClick={() => setEditing(r)}>{t('common.edit')}</Button>}
            {hasPerm('training.delete') && !r.order_item && <MarkButton endpoint="/training/records/" row={r} onDone={() => { reload(); reloadSum() }} />}
          </Space> },
        ]} />
      <RecordModal open={editing !== undefined} record={editing ?? null} employee={employee} onClose={() => setEditing(undefined)}
        onSaved={() => { reload(); reloadSum() }} />
    </>
  )
}

// --- planul anual ------------------------------------------------------------------------------------------------------
function Plans() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const { data, loading, reload } = useFetch<TrainingPlan[]>('/training/plans/')
  const [current, setCurrent] = useState<number | null>(null)
  const [newYear, setNewYear] = useState(dayjs().year() + (dayjs().month() >= 9 ? 1 : 0))
  const plan = data?.find((p) => p.id === current) ?? null
  useEffect(() => { if (!current && data?.length) setCurrent(data[0].id) }, [data, current])
  const create = async () => {
    try {
      const r = await api.post('/training/plans/', { year: newYear })
      reload()
      setCurrent(r.data.id)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const act = async (what: 'fill' | 'approve' | 'reopen') => {
    try {
      const r = await api.post(`/training/plans/${plan!.id}/${what}/`, {})
      if (what === 'fill') message.success(t('tr.plan.filled', { count: r.data.added }))
      reload()
      setLinesKey((k) => k + 1)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const [linesKey, setLinesKey] = useState(0)
  const [printOpen, setPrintOpen] = useState(false)
  const editable = !!plan && plan.status === 'draft' && !plan.deletion_mark && hasPerm('training.edit')
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Space wrap>
        <Select style={{ width: 220 }} loading={loading} value={current ?? undefined} onChange={setCurrent} placeholder={t('tr.plan.choose')}
          options={(data ?? []).map((p) => ({ value: p.id, label: `${p.year}${p.number ? ` · nr. ${p.number}` : ''}${p.deletion_mark ? ` · ${t('marks.short')}` : ''}` }))} />
        {plan && <Tag color={plan.status === 'approved' ? 'green' : 'default'}>{t(`tr.plan.st.${plan.status}`)}</Tag>}
        {plan && <Typography.Text type="secondary">{t('tr.plan.stats', { lines: plan.lines_count, done: plan.done_count, hours: num(plan.hours_total) })}</Typography.Text>}
        {hasPerm('training.create') && <Space.Compact>
          <InputNumber value={newYear} min={2020} max={2100} onChange={(v) => v && setNewYear(v)} />
          <Button icon={<PlusOutlined />} onClick={create}>{t('tr.plan.new')}</Button>
        </Space.Compact>}
      </Space>
      {plan && <MarkedBanner endpoint="/training/plans/" row={plan} onDone={reload} canUnmark={hasPerm('training.delete')} />}
      {plan && !plan.deletion_mark && <Space wrap>
        {editable && <Button icon={<ThunderboltOutlined />} title={t('tr.plan.fillHint')} onClick={() => act('fill')}>{t('tr.plan.fill')}</Button>}
        {editable && <Button type="primary" onClick={() => act('approve')}>{t('tr.plan.approve')}</Button>}
        {plan.status === 'approved' && hasPerm('training.edit') && <Button onClick={() => act('reopen')}>{t('tr.plan.reopen')}</Button>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('rep.print')}</Button>
        {plan.status !== 'approved' && hasPerm('training.delete') && <MarkButton endpoint="/training/plans/" row={plan} onDone={reload} text />}
      </Space>}
      {plan && <CrudTable key={`${plan.id}-${linesKey}`} endpoint="/training/plan-lines/" params={{ plan: plan.id }} defaults={{ plan: plan.id }}
        canEdit={editable} onChanged={reload}
        fields={[
          { key: 'plan', label: '', hidden: true },
          { key: 'employee_name', label: '', hidden: true },
          { key: 'employee', label: t('ord.employeeOne'), required: true, render: (_v, r) => String(r.employee_name ?? ''),
            input: (form) => <EmployeeSelect label={String(form.getFieldValue('employee_name') ?? '') || undefined} allowClear={false} /> },
          { key: 'subdivision', label: t('org.subdivision'), display: true, render: (v) => String(v ?? '') },
          { key: 'title', label: t('tr.plan.course'), required: true },
          { key: 'kind', label: t('tr.kind'), type: 'select', options: TRAINING_KINDS.map((k) => ({ value: k, label: t(`tr.kinds.${k}`) })), inTable: false },
          { key: 'provider', label: t('tr.provider') },
          { key: 'month', label: t('tr.plan.month'), type: 'number', width: 70 },
          { key: 'hours', label: t('tr.hours'), type: 'number', width: 70 },
          { key: 'done', label: t('tr.plan.done'), display: true, render: (v) => v ? <Tag color="green">{String(v)}</Tag> : '' },
          { key: 'note', label: t('org.notes'), inTable: false },
        ]} />}
      {plan && <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="report" url={`/training/plans/${plan.id}/print/`}
        params={{}} optionKeys={[]} title={t('tr.tabs.plans')} />}
    </Space>
  )
}

/** Formarea din fișa angajatului (fila „Studii și formare”): cursurile, instruirile și certificatele lui. */
export function EmployeeTraining({ employee }: { employee: number }) {
  const { t } = useTranslation()
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Typography.Text strong>{t('tr.cardTitle')}</Typography.Text>
      <Records employee={employee} />
    </Space>
  )
}

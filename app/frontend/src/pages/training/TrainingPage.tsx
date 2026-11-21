import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Modal, Progress, Row, Select, Space, Tabs, Tag,
  Typography, message,
} from 'antd'
import { FileDoneOutlined, PlusOutlined, PrinterOutlined, SettingOutlined, ThunderboltOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import AppTable from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import CrudTable from '../../components/CrudTable'
import PeriodPicker, { periodParams, type Period } from '../../components/PeriodPicker'
import PrintDialog from '../../components/PrintDialog'
import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useDict } from '../../api/staff'
import {
  ATT_STATUSES, ATT_STATUS_COLOR, CREDIT_STATUS_COLOR, TRAINING_KINDS, type Attestation, type CreditRow, type TrainingPlan,
  type TrainingRecord,
} from '../../api/training'
import { useApp } from '../../auth/AppContext'
import { d } from '../leave/LeavePage'
import RefSelect from '../../components/RefSelect'
import EmployeeSelect from '../../components/EmployeeSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'

const num = (v: number | string | null | undefined) => (v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('ro-RO'))

/** Formare și atestare: registrul EMC, creditele, calendarul atestării, planul anual de formare. */
export default function TrainingPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'records'
  return (
    <Card title={t('menu.training')}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden items={[
        { key: 'records', label: t('tr.tabs.records'), children: <Records /> },
        { key: 'credits', label: t('tr.tabs.credits'), children: <Credits /> },
        { key: 'attestation', label: t('tr.tabs.attestation'), children: <AttestationTab /> },
        { key: 'plans', label: t('tr.tabs.plans'), children: <Plans /> },
      ]} />
    </Card>
  )
}

// --- registrul EMC -------------------------------------------------------------------------------------------------
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
    if (record) form.setFieldsValue({ ...record, date_from: dayjs(record.date_from), date_to: record.date_to ? dayjs(record.date_to) : null,
      certificate_date: record.certificate_date ? dayjs(record.certificate_date) : null })
    else form.setFieldsValue({ kind: 'course', employee })
  }
  const save = async () => {
    const v = await form.validateFields()
    const fmt = (x: Dayjs | null | undefined) => (x ? x.format('YYYY-MM-DD') : null)
    const body = { ...v, employee: employee ?? v.employee ?? record?.employee, date_from: fmt(v.date_from), date_to: fmt(v.date_to),
      certificate_date: fmt(v.certificate_date) }
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
          <Col xs={24} md={12}><Form.Item name="provider" label={t('tr.provider')}><Input placeholder="USMF „Nicolae Testemițanu”" /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="specialty" label={t('staff.edu.specialty')}>
            <RefSelect spec="specialty" />
          </Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="date_from" label={t('staff.sen.from')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="date_to" label={t('staff.sen.to')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="hours" label={t('tr.hours')}><InputNumber min={0} max={5000} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="credits" label={t('tr.credits')}><InputNumber min={0} max={1000} step={0.5} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="certificate_number" label={t('tr.certificate')}><Input /></Form.Item></Col>
          <Col xs={12} md={8}><Form.Item name="certificate_date" label={t('tr.certificateDate')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
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
  const { data: sum, reload: reloadSum } = useFetch<{ hours: number; credits: number; people: number }>(employee ? null : '/training/records/summary/', query)
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
        {sum && <Typography.Text type="secondary">{t('tr.summary', { people: sum.people, hours: num(sum.hours), credits: num(sum.credits) })}</Typography.Text>}
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
          { title: t('tr.credits'), dataIndex: 'credits', width: 80, align: 'right', render: num },
          { title: t('tr.certificate'), dataIndex: 'certificate_number', width: 120 },
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

// --- creditele ------------------------------------------------------------------------------------------------------
function StatusTag({ status }: { status: CreditRow['status'] }) {
  const { t } = useTranslation()
  return <Tag color={CREDIT_STATUS_COLOR[status]}>{t(`tr.status.${status}`)}</Tag>
}

function Credits() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({})
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { data, loading, reload } = useFetch<{ rows: CreditRow[]; counts: Record<string, number> }>('/training/credits/', filters)
  const set = (k: string, v: string | number | undefined) => setFilters({ ...filters, [k]: v })
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <SubdivisionSelect style={{ width: 280 }} placeholder={t('org.subdivision')} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />
        <Select allowClear style={{ width: 220 }} placeholder={t('tr.statusAll')} onChange={(v) => set('status', v)}
          options={['risk', 'behind', 'ok', 'done'].map((s) => ({ value: s, label: `${t(`tr.status.${s}`)} (${data?.counts[s] ?? 0})` }))} />
        {hasPerm('settings.edit') && <Button icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)}>{t('tr.norms')}</Button>}
      </Space>
      <Typography.Paragraph type="secondary">{t('tr.creditsHint')}</Typography.Paragraph>
      <AppTable<CreditRow> rowKey="employee" size="small" loading={loading} dataSource={data?.rows ?? []} exportName={t('tr.tabs.credits')}
        pagination={{ pageSize: 100 }}
        columns={[
          { title: t('staff.fullName'), dataIndex: 'name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}?tab=education`)}>{v}</a> },
          { title: t('org.subdivision'), dataIndex: 'subdivision' },
          { title: t('staff.qual.category'), dataIndex: 'category', render: (v: string) => v || <Typography.Text type="secondary">—</Typography.Text> },
          { title: t('tr.periodFrom'), dataIndex: 'period_from', width: 110, render: d },
          { title: t('tr.expiry'), dataIndex: 'expiry', width: 110, render: d },
          { title: t('tr.credits'), key: 'c', width: 200, render: (_: unknown, r) => <Space>
            <Progress percent={Math.min(r.pct, 100)} size="small" style={{ width: 90, margin: 0 }} showInfo={false}
              status={r.status === 'risk' ? 'exception' : undefined} />{num(r.credits)} / {num(r.required)}</Space> },
          { title: t('tr.missing'), dataIndex: 'missing', width: 90, align: 'right', render: num },
          { title: '', dataIndex: 'status', width: 170, render: (v: CreditRow['status']) => <StatusTag status={v} /> },
        ]} />
      <NormsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} onSaved={reload} />
    </>
  )
}

function NormsModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const { data } = useFetch<{ period_years: number; warn_months: number; credits: Record<string, number> }>(open ? '/training/settings/' : null)
  const categories = useDict('staff_category')
  useEffect(() => { if (data) form.setFieldsValue(data) }, [data, form])
  const save = async () => {
    try {
      await api.put('/training/settings/', await form.validateFields())
      message.success(t('common.saved'))
      onSaved()
      onClose()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <Modal open={open} title={t('tr.norms')} onCancel={onClose} onOk={save} destroyOnHidden>
      <Form form={form} layout="vertical">
        <Typography.Paragraph type="secondary">{t('tr.normsHint')}</Typography.Paragraph>
        <Row gutter={12}>
          <Col span={12}><Form.Item name="period_years" label={t('tr.periodYears')}><InputNumber min={1} max={10} /></Form.Item></Col>
          <Col span={12}><Form.Item name="warn_months" label={t('tr.warnMonths')}><InputNumber min={1} max={36} /></Form.Item></Col>
          {categories.map((c) => <Col span={12} key={c.code}>
            <Form.Item name={['credits', c.code]} label={c.label}><InputNumber min={0} max={2000} /></Form.Item></Col>)}
        </Row>
      </Form>
    </Modal>
  )
}

// --- atestarea --------------------------------------------------------------------------------------------------------
function AttestationTab() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [months, setMonths] = useState(12)
  const [picked, setPicked] = useState<number[]>([])
  const [session, setSession] = useState<Dayjs | null>(null)
  const [status, setStatus] = useState<string>('open')
  const [chosen, setChosen] = useState<number[]>([])
  const [editing, setEditing] = useState<Attestation | null>(null)
  const [printOpen, setPrintOpen] = useState(false)
  const due = useFetch<{ rows: CreditRow[] }>('/training/attestation-due/', { months })
  const list = useFetch<Paged<Attestation>>('/training/attestations/', { status, page_size: 500 })
  const include = async () => {
    try {
      const r = await api.post('/training/attestations/plan/', { employees: picked, session_date: session?.format('YYYY-MM-DD') })
      message.success(t('tr.att.added', { count: r.data.created }))
      setPicked([])
      due.reload()
      list.reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const makeOrder = async () => {
    try {
      const r = await api.post('/training/attestations/make-order/', { ids: chosen })
      message.success(t('tr.att.orderMade'))
      setChosen([])
      list.reload()
      if (r.data.orders[0]) navigate(`/orders/${r.data.orders[0].id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={24}>
      <div>
        <Typography.Title level={5}>{t('tr.att.dueTitle')}</Typography.Title>
        <Space wrap style={{ marginBottom: 12 }}>
          <InputNumber min={1} max={36} value={months} onChange={(v) => v && setMonths(v)} prefix={t('tr.att.months')} style={{ width: 170 }} />
          {hasPerm('training.create') && <>
            <DatePicker format="DD.MM.YYYY" value={session} onChange={setSession} placeholder={t('tr.att.session')} />
            <Button type="primary" icon={<PlusOutlined />} disabled={!picked.length} onClick={include}>{t('tr.att.include', { count: picked.length })}</Button>
          </>}
        </Space>
        <AppTable<CreditRow> rowKey="employee" size="small" loading={due.loading} dataSource={due.data?.rows ?? []} pagination={false}
          exportName={t('tr.att.dueTitle')}
          rowSelection={hasPerm('training.create') ? { selectedRowKeys: picked, onChange: (k) => setPicked(k as number[]),
            getCheckboxProps: (r) => ({ disabled: !!r.in_list }) } : undefined}
          columns={[
            { title: t('tr.expiry'), dataIndex: 'expiry', width: 110, render: (v: string, r) => <Tag color={r.expired ? 'red' : 'orange'}>{d(v)}</Tag> },
            { title: t('staff.fullName'), dataIndex: 'name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}?tab=education`)}>{v}</a> },
            { title: t('org.subdivision'), dataIndex: 'subdivision' },
            { title: t('staff.edu.specialty'), dataIndex: 'specialty' },
            { title: t('staff.qual.category'), dataIndex: 'category' },
            { title: t('tr.credits'), key: 'c', width: 120, render: (_: unknown, r) => r.required ? `${num(r.credits)} / ${num(r.required)}` : '' },
            { title: '', key: 's', width: 170, render: (_: unknown, r) => r.in_list ? <Tag color="blue">{t('tr.att.inList')}</Tag>
              : r.required ? <StatusTag status={r.status} /> : null },
          ]} />
      </div>
      <div>
        <Typography.Title level={5}>{t('tr.att.listTitle')}</Typography.Title>
        <Space wrap style={{ marginBottom: 12 }}>
          <Select style={{ width: 220 }} value={status} onChange={setStatus}
            options={[{ value: 'open', label: t('tr.att.open') }, { value: '', label: t('tr.att.all') },
              ...ATT_STATUSES.map((s) => ({ value: s, label: t(`tr.att.st.${s}`) }))]} />
          <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('tr.att.printList')}</Button>
          {hasPerm('orders.create') && <Button icon={<FileDoneOutlined />} disabled={!chosen.length} onClick={makeOrder}>
            {t('tr.att.makeOrder', { count: chosen.length })}</Button>}
        </Space>
        <AppTable<Attestation> rowKey="id" size="small" loading={list.loading} dataSource={list.data?.results ?? []} pagination={false}
          exportName={t('tr.att.listTitle')} rowTone={(r) => ROW_TONE.attestation(r.status)}
          rowSelection={{ selectedRowKeys: chosen, onChange: (k) => setChosen(k as number[]),
            getCheckboxProps: (r) => ({ disabled: !['awarded', 'confirmed'].includes(r.status) || !!r.order_item }) }}
          onRow={(r) => ({ onDoubleClick: () => hasPerm('training.edit') && setEditing(r) })}
          columns={[
            { title: t('staff.fullName'), dataIndex: 'employee_name' },
            { title: t('org.subdivision'), dataIndex: 'subdivision' },
            { title: t('tr.att.current'), dataIndex: 'current_category_name', render: (v: string) => v || '—' },
            { title: t('tr.expiry'), dataIndex: 'due_date', width: 100, render: d },
            { title: t('tr.att.requested'), dataIndex: 'requested_category_name' },
            { title: t('tr.att.session'), dataIndex: 'session_date', width: 110, render: d },
            { title: t('tr.att.statusCol'), dataIndex: 'status', width: 170, render: (v: string, r) => <Tag color={ATT_STATUS_COLOR[v]}>{r.status_label}</Tag> },
            { title: t('tr.att.result'), key: 'res', render: (_: unknown, r) => r.result_category_name ? `${r.result_category_name}, ${d(r.result_date)}` : '' },
            { title: t('tr.order'), dataIndex: 'order_ref', render: (v: string, r) => v ? <a onClick={() => navigate(`/orders/${r.order_id}`)}>{v}</a> : '' },
            { title: '', key: 'x', width: 80, render: (_: unknown, r) => hasPerm('training.edit') &&
              <Button size="small" type="link" onClick={() => setEditing(r)}>{t('common.edit')}</Button> },
          ]} />
      </div>
      <AttestationModal record={editing} onClose={() => setEditing(null)} onSaved={() => { list.reload(); due.reload() }} />
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="report" url="/training/attestations/print-list/"
        params={{ status }} optionKeys={[]} title={t('tr.att.printList')} />
    </Space>
  )
}

function AttestationModal({ record, onClose, onSaved }: {
  record: Attestation | null
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const afterOpen = (v: boolean) => {
    if (!v || !record) return
    const dt = (x: string | null) => (x ? dayjs(x) : null)
    form.setFieldsValue({ ...record, session_date: dt(record.session_date), submitted_on: dt(record.submitted_on), result_date: dt(record.result_date) })
  }
  const save = async () => {
    const v = await form.validateFields()
    const fmt = (x: Dayjs | null | undefined) => (x ? x.format('YYYY-MM-DD') : null)
    try {
      await api.patch(`/training/attestations/${record!.id}/`, { ...v, session_date: fmt(v.session_date), submitted_on: fmt(v.submitted_on),
        result_date: fmt(v.result_date) })
      message.success(t('common.saved'))
      onSaved()
      onClose()
    } catch (e) {
      form.setFields(fieldErrors(e))
      message.error(errorText(e))
    }
  }
  const locked = !!record?.order_item
  return (
    <Modal open={!!record} title={record?.employee_name} onCancel={onClose} afterOpenChange={afterOpen} destroyOnHidden width={640}
      footer={<Space>
        {!locked && record && <MarkButton endpoint="/training/attestations/" row={record} onDone={() => { onSaved(); onClose() }} text />}
        <Button onClick={onClose}>{t('common.cancel')}</Button>
        <Button type="primary" onClick={save}>{t('common.save')}</Button>
      </Space>}>
      {locked && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('tr.att.locked', { order: record?.order_ref })} />}
      <Form form={form} layout="vertical">
        <FormLayout formKey="attestation"><Row gutter={12}>
          <Col xs={24} md={12}><Form.Item name="requested_category" label={t('tr.att.requested')}><RefSelect spec={{ dict: 'qualification' }} allowClear={false} disabled={locked} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="submitted_on" label={t('tr.att.submitted')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="session_date" label={t('tr.att.session')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="status" label={t('tr.att.statusCol')}>
            <Select disabled={locked} options={ATT_STATUSES.map((s) => ({ value: s, label: t(`tr.att.st.${s}`) }))} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="decision" label={t('tr.att.decision')}><Input /></Form.Item></Col>
          <Col xs={12}><Form.Item name="result_category" label={t('tr.att.resultCategory')}><RefSelect spec={{ dict: 'qualification' }} disabled={locked} /></Form.Item></Col>
          <Col xs={12}><Form.Item name="result_date" label={t('tr.att.resultDate')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} disabled={locked} /></Form.Item></Col>
          <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row></FormLayout>
      </Form>
    </Modal>
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
      const r = await api.post(`/training/plans/${plan!.id}/${what}/`, what === 'fill' ? { only_behind: true } : {})
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
        {plan && <Typography.Text type="secondary">{t('tr.plan.stats', { lines: plan.lines_count, done: plan.done_count, credits: num(plan.credits_total) })}</Typography.Text>}
        {hasPerm('training.create') && <Space.Compact>
          <InputNumber value={newYear} min={2020} max={2100} onChange={(v) => v && setNewYear(v)} />
          <Button icon={<PlusOutlined />} onClick={create}>{t('tr.plan.new')}</Button>
        </Space.Compact>}
      </Space>
      {plan && <MarkedBanner endpoint="/training/plans/" row={plan} onDone={reload} canUnmark={hasPerm('training.delete')} />}
      {plan && !plan.deletion_mark && <Space wrap>
        {editable && <Button icon={<ThunderboltOutlined />} onClick={() => act('fill')}>{t('tr.plan.fill')}</Button>}
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
          { key: 'credits', label: t('tr.credits'), type: 'number', width: 80 },
          { key: 'done', label: t('tr.plan.done'), display: true, render: (v) => v ? <Tag color="green">{String(v)}</Tag> : '' },
          { key: 'note', label: t('org.notes'), inTable: false },
        ]} />}
      {plan && <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="report" url={`/training/plans/${plan.id}/print/`}
        params={{}} optionKeys={[]} title={t('tr.tabs.plans')} />}
    </Space>
  )
}

/** Fila EMC din fișa angajatului: creditele în perioada de atestare și activitățile de formare. */
export function EmployeeTraining({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { data } = useFetch<{ rows: CreditRow[] }>('/training/credits/', { employee })
  const row = data?.rows[0]
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Typography.Text strong>{t('tr.cardTitle')}</Typography.Text>
      {row && <Space wrap>
        <StatusTag status={row.status} />
        <Typography.Text>{t('tr.cardCredits', { credits: num(row.credits), required: num(row.required), from: d(row.period_from) })}</Typography.Text>
        {row.expiry && <Typography.Text type="secondary">{t('tr.cardExpiry', { date: d(row.expiry) })}</Typography.Text>}
      </Space>}
      <Records employee={employee} />
    </Space>
  )
}

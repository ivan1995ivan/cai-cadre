import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Tabs, Tag, Typography,
  message,
} from 'antd'
import { CalendarOutlined, CheckOutlined, CloseOutlined, FileAddOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import {
  REQUEST_KINDS, REQUEST_STATUS_COLOR, fmtDays, type Balance, type BalanceRow, type LeaveRequest,
} from '../../api/leave'
import type { Subdivision } from '../../api/org'
import type { Order } from '../../api/orders'
import { useApp, useLocalName } from '../../auth/AppContext'
import EmployeeSelect from '../../components/EmployeeSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'
import { useEditGuard } from '../../components/UnsavedGuard'

export const d = (v: string | null | undefined) => (v ? dayjs(v).format('DD.MM.YYYY') : '')

/** Subdiviziunile pentru filtre (doar cele active). */
export function useSubdivisionOptions() {
  const localName = useLocalName()
  const { data } = useFetch<Subdivision[]>('/org/subdivisions/', { active: 1 })
  return (data ?? []).map((s) => ({ value: s.id, label: localName(s) }))
}

/** Pagina „Concedii”: soldurile și cererile (setările evidenței sunt la Administrare → Setări). */
export default function LeavePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'requests' ? 'requests' : 'balances'
  return (
    <Card title={t('menu.leave')} extra={<Button icon={<CalendarOutlined />} onClick={() => navigate('/leave/schedule')}>
      {t('menu.leaveSchedule')}</Button>}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden items={[
        { key: 'balances', label: t('lv.tabs.balances'), children: <BalancesTab /> },
        { key: 'requests', label: t('lv.tabs.requests'), children: <RequestsTab /> },
      ]} />
    </Card>
  )
}

function BalancesTab() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({})
  const [page, setPage] = useState(1)
  const { data, loading } = useFetch<Paged<BalanceRow>>('/leave/balances/', { ...filters, page, page_size: 50 })
  const set = (k: string, v: string | number | undefined) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1) }
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search allowClear placeholder={t('lv.searchHint')} style={{ width: 240 }} onSearch={(v) => set('q', v || undefined)} />
        <SubdivisionSelect style={{ width: 300 }} placeholder={t('org.subdivision')} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />
        <DatePicker format="DD.MM.YYYY" placeholder={t('lv.onDate')} onChange={(v) => set('on_date', v ? v.format('YYYY-MM-DD') : undefined)} />
      </Space>
      <Table<BalanceRow> rowKey="id" size="small" loading={loading} dataSource={data?.results ?? []} exportName={t('lv.tabs.balances')}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/employees/${r.id}?tab=leave`) })}
        pagination={{ current: page, pageSize: 50, total: data?.count ?? 0, onChange: setPage, showTotal: (n) => t('common.total', { count: n }) }}
        columns={[
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 80 },
          { title: t('staff.fullName'), dataIndex: 'full_name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.id}?tab=leave`)}>{v}</a> },
          { title: t('org.subdivision'), dataIndex: 'subdivision', width: 200 },
          { title: t('org.sl.position'), dataIndex: 'occupation', width: 200 },
          { title: t('lv.hired'), dataIndex: 'hired', width: 100, render: d },
          { title: t('lv.workYear'), key: 'wy', width: 180, render: (_: unknown, r) => r.year_from ? `${d(r.year_from)} – ${d(r.year_to)}` : '' },
          { title: t('lv.entitled'), dataIndex: 'entitled', width: 80, align: 'right' },
          { title: t('lv.accrued'), dataIndex: 'accrued', width: 90, align: 'right', render: fmtDays },
          { title: t('lv.usedYear'), dataIndex: 'used', width: 90, align: 'right', render: fmtDays },
          { title: t('lv.remaining'), dataIndex: 'remaining', width: 100, align: 'right',
            render: (v: number) => <Typography.Text strong type={v < 0 ? 'danger' : undefined}>{fmtDays(v)}</Typography.Text> },
          { title: t('lv.available'), dataIndex: 'available', width: 110, align: 'right', render: fmtDays },
        ]} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>{t('lv.balanceHint')}</Typography.Paragraph>
    </>
  )
}

/** Cererea de concediu nouă (din lista cererilor sau din fișa angajatului). */
export function RequestModal({ open, employee, onClose, onSaved }: {
  open: boolean
  employee?: number
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const who = Form.useWatch('employee', form) as number | undefined
  const kind = Form.useWatch('kind', form) as string | undefined
  const from = Form.useWatch('date_from', form) as Dayjs | undefined
  const days = Form.useWatch('days', form) as number | undefined
  const [calc, setCalc] = useState<{ to: string; days: number } | null>(null)
  const { data: bal } = useFetch<Balance>(open && (employee ?? who) ? `/leave/balance/${employee ?? who}/` : null)

  useEffect(() => {
    if (open) {
      form.resetFields()
      form.setFieldsValue({ kind: 'annual', employee })
      setCalc(null)
    }
  }, [open, employee, form])

  useEffect(() => {
    if (!from || !days || !kind) { setCalc(null); return }
    api.get('/orders/leave-days/', { params: { from: from.format('YYYY-MM-DD'), days, kind } })
      .then((r) => setCalc(r.data)).catch(() => setCalc(null))
  }, [from, days, kind])

  const save = async () => {
    const v = await form.validateFields()
    try {
      await api.post('/leave/requests/', { ...v, employee: employee ?? v.employee, date_from: v.date_from.format('YYYY-MM-DD') })
      message.success(t('lv.req.saved'))
      onSaved()
      onClose()
    } catch (e) {
      form.setFields(fieldErrors(e))
      message.error(errorText(e))
    }
  }

  return (
    <Modal open={open} title={t('lv.req.new')} onOk={save} onCancel={onClose} width={600} destroyOnHidden>
      <Form form={form} layout="vertical">
        <FormLayout formKey="leave-request">{!employee && <Form.Item name="employee" label={t('ord.employeeOne')} rules={[{ required: true }]}>
          <EmployeeSelect />
        </Form.Item>}
        <Row gutter={12}>
          <Col xs={24} md={12}><Form.Item name="kind" label={t('lv.kind')} rules={[{ required: true }]}>
            <Select options={REQUEST_KINDS.map((k) => ({ value: k, label: t(`lv.kinds.${k}`) }))} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="date_from" label={t('staff.sen.from')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="days" label={t('ord.p.days')} rules={[{ required: true }]}>
            <InputNumber min={1} max={1500} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24}><Form.Item name="reason" label={t('lv.req.reason')}><Input /></Form.Item></Col>
        </Row></FormLayout>
        {calc && <Alert type="info" showIcon title={t('lv.req.calc', { days: calc.days, to: d(calc.to) })} />}
        {bal && kind === 'annual' && <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
          {t('lv.req.balance', { available: fmtDays(bal.available), remaining: fmtDays(bal.remaining) })}</Typography.Paragraph>}
      </Form>
    </Modal>
  )
}

/** Lista cererilor: aprobarea de către șef și ordinele făcute din cererile aprobate. */
export function RequestsTab({ employee }: { employee?: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>(employee ? { employee } : { status: 'new,approved' })
  const [page, setPage] = useState(1)
  const { data, loading, reload } = useFetch<Paged<LeaveRequest>>('/leave/requests/', { ...filters, page, page_size: 50 })
  const [selected, setSelected] = useState<number[]>([])
  const [creating, setCreating] = useState(false)
  const set = (k: string, v: string | number | undefined) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1) }
  const canOrder = hasPerm('orders.create')

  const act = async (r: LeaveRequest, what: 'approve' | 'reject' | 'withdraw', note?: string) => {
    try {
      await api.post(`/leave/requests/${r.id}/${what}/`, { note })
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const reject = (r: LeaveRequest) => {
    let note = ''
    Modal.confirm({
      title: t('lv.req.rejectTitle'), okText: t('lv.req.reject'), okButtonProps: { danger: true },
      content: <Input.TextArea rows={2} placeholder={t('lv.req.rejectNote')} onChange={(e) => { note = e.target.value }} />,
      onOk: () => act(r, 'reject', note),
    })
  }
  const makeOrders = async () => {
    try {
      const r = await api.post<Order[]>('/leave/requests/make-orders/', { ids: selected })
      setSelected([])
      message.success(t('lv.req.ordersMade', { count: r.data.length }))
      if (r.data.length === 1) navigate(`/orders/${r.data[0].id}`)
      else reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        {!employee && <Select style={{ width: 240 }} value={filters.status as string | undefined} allowClear placeholder={t('ord.status')}
          onChange={(v) => set('status', v)} options={[
            { value: 'new,approved', label: t('lv.req.open') },
            ...['new', 'approved', 'rejected', 'ordered', 'withdrawn'].map((s) => ({ value: s, label: t(`lv.req.statuses.${s}`) }))]} />}
        {!employee && <SubdivisionSelect style={{ width: 300 }} placeholder={t('org.subdivision')} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />}
        {hasPerm('leave.create') && <Button icon={<PlusOutlined />} onClick={() => setCreating(true)}>{t('lv.req.new')}</Button>}
        {canOrder && <Button type="primary" icon={<FileAddOutlined />} disabled={!selected.length} onClick={makeOrders}>
          {t('lv.req.makeOrders', { count: selected.length })}</Button>}
      </Space>
      <Table<LeaveRequest> rowKey="id" size="small" loading={loading} dataSource={data?.results ?? []} exportName={t('lv.tabs.requests')}
        rowTone={(r) => ROW_TONE.leaveRequest(r.status)}
        rowSelection={canOrder ? { selectedRowKeys: selected, onChange: (k) => setSelected(k as number[]),
          getCheckboxProps: (r) => ({ disabled: !(r.status === 'approved' || (r.status === 'ordered' && !r.order)) }) } : undefined}
        pagination={{ current: page, pageSize: 50, total: data?.count ?? 0, onChange: setPage, showTotal: (n) => t('common.total', { count: n }) }}
        columns={[
          { title: t('lv.req.created'), dataIndex: 'created_at', width: 100, render: d },
          ...(employee ? [] : [
            { title: t('staff.fullName'), dataIndex: 'employee_name', render: (v: string, r: LeaveRequest) => <a onClick={() => navigate(`/employees/${r.employee}?tab=leave`)}>{v}</a> },
            { title: t('org.subdivision'), dataIndex: 'subdivision', width: 180 },
          ]),
          { title: t('lv.kind'), dataIndex: 'kind_label', width: 220 },
          { title: t('lv.period'), key: 'p', width: 190, render: (_: unknown, r) => `${d(r.date_from)} – ${d(r.date_to)}` },
          { title: t('ord.p.days'), dataIndex: 'days', width: 60, align: 'right' },
          { title: t('lv.req.reason'), dataIndex: 'reason' },
          { title: t('ord.status'), dataIndex: 'status', width: 200, render: (v: string, r) => (
            <Space orientation="vertical" size={0}>
              <Tag color={REQUEST_STATUS_COLOR[v]}>{r.status_label}</Tag>
              {r.decided_by_name && <Typography.Text type="secondary" style={{ fontSize: 12 }}>{r.decided_by_name}{r.decision_note ? `: ${r.decision_note}` : ''}</Typography.Text>}
            </Space>) },
          { title: t('ord.tab.order'), dataIndex: 'order', width: 140, render: (o: LeaveRequest['order']) => o
            ? <a onClick={() => navigate(`/orders/${o.id}`)}>{o.label}</a> : '' },
          { title: '', key: 'act', width: 120, render: (_: unknown, r) => (
            <Space size={4}>
              {hasPerm('leave.approve') && (r.status === 'new' || r.status === 'rejected') &&
                <Button size="small" type="link" icon={<CheckOutlined />} title={t('lv.req.approve')} onClick={() => act(r, 'approve')} />}
              {hasPerm('leave.approve') && (r.status === 'new' || r.status === 'approved') &&
                <Button size="small" type="link" danger icon={<CloseOutlined />} title={t('lv.req.reject')} onClick={() => reject(r)} />}
              {hasPerm('leave.edit') && (r.status === 'new' || r.status === 'approved') &&
                <Popconfirm title={t('lv.req.withdrawConfirm')} onConfirm={() => act(r, 'withdraw')}>
                  <Button size="small" type="link">{t('lv.req.withdraw')}</Button></Popconfirm>}
            </Space>) },
        ]} />
      <RequestModal open={creating} employee={employee} onClose={() => setCreating(false)} onSaved={reload} />
    </>
  )
}

/** Setările evidenței concediilor (Administrare → Setări). */
export function LeaveSettingsPage({ title }: { title: string }) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const { data } = useFetch<{ start_date: string | null; not_counted: string[] }>('/leave/settings/')
  useEffect(() => {
    if (data) form.setFieldsValue({ start_date: data.start_date ? dayjs(data.start_date) : null, not_counted: data.not_counted })
  }, [data, form])
  const { touch, clean } = useEditGuard(() => save())
  const save = async () => {
    const v = await form.validateFields()
    try {
      await api.put('/leave/settings/', { start_date: v.start_date ? v.start_date.format('YYYY-MM-DD') : null, not_counted: v.not_counted ?? [] })
      message.success(t('common.saved'))
      clean()
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  return (
    <Card title={title}>
      <Form form={form} layout="vertical" style={{ maxWidth: 640 }} onValuesChange={touch}>
        <Form.Item name="start_date" label={t('lv.set.startDate')} extra={t('lv.set.startDateHint')}>
          <DatePicker format="DD.MM.YYYY" />
        </Form.Item>
        <Form.Item name="not_counted" label={t('lv.set.notCounted')} extra={t('lv.set.notCountedHint')}>
          <Select mode="multiple" options={['unpaid', 'childcare', 'childcare_unpaid', 'study', 'maternity'].map((k) => ({ value: k, label: t(`lv.kinds.${k}`) }))} />
        </Form.Item>
        <Button type="primary" onClick={save}>{t('common.save')}</Button>
      </Form>
    </Card>
  )
}

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import {
  Alert, Badge, Button, Card, Col, DatePicker, Descriptions, Empty, Form, Input, InputNumber, List, Modal, Popconfirm, Row, Select, Space,
  Statistic, Table, Tabs, Tag, Typography, message,
} from 'antd'
import { CheckOutlined, PlusOutlined, PrinterOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import PrintDialog from '../../components/PrintDialog'
import { api, errorText, fieldErrors } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { REQUEST_KINDS, REQUEST_STATUS_COLOR, fmtDays, type LeaveRequest } from '../../api/leave'
import { d } from '../leave/LeavePage'

interface Profile {
  full_name: string
  tab_number: string
  birth_date: string | null
  phone: string
  email: string
  address: string
  seniority: string
  jobs: { subdivision: string; occupation: string; kind: string; rate: number; date_from: string; date_to: string | null; status: string }[]
  leave: { available: number; remaining: number }
  absences: { kind: string; date_from: string; date_to: string; days: number }[]
  todo: { orders: number; requests: number }
  payroll: boolean
}
interface MyOrder { id: number; number: string; date: string; type: string; title: string; text: string; acknowledged_on: string | null }
interface MyRequest { id: number; kind: string; kind_label: string; text: string; copies: number; status: string; status_label: string; answer: string; created_at: string }
interface Payslip { id: number; year: number; month: number; occupation: string; gross: number; deductions: number; net: number }

const OTHER_KINDS = ['certificate_work', 'certificate_seniority', 'certificate_salary', 'data_change', 'other']
const OTHER_COLOR: Record<string, string> = { new: 'blue', in_work: 'orange', done: 'green', rejected: 'red', withdrawn: 'default' }
const money = (v: number) => v.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Cabinetul angajatului: datele mele, ordinele mele (cu „am luat cunoștință”), cererile, fișele de calcul. */
export default function PortalPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'home'
  const { data: me, error, reload } = useFetch<Profile>('/portal/profile/')
  if (error) return <Card title={t('menu.portal')}><Alert type="warning" showIcon title={errorText(error)} /></Card>
  return (
    <Card title={me ? `${t('menu.portal')} — ${me.full_name}` : t('menu.portal')}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden items={[
        { key: 'home', label: t('pt.tabs.home'), children: me && <Home me={me} /> },
        { key: 'orders', label: <Badge count={me?.todo.orders} size="small" offset={[8, -2]}>{t('pt.tabs.orders')}</Badge>,
          children: <Orders onChanged={reload} /> },
        { key: 'requests', label: t('pt.tabs.requests'), children: <Requests onChanged={reload} /> },
        ...(me?.payroll ? [{ key: 'payslips', label: t('pt.tabs.payslips'), children: <Payslips /> }] : []),
      ]} />
    </Card>
  )
}

function Home({ me }: { me: Profile }) {
  const { t } = useTranslation()
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} md={8}><Card size="small"><Statistic title={t('pt.leaveAvailable')} value={fmtDays(me.leave.available)} suffix={t('pt.days')} /></Card></Col>
      <Col xs={12} md={8}><Card size="small"><Statistic title={t('pt.ordersTodo')} value={me.todo.orders} /></Card></Col>
      <Col xs={12} md={8}><Card size="small"><Statistic title={t('pt.requestsOpen')} value={me.todo.requests} /></Card></Col>
      <Col xs={24} lg={12}>
        <Card size="small" title={t('pt.myData')}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label={t('staff.tab')}>{me.tab_number}</Descriptions.Item>
            <Descriptions.Item label={t('staff.birthDate')}>{d(me.birth_date)}</Descriptions.Item>
            <Descriptions.Item label={t('pt.seniority')}>{me.seniority}</Descriptions.Item>
            <Descriptions.Item label={t('users.phone')}>{me.phone}</Descriptions.Item>
            <Descriptions.Item label="E-mail">{me.email}</Descriptions.Item>
            <Descriptions.Item label={t('pt.address')}>{me.address}</Descriptions.Item>
          </Descriptions>
          <Typography.Text type="secondary">{t('pt.changeHint')}</Typography.Text>
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card size="small" title={t('pt.jobs')}>
          <List size="small" dataSource={me.jobs} renderItem={(j) => (
            <List.Item><List.Item.Meta title={`${j.occupation} — ${j.subdivision}`}
              description={`${j.kind}, ${j.rate.toLocaleString('ro-RO')}% · ${t('pt.since')} ${d(j.date_from)}${j.date_to ? ` ${t('pt.until')} ${d(j.date_to)}` : ''}`} /></List.Item>)} />
        </Card>
        <Card size="small" title={t('pt.absences')} style={{ marginTop: 16 }}>
          {me.absences.length ? <List size="small" dataSource={me.absences} renderItem={(a) => (
            <List.Item>{a.kind}<Typography.Text type="secondary">{d(a.date_from)} – {d(a.date_to)} ({a.days})</Typography.Text></List.Item>)} />
            : <Empty description={t('pt.noAbsences')} image={Empty.PRESENTED_IMAGE_SIMPLE} />}
        </Card>
      </Col>
    </Row>
  )
}

function Orders({ onChanged }: { onChanged: () => void }) {
  const { t } = useTranslation()
  const { data, loading, reload } = useFetch<MyOrder[]>('/portal/orders/')
  const [open, setOpen] = useState<MyOrder | null>(null)
  const ack = async (o: MyOrder) => {
    try {
      await api.post('/portal/orders/', { item: o.id })
      message.success(t('pt.acknowledged'))
      setOpen(null)
      reload()
      onChanged()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <>
      <Table<MyOrder> rowKey="id" size="small" loading={loading} dataSource={data ?? []} pagination={{ pageSize: 20 }}
        onRow={(o) => ({ onClick: () => setOpen(o), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 110 },
          { title: t('ord.date'), dataIndex: 'date', width: 110, render: d },
          { title: t('pt.orderType'), dataIndex: 'type' },
          { title: '', dataIndex: 'acknowledged_on', width: 220, render: (v: string | null, o) => v
            ? <Tag color="green">{t('pt.ackOn', { date: d(v) })}</Tag>
            : <Button size="small" type="primary" icon={<CheckOutlined />} onClick={(e) => { e.stopPropagation(); setOpen(o) }}>{t('pt.read')}</Button> },
        ]} />
      <Modal open={!!open} title={open ? `${t('ord.number')} ${open.number} · ${d(open.date)}` : ''} onCancel={() => setOpen(null)}
        footer={open && !open.acknowledged_on ? <Button type="primary" icon={<CheckOutlined />} onClick={() => ack(open)}>{t('pt.ack')}</Button> : null}>
        {open && <>
          <Typography.Paragraph strong>{open.title}</Typography.Paragraph>
          <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>{open.text}</Typography.Paragraph>
        </>}
      </Modal>
    </>
  )
}

function Requests({ onChanged }: { onChanged: () => void }) {
  const { t } = useTranslation()
  const leave = useFetch<LeaveRequest[]>('/portal/leave-requests/')
  const other = useFetch<MyRequest[]>('/portal/my-requests/')
  const [leaveOpen, setLeaveOpen] = useState(false)
  const [otherOpen, setOtherOpen] = useState(false)
  const done = () => { leave.reload(); other.reload(); onChanged() }
  const withdrawLeave = async (r: LeaveRequest) => {
    try { await api.post('/portal/leave-requests/withdraw/', { id: r.id }); done() } catch (e) { message.error(errorText(e)) }
  }
  const withdrawOther = async (r: MyRequest) => {
    try { await api.post(`/portal/my-requests/${r.id}/withdraw/`); done() } catch (e) { message.error(errorText(e)) }
  }
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={24}>
      <div>
        <Space style={{ marginBottom: 8 }}>
          <Typography.Title level={5} style={{ margin: 0 }}>{t('pt.leaveRequests')}</Typography.Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setLeaveOpen(true)}>{t('pt.newLeave')}</Button>
        </Space>
        <Table<LeaveRequest> rowKey="id" size="small" loading={leave.loading} dataSource={leave.data ?? []} pagination={false}
          columns={[
            { title: t('lv.kind'), dataIndex: 'kind_label' },
            { title: t('staff.sen.from'), dataIndex: 'date_from', width: 110, render: d },
            { title: t('staff.sen.to'), dataIndex: 'date_to', width: 110, render: d },
            { title: t('ord.p.days'), dataIndex: 'days', width: 70 },
            { title: t('pt.status'), dataIndex: 'status', width: 170, render: (v: string, r) => <Tag color={REQUEST_STATUS_COLOR[v]}>{r.status_label}</Tag> },
            { title: t('pt.note'), dataIndex: 'decision_note', render: (v: string, r) => r.order ? `${v ? v + ' · ' : ''}${t('pt.order')} ${r.order.label}` : v },
            { title: '', key: 'x', width: 100, render: (_: unknown, r) => ['new', 'rejected'].includes(r.status) &&
              <Popconfirm title={t('pt.withdrawConfirm')} onConfirm={() => withdrawLeave(r)}><Button size="small" danger>{t('pt.withdraw')}</Button></Popconfirm> },
          ]} />
      </div>
      <div>
        <Space style={{ marginBottom: 8 }}>
          <Typography.Title level={5} style={{ margin: 0 }}>{t('pt.otherRequests')}</Typography.Title>
          <Button icon={<PlusOutlined />} onClick={() => setOtherOpen(true)}>{t('pt.newOther')}</Button>
        </Space>
        <Table<MyRequest> rowKey="id" size="small" loading={other.loading} dataSource={other.data ?? []} pagination={false}
          columns={[
            { title: t('ord.date'), dataIndex: 'created_at', width: 110, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
            { title: t('lv.kind'), dataIndex: 'kind_label' },
            { title: t('pt.text'), dataIndex: 'text' },
            { title: t('pt.status'), dataIndex: 'status', width: 130, render: (v: string, r) => <Tag color={OTHER_COLOR[v]}>{r.status_label}</Tag> },
            { title: t('pt.answer'), dataIndex: 'answer' },
            { title: '', key: 'x', width: 100, render: (_: unknown, r) => r.status === 'new' &&
              <Popconfirm title={t('pt.withdrawConfirm')} onConfirm={() => withdrawOther(r)}><Button size="small" danger>{t('pt.withdraw')}</Button></Popconfirm> },
          ]} />
      </div>
      <LeaveModal open={leaveOpen} onClose={() => setLeaveOpen(false)} onSaved={done} />
      <OtherModal open={otherOpen} onClose={() => setOtherOpen(false)} onSaved={done} />
    </Space>
  )
}

function LeaveModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const save = async () => {
    const v = await form.validateFields()
    try {
      await api.post('/portal/leave-requests/', { ...v, date_from: (v.date_from as Dayjs).format('YYYY-MM-DD') })
      message.success(t('pt.sent'))
      form.resetFields()
      onSaved()
      onClose()
    } catch (e) {
      form.setFields(fieldErrors(e))
      message.error(errorText(e))
    }
  }
  return (
    <Modal open={open} title={t('pt.newLeave')} onCancel={onClose} onOk={save} okText={t('pt.send')} destroyOnHidden>
      <Form form={form} layout="vertical" initialValues={{ kind: 'annual', days: 14 }}>
        <Form.Item name="kind" label={t('lv.kind')} rules={[{ required: true }]}>
          <Select options={REQUEST_KINDS.map((k) => ({ value: k, label: t(`lv.kinds.${k}`) }))} />
        </Form.Item>
        <Row gutter={12}>
          <Col span={12}><Form.Item name="date_from" label={t('staff.sen.from')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col span={12}><Form.Item name="days" label={t('ord.p.days')} rules={[{ required: true }]}><InputNumber min={1} max={365} style={{ width: '100%' }} /></Form.Item></Col>
        </Row>
        <Form.Item name="reason" label={t('pt.reason')}><Input /></Form.Item>
        <Typography.Text type="secondary">{t('pt.leaveHint')}</Typography.Text>
      </Form>
    </Modal>
  )
}

function OtherModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const kind = Form.useWatch('kind', form)
  const save = async () => {
    const v = await form.validateFields()
    try {
      await api.post('/portal/my-requests/', v)
      message.success(t('pt.sent'))
      form.resetFields()
      onSaved()
      onClose()
    } catch (e) {
      form.setFields(fieldErrors(e))
      message.error(errorText(e))
    }
  }
  return (
    <Modal open={open} title={t('pt.newOther')} onCancel={onClose} onOk={save} okText={t('pt.send')} destroyOnHidden>
      <Form form={form} layout="vertical" initialValues={{ kind: 'certificate_work', copies: 1 }}>
        <Form.Item name="kind" label={t('lv.kind')} rules={[{ required: true }]}>
          <Select options={OTHER_KINDS.map((k) => ({ value: k, label: t(`pt.kinds.${k}`) }))} />
        </Form.Item>
        <Form.Item name="text" label={kind === 'data_change' ? t('pt.whatChanges') : t('pt.forWhom')}
          rules={kind === 'data_change' || kind === 'other' ? [{ required: true }] : []}><Input.TextArea rows={3} /></Form.Item>
        {kind?.startsWith('certificate') && <Form.Item name="copies" label={t('pt.copies')}><InputNumber min={1} max={10} /></Form.Item>}
      </Form>
    </Modal>
  )
}

function Payslips() {
  const { t } = useTranslation()
  const { data, loading } = useFetch<Payslip[]>('/portal/payslips/')
  const [line, setLine] = useState<number | null>(null)
  return (
    <>
      <Table<Payslip> rowKey="id" size="small" loading={loading} dataSource={data ?? []} pagination={false}
        columns={[
          { title: t('pt.month'), key: 'm', render: (_: unknown, r) => dayjs(`${r.year}-${String(r.month).padStart(2, '0')}-01`).format('MMMM YYYY') },
          { title: t('pt.position'), dataIndex: 'occupation' },
          { title: t('pt.gross'), dataIndex: 'gross', align: 'right', render: money },
          { title: t('pt.deductions'), dataIndex: 'deductions', align: 'right', render: money },
          { title: t('pt.net'), dataIndex: 'net', align: 'right', render: (v: number) => <b>{money(v)}</b> },
          { title: '', key: 'p', width: 110, render: (_: unknown, r) => <Button size="small" icon={<PrinterOutlined />} onClick={() => setLine(r.id)}>{t('rep.print')}</Button> },
        ]} />
      <PrintDialog open={line !== null} onClose={() => setLine(null)} docType="payslip" url="/portal/payslips/" params={{ line }}
        optionKeys={[]} title={t('pt.tabs.payslips')} />
    </>
  )
}

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Popconfirm, Row, Space, Spin, Tag, Typography, message, Select } from 'antd'
import { CheckOutlined, PlusOutlined, PrinterOutlined, ReloadOutlined, RollbackOutlined, SaveOutlined, UndoOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import CloseForm from '../../components/CloseForm'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import PrintDialog from '../../components/PrintDialog'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import { ROW_TONE } from '../../components/rowTone'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'
import { useTabTitle } from '../../layout/tabs'

export interface MealVoucherLine {
  id: number
  employee: number
  employee_name: string
  tab_number: string
  employment: number
  occupation: string
  subdivision: string
  days: number
  day_hours: string
  night_hours: string
  shifts: boolean
  count: number
  manual: boolean
  amount: string
  taxable: string
  note: string
}

export interface MealVoucherList {
  id: number
  deletion_mark: boolean
  number: string
  date: string
  year: number
  month: number
  subdivision: number | null
  subdivision_name: string
  value: string
  cap: string
  status: 'draft' | 'approved'
  status_label: string
  note: string
  lines: MealVoucherLine[]
  totals: { people: number; count: number; amount: number; taxable: number }
  problems: string[]
}

const STATUS_COLOR: Record<string, string> = { draft: 'gold', approved: 'green' }
const money = (v: number | string) => Number(v).toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const hours = (v: number | string) => Number(v).toLocaleString('ro-RO', { maximumFractionDigits: 2 })

/** Borderourile tichetelor de masă (Salarizare): pe luna lucrată, transferate la data borderoului. */
export default function MealVouchersPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [year, setYear] = useState(dayjs().year())
  const [creating, setCreating] = useState(false)
  const { data, loading } = useFetch<Paged<MealVoucherList>>('/payroll/meal-vouchers/', { year, page_size: 500 })
  const rows = data?.results ?? []
  return (
    <Card title={t('menu.mealVouchers')} extra={<Select style={{ width: 100 }} value={year} onChange={setYear}
      options={Array.from({ length: 5 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />}>
      <Space style={{ marginBottom: 12 }} wrap>
        {hasPerm('payroll.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>{t('mv.new')}</Button>}
        <Typography.Text type="secondary">{t('mv.hint')}</Typography.Text>
      </Space>
      <Table<MealVoucherList> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} exportName={t('menu.mealVouchers')}
        rowTone={(r) => ROW_TONE.payItemChange(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/payroll/meal-vouchers/${r.id}`) })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 140, render: (v: string, r) => <a onClick={() => navigate(`/payroll/meal-vouchers/${r.id}`)}>{v}</a> },
          { title: t('mv.date'), dataIndex: 'date', width: 110, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('mv.period'), key: 'period', width: 100, render: (_: unknown, r) => `${String(r.month).padStart(2, '0')}.${r.year}` },
          { title: t('ord.status'), dataIndex: 'status', width: 110, render: (v: string, r) => <Tag color={STATUS_COLOR[v]}>{t(`mv.status.${v}`, { defaultValue: r.status_label })}</Tag> },
          { title: t('mv.subdivision'), dataIndex: 'subdivision_name', render: (v: string) => v || t('mv.allCompany') },
          { title: t('mv.people'), key: 'p', width: 90, align: 'right', render: (_: unknown, r) => r.totals.people },
          { title: t('mv.count'), key: 'c', width: 90, align: 'right', render: (_: unknown, r) => r.totals.count },
          { title: t('mv.amount'), key: 'a', width: 120, align: 'right', render: (_: unknown, r) => money(r.totals.amount) },
          { title: t('mv.taxable'), key: 'x', width: 130, align: 'right', render: (_: unknown, r) => (r.totals.taxable ? money(r.totals.taxable) : '') },
        ]} />
      {creating && <CreateDialog onClose={() => setCreating(false)} onCreated={(id) => navigate(`/payroll/meal-vouchers/${id}`)} />}
    </Card>
  )
}

function CreateDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (id: number) => void }) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    const v = await form.validateFields()
    setBusy(true)
    try {
      const worked: Dayjs = v.period
      const r = await api.post<MealVoucherList>('/payroll/meal-vouchers/', {
        date: v.date.format('YYYY-MM-DD'), year: worked.year(), month: worked.month() + 1, subdivision: v.subdivision ?? null })
      onCreated(r.data.id)
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card size="small" style={{ marginTop: 12 }} title={t('mv.new')} extra={<Space>
      <Button onClick={onClose}>{t('common.cancel')}</Button>
      <Button type="primary" loading={busy} onClick={submit}>{t('mv.create')}</Button></Space>}>
      <Form form={form} layout="vertical" initialValues={{ period: dayjs().subtract(1, 'month').startOf('month'), date: dayjs() }}>
        <Row gutter={16}>
          <Col xs={24} md={6}><Form.Item name="period" label={t('mv.period')} rules={[{ required: true }]} extra={t('mv.periodHint')}>
            <DatePicker picker="month" format="MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={6}><Form.Item name="date" label={t('mv.date')} rules={[{ required: true }]} extra={t('mv.dateHint')}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="subdivision" label={t('mv.subdivision')} extra={t('mv.subdivisionHint')}>
            <SubdivisionSelect /></Form.Item></Col>
        </Row>
      </Form>
    </Card>
  )
}

/** Borderoul: antetul (data transferului, valoarea nominală), rândurile din pontaj (zilele, orele în schimburi, tichetele —
 *  numărul se poate scrie de mână), aprobarea (partea impozabilă intră în salariul lunii datei), tiparul. */
export function MealVoucherEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const { hasPerm } = useApp()
  const { data: doc, reload } = useFetch<MealVoucherList>(`/payroll/meal-vouchers/${id}/`)
  useTabTitle(doc ? { key: 'desk.tab.mealVouchers', params: { number: doc.number } } : null)
  const [busy, setBusy] = useState(false)
  const [print, setPrint] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [header] = Form.useForm()
  const draft = !!doc && doc.status === 'draft' && !doc.deletion_mark && hasPerm('payroll.edit')

  useEffect(() => {
    if (!doc) return
    header.setFieldsValue({ date: dayjs(doc.date), value: Number(doc.value), note: doc.note })
    setDirty(false)
  }, [doc, header])

  const save = async (quiet = false) => {
    if (!doc) return false
    try {
      const h = await header.validateFields()
      await api.patch(`/payroll/meal-vouchers/${doc.id}/`, { date: h.date.format('YYYY-MM-DD'), value: h.value, note: h.note ?? '' })
      setDirty(false)
      if (!quiet) message.success(t('common.saved'))
      reload()
      return true
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  useUnsavedGuard(dirty && draft, () => save(true))

  const post = async (what: string, body: object = {}, done?: string) => {
    setBusy(true)
    try {
      if (dirty && !(await save(true))) return
      await api.post(`/payroll/meal-vouchers/${id}/${what}/`, body)
      if (done) message.success(done)
      reload()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  if (!doc) return <Spin />
  return (
    <Card title={<Space wrap>{t('mv.title')}<b>{doc.number}</b><Tag color={STATUS_COLOR[doc.status]}>{t(`mv.status.${doc.status}`, { defaultValue: doc.status_label })}</Tag></Space>}
      extra={<Space wrap>
        {draft && <Button icon={<SaveOutlined />} onClick={() => save()}>{t('common.save')}</Button>}
        {draft && <Button icon={<ReloadOutlined />} loading={busy} onClick={() => post('fill', {}, t('mv.filled'))}>{t('mv.fill')}</Button>}
        {draft && hasPerm('payroll.approve') && <Popconfirm title={t('mv.approveConfirm')} onConfirm={() => post('approve', {}, t('mv.approved'))}>
          <Button type="primary" icon={<CheckOutlined />} loading={busy}>{t('mv.approve')}</Button></Popconfirm>}
        {doc.status === 'approved' && hasPerm('payroll.approve') && <Popconfirm title={t('mv.unapproveConfirm')} onConfirm={() => post('unapprove', {}, t('mv.unapproved'))}>
          <Button icon={<RollbackOutlined />} loading={busy}>{t('mv.unapprove')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrint(true)}>{t('lv.print')}</Button>
        {doc.status === 'draft' && hasPerm('payroll.delete') && <MarkButton endpoint="/payroll/meal-vouchers/" row={doc} onDone={reload} text />}
        <CloseForm to="/payroll/meal-vouchers" />
      </Space>}>
      <MarkedBanner endpoint="/payroll/meal-vouchers/" row={doc} onDone={reload} canUnmark={hasPerm('payroll.delete')} />
      {doc.status === 'approved' && <Alert type="success" showIcon style={{ marginBottom: 12 }} title={t('mv.approvedHint')} />}
      {draft && doc.problems.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('mv.problems')}
        description={<ul style={{ margin: 0, paddingInlineStart: 18 }}>{doc.problems.map((p) => <li key={p}>{p}</li>)}</ul>} />}
      <Form form={header} layout="vertical" disabled={!draft} onValuesChange={() => setDirty(true)}>
        <Row gutter={16}>
          <Col xs={24} md={4}><Form.Item label={t('mv.period')}><Input disabled value={`${String(doc.month).padStart(2, '0')}.${doc.year}`} /></Form.Item></Col>
          <Col xs={24} md={5}><Form.Item name="date" label={t('mv.date')} rules={[{ required: true }]} extra={t('mv.dateHint')}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={5}><Form.Item name="value" label={t('mv.value')} rules={[{ required: true }]}
            extra={t('mv.valueHint', { cap: money(doc.cap) })}><InputNumber min={0} step={1} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={10}><Form.Item label={t('mv.subdivision')}><Input disabled value={doc.subdivision_name || t('mv.allCompany')} /></Form.Item></Col>
          <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row>
      </Form>
      <Typography.Paragraph type="secondary">{t('mv.rulesHint')}</Typography.Paragraph>
      <Table<MealVoucherLine> rowKey="id" size="small" dataSource={doc.lines} pagination={false} exportName={`${t('mv.title')} ${doc.number}`}
        columns={[
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 90 },
          { title: t('mv.employee'), dataIndex: 'employee_name', render: (v: string, r) => <>{v}<br /><Typography.Text type="secondary">{r.occupation} · {r.subdivision}</Typography.Text></> },
          { title: t('mv.days'), dataIndex: 'days', width: 80, align: 'right' },
          { title: t('mv.shiftHours'), key: 'h', width: 140, align: 'right', render: (_: unknown, r) => (r.shifts
            ? t('mv.shiftHoursValue', { day: hours(r.day_hours), night: hours(r.night_hours) }) : '') },
          { title: t('mv.count'), dataIndex: 'count', width: 120, align: 'right', render: (v: number, r) => draft
            ? <CountCell line={r} onSet={(count) => post('set-count', { line: r.id, count })} />
            : <>{v}{r.manual && <Tag style={{ marginInlineStart: 4 }}>{t('mv.manual')}</Tag>}</> },
          { title: t('mv.amount'), dataIndex: 'amount', width: 110, align: 'right', render: money },
          { title: t('mv.taxable'), dataIndex: 'taxable', width: 120, align: 'right', render: (v: string) => (Number(v) ? money(v) : '') },
          { title: t('mv.how'), dataIndex: 'note', render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
        ]}
        summary={() => (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={4} align="right"><b>{t('mv.total')}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={4} align="right"><b>{doc.totals.count}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={5} align="right"><b>{money(doc.totals.amount)}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={6} align="right"><b>{doc.totals.taxable ? money(doc.totals.taxable) : ''}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={7} />
          </Table.Summary.Row>
        )} />
      {print && <PrintDialog open onClose={() => setPrint(false)} docType="meal_vouchers" url={`/payroll/meal-vouchers/${doc.id}/print/`}
        params={{}} optionKeys={[]} title={`${t('mv.title')} ${doc.number}`} />}
    </Card>
  )
}

/** Numărul tichetelor: scris de mână (rămâne la completarea din pontaj) sau înapoi la cel socotit. */
function CountCell({ line, onSet }: { line: MealVoucherLine; onSet: (count: number | '') => void }) {
  const { t } = useTranslation()
  const [value, setValue] = useState<number | null>(line.count)
  useEffect(() => setValue(line.count), [line.count])
  return (
    <Space size={2}>
      <InputNumber size="small" min={0} max={62} value={value} style={{ width: 64 }} onChange={(v) => setValue(v)}
        onBlur={() => { if (value !== null && value !== line.count) onSet(value) }}
        onPressEnter={() => { if (value !== null && value !== line.count) onSet(value) }} />
      {line.manual && <Button size="small" type="text" icon={<UndoOutlined />} title={t('mv.resetCount')} onClick={() => onSet('')} />}
    </Space>
  )
}

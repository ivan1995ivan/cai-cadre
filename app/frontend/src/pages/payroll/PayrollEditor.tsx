import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Spin, Table, Tag, Tooltip,
  Typography, message,
} from 'antd'
import {
  CalculatorOutlined, CheckOutlined, DeleteOutlined, DollarOutlined, EditOutlined, PlusOutlined, PrinterOutlined, RollbackOutlined,
  SaveOutlined, UndoOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import AppTable from '../../components/AppTable'
import CloseForm from '../../components/CloseForm'
import PrintDialog from '../../components/PrintDialog'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import {
  AT_PAYMENT_AUTOS, PAYMENT_STATUS_COLOR, PAYROLL_STATUS_COLOR, money, type Payment, type PayrollItem, type PayrollLine, type PayrollReport,
} from '../../api/payroll'
import { useApp, useLocalName } from '../../auth/AppContext'
import { useTabTitle } from '../../layout/tabs'

/** Ce se corectează: un rând calculat (se pune un rând de mână de același tip, care îl înlocuiește) sau un rând nou. */
interface Editing { line: PayrollLine; item?: PayrollItem }

interface Header { date: Dayjs; note: string }

/**
 * Calculul salariului pe o lună: rândurile pe raporturi de muncă, acumulările, reținerile și CAS al fiecăruia. Impozitul
 * pe venit și CNAM nu sunt aici — se rețin la plată, în îndreptarea spre plată făcută în baza calculului aprobat (butonul
 * „Îndreptare spre plată”; legăturile spre ele — sub titlu). Orice sumă se corectează de mână (creionul): rândul de mână
 * înlocuiește suma calculată, CAS se reface. Data documentului se scrie de mână în antet. Fluturașii se fac din
 * îndreptarea spre plată pe salariu.
 */
export default function PayrollEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const localName = useLocalName()
  const { data, loading, reload } = useFetch<PayrollReport>(`/payroll/payrolls/${id}/report/`)
  const [print, setPrint] = useState(false)
  const [editing, setEditing] = useState<Editing | null>(null)
  const [form] = Form.useForm()
  const [header] = Form.useForm<Header>()
  const [dirty, setDirty] = useState(false)
  const editable = !!data && data.status !== 'approved' && !data.deletion_mark && hasPerm('payroll.edit')

  // antetul se pune din document la deschidere și după salvare (nu la fiecare recalculare — ar șterge ce s-a scris)
  useEffect(() => {
    if (!data) return
    header.setFieldsValue({ date: dayjs(data.date), note: data.note })
    setDirty(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.id, data?.date, data?.note])

  /** Salvează antetul (data, observațiile); true — salvat sau nimic de salvat. */
  const saveHeader = async () => {
    if (!dirty) return true
    try {
      const v = await header.validateFields()
      await api.patch(`/payroll/payrolls/${id}/`, { date: v.date.format('YYYY-MM-DD'), note: v.note ?? '' })
      setDirty(false)
      reload()
      return true
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return false
      message.error(errorText(e))
      return false
    }
  }
  useUnsavedGuard(dirty, saveHeader)
  const title = data ? t('pay.heading', { number: data.number, date: dayjs(data.date).format('DD.MM.YYYY') }) : ''
  useTabTitle(data ? { key: 'desk.tab.payroll', params: { number: data.number } } : null)

  if (!data) return <Card loading={loading}><Spin /></Card>
  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    try {
      await fn()
      if (ok) message.success(ok)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  // acțiunile pe document salvează întâi antetul scris
  const post = async (action: string) => {
    if (await saveHeader()) await run(() => api.post(`/payroll/payrolls/${id}/${action}/`), action === 'calculate' ? t('pay.calculated') : undefined)
  }
  const toPayment = async () => {
    try {
      const r = await api.post<Payment>('/payroll/payments/', { payroll: data.id, kind: 'salary', method: 'all', date: dayjs().format('YYYY-MM-DD') })
      navigate(`/payroll/payments/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const typeById = Object.fromEntries(data.types.map((x) => [x.id, x]))
  // impozitul, CNAM și avansul se rețin la plată — nu se corectează aici
  const editableType = (typeId: number) => !AT_PAYMENT_AUTOS.includes(typeById[typeId]?.auto ?? '')
  const manualTypes = data.types.filter((x) => editableType(x.id))
  // rândul de mână pe un tip calculat singur îl înlocuiește (se poate întoarce la calcul); pe alt tip e un rând în plus
  const overridesAuto = (typeId: number) => typeById[typeId]?.formula === 'auto' && typeById[typeId]?.auto !== 'none'
  const openEdit = (line: PayrollLine, item?: PayrollItem) => {
    form.resetFields()
    if (item) form.setFieldsValue({ pay_type: item.pay_type, amount: Number(item.amount), note: item.manual ? item.note : '' })
    setEditing({ line, item })
  }
  const saveItem = async () => {
    const v = await form.validateFields()
    await run(() => api.post('/payroll/items/', { ...v, line: editing!.line.id }), t('pay.corrected'))
    setEditing(null)
  }
  const monthName = `${dayjs().month(data.month - 1).format('MMMM')} ${data.year}`
  // IT Park: toate rândurile impozitate final — restul e chiar suma de plată (fără impozit și CNAM la plată)
  const allFinal = data.lines.length > 0 && data.lines.every((l) => l.it_park)

  const itemsTable = (line: PayrollLine) => (
    <Table<PayrollItem> size="small" rowKey="id" pagination={false} dataSource={line.items} style={{ margin: '4px 0 8px 32px', maxWidth: 1150 }}
      rowClassName={(r) => (r.category === 'employer' ? 'muted-row' : '')}
      columns={[
        { title: t('pay.item'), dataIndex: 'name', render: (v: string, r) => <Space size={4}>{v}{r.manual && <Tag color="orange">{t('pay.manual')}</Tag>}
          {r.category === 'employer' && <Tag color="default">{t('pay.employer')}</Tag>}</Space> },
        { title: t('pay.qty'), dataIndex: 'quantity', width: 80, align: 'right', render: (v: string | null) => (v ? Number(v).toLocaleString('ro-MD') : '') },
        { title: t('pay.base'), dataIndex: 'base', width: 110, align: 'right', render: money },
        { title: '%', dataIndex: 'percent', width: 70, align: 'right', render: (v: string | null) => (v ? `${Number(v).toLocaleString('ro-MD')}%` : '') },
        { title: t('pay.amount'), dataIndex: 'amount', width: 120, align: 'right', render: (v: string, r) =>
          <Typography.Text strong type={r.category === 'deduction' ? 'danger' : undefined}>{r.category === 'deduction' ? '−' : ''}{money(v)}</Typography.Text> },
        { title: t('pay.note'), dataIndex: 'note', render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
        ...(editable ? [{ title: '', key: 'act', width: 76, render: (_: unknown, r: PayrollItem) => (
          <Space size={0}>
            {editableType(r.pay_type) && <Tooltip title={t(r.manual ? 'pay.editManual' : 'pay.correct')}>
              <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openEdit(line, r)} /></Tooltip>}
            {r.manual && <Popconfirm title={t(overridesAuto(r.pay_type) ? 'pay.restoreConfirm' : 'common.confirmDelete')}
              onConfirm={() => run(() => api.delete(`/payroll/items/${r.id}/`))}>
              <Tooltip title={t(overridesAuto(r.pay_type) ? 'pay.restore' : 'common.delete')}>
                <Button size="small" type="text" danger icon={overridesAuto(r.pay_type) ? <UndoOutlined /> : <DeleteOutlined />} /></Tooltip>
            </Popconfirm>}
          </Space>) }] : []),
      ]} />
  )

  return (
    <Card className="doc-form" title={<Space wrap>
      {title}<Tag color={PAYROLL_STATUS_COLOR[data.status]}>{data.status_label}</Tag>
      {data.it_park && <Tooltip title={t('itp.payrollHint')}><Tag color="purple">{t('itp.finalTag')}</Tag></Tooltip>}
      {data.payments.map((x) => <Tag key={x.id} color={PAYMENT_STATUS_COLOR[x.status]} style={{ cursor: 'pointer' }}
        onClick={() => navigate(`/payroll/payments/${x.id}`)}>{t('pay.paymentRef', { number: x.number, date: dayjs(x.date).format('DD.MM.YYYY') })} · {x.status_label}</Tag>)}
    </Space>} extra={<Space wrap>
      {!data.deletion_mark && <>
        {editable && <Button icon={<SaveOutlined />} disabled={!dirty} onClick={saveHeader}>{t('common.save')}</Button>}
        {editable && <Button icon={<CalculatorOutlined />} onClick={() => post('calculate')}>{t('pay.calculate')}</Button>}
        {editable && data.status === 'draft' && <Button onClick={() => post('check')}>{t('pay.check')}</Button>}
        {data.status !== 'approved' && hasPerm('payroll.approve') && <Popconfirm title={t('pay.approveConfirm')} onConfirm={() => post('approve')}>
          <Button type="primary" icon={<CheckOutlined />}>{t('pay.approve')}</Button></Popconfirm>}
        {data.status === 'approved' && hasPerm('payroll.create') && <Tooltip title={t('pay.toPaymentHint')}>
          <Button type="primary" icon={<DollarOutlined />} onClick={toPayment}>{t('pay.toPayment')}</Button></Tooltip>}
        {data.status === 'approved' && hasPerm('payroll.approve') && <Popconfirm title={t('pay.reopenConfirm')} onConfirm={() => post('reopen')}>
          <Button icon={<RollbackOutlined />}>{t('wt.doc.reopen')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrint(true)}>{t('pay.printSheet')}</Button>
        {data.status !== 'approved' && hasPerm('payroll.delete') && <MarkButton endpoint="/payroll/payrolls/" row={data} onDone={reload} text />}
      </>}
      <CloseForm to="/payroll" />
    </Space>}>
      <MarkedBanner endpoint="/payroll/payrolls/" row={data} onDone={reload} canUnmark={hasPerm('payroll.delete')} />
      {data.it_park && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('itp.payrollHint')} />}
      <Form form={header} layout="vertical" disabled={!editable} onValuesChange={() => setDirty(true)}>
        <Row gutter={12}>
          <Col xs={12} md={4}><Form.Item name="date" label={t('ord.date')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item label={t('pay.month')}><Input value={monthName} disabled /></Form.Item></Col>
          <Col xs={24} md={6}><Form.Item label={t('org.subdivision')}><Input value={data.subdivision_name || t('pay.whole')} disabled /></Form.Item></Col>
          <Col xs={24} md={10}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row>
      </Form>
      <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }} bordered style={{ marginBottom: 12 }}
        styles={{ label: { whiteSpace: 'nowrap' }, content: { whiteSpace: 'nowrap' } }} items={[
        { key: 'g', label: t('pay.gross'), children: money(data.totals.gross) },
        { key: 'd', label: t('pay.deductions'), children: money(data.totals.deductions) },
        { key: 'n', label: allFinal ? t('itp.netFinal') : t('pay.net'), children: <b>{money(data.totals.net)}</b> },
        { key: 'cas', label: t('pay.cas'), children: money(data.totals.cas) },
        { key: 'when', label: t('pay.calculatedAt'), children: data.calculated_at ? dayjs(data.calculated_at).format('DD.MM.YYYY HH:mm') : '' },
      ]} />
      <AppTable<PayrollLine> rowKey="id" size="small" loading={loading} dataSource={data.lines} pagination={false} exportName={`${title} — ${monthName}`}
        expandable={{ expandedRowRender: itemsTable }}
        columns={[
          { title: t('staff.fullName'), dataIndex: 'employee_name', width: 230, render: (v: string, r) => (
            <Space orientation="vertical" size={0}>
              <a onClick={() => navigate(`/employees/${r.employee}?tab=pay`)}>{v}</a>
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>{r.info.occupation}{r.info.kind !== 'main' ? ` · ${r.info.kind_label}` : ''} · {r.info.rate * 100}%</Typography.Text>
            </Space>) },
          { title: t('wt.ts.days'), key: 'd', width: 60, align: 'right', render: (_: unknown, r) => <Tooltip title={r.info.timesheet?.assumed ? t('pay.noTimesheet') : ''}>
            <span style={{ color: r.info.timesheet?.assumed ? 'var(--ant-color-warning)' : undefined }}>{r.info.timesheet?.days ?? ''}</span></Tooltip> },
          { title: t('wt.ro.hours'), key: 'h', width: 70, align: 'right', render: (_: unknown, r) => `${r.info.timesheet?.hours ?? ''}${r.info.timesheet?.norm ? ` / ${r.info.timesheet.norm}` : ''}` },
          { title: t('pay.gross'), dataIndex: 'gross', width: 110, align: 'right', render: money },
          { title: t('pay.deductions'), dataIndex: 'deductions', width: 100, align: 'right', render: money },
          { title: allFinal ? t('itp.netFinal') : t('pay.net'), dataIndex: 'net', width: 120, align: 'right', render: (v: string) => <b>{money(v)}</b> },
          { title: t('pay.cas'), dataIndex: 'cas', width: 100, align: 'right', render: (v: string, r) =>
            r.it_park ? <Tooltip title={t('itp.finalLine')}><Tag color="purple" style={{ marginInlineEnd: 0 }}>{t('itp.finalShort')}</Tag></Tooltip> : money(v) },
          { title: '', key: 'act', width: 90, render: (_: unknown, r) => <Space size={0}>
            {editable && <Tooltip title={t('pay.addItem')}><Button size="small" type="text" icon={<PlusOutlined />} onClick={() => openEdit(r)} /></Tooltip>}
          </Space> },
        ]} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>{t('pay.legend')}</Typography.Paragraph>
      <Modal open={!!editing} onOk={saveItem} onCancel={() => setEditing(null)}
        title={editing ? t(editing.item ? 'pay.correctFor' : 'pay.addItemFor', { name: editing.line.employee_name, item: editing.item?.name }) : ''}>
        <Form form={form} layout="vertical">
          <Form.Item name="pay_type" label={t('pay.item')} rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" disabled={!!editing?.item}
              options={manualTypes.map((x) => ({ value: x.id, label: `${x.code} — ${localName(x)} (${x.category_label})` }))} />
          </Form.Item>
          <Form.Item name="amount" label={t('pay.amount')} rules={[{ required: true }]}><InputNumber min={0} step={10} style={{ width: '100%' }} autoFocus /></Form.Item>
          <Form.Item name="note" label={t('pay.note')}><Input /></Form.Item>
          <Typography.Text type="secondary">{t('pay.correctHint')}</Typography.Text>
        </Form>
      </Modal>
      {print && <PrintDialog open onClose={() => setPrint(false)} docType="payroll_sheet" url={`/payroll/payrolls/${id}/print/`}
        params={{}} optionKeys={[]} title={t('pay.printSheet')} />}
    </Card>
  )
}

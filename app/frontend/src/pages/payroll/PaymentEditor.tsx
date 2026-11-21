import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Spin, Tag, Tooltip, Typography,
  message,
} from 'antd'
import {
  BankOutlined, CheckOutlined, DeleteOutlined, DollarOutlined, DownloadOutlined, FilePdfOutlined, FileTextOutlined, MailOutlined, PrinterOutlined,
  ReloadOutlined, RollbackOutlined, SaveOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import CloseForm from '../../components/CloseForm'
import PrintDialog from '../../components/PrintDialog'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { PAYMENT_STATUS_COLOR, PAYROLL_STATUS_COLOR, downloadFile, money, type Payment, type PaymentLine, type Payroll } from '../../api/payroll'
import { useApp } from '../../auth/AppContext'
import PayslipMail from './PayslipMail'
import { useTabTitle } from '../../layout/tabs'

interface Header { date: Dayjs; kind: Payment['kind']; payroll: number | null; ym: Dayjs; method: Payment['method']; note: string }

/** Ce schimbă rândurile: altă bază, alt fel, altă modalitate sau altă lună — serverul completează îndreptarea din nou. */
const REFILL: (keyof Header)[] = ['kind', 'payroll', 'ym', 'method']

const toHeader = (doc: Payment): Header => ({
  date: dayjs(doc.date), kind: doc.kind, payroll: doc.payroll, ym: dayjs(`${doc.year}-${String(doc.month).padStart(2, '0')}-01`),
  method: doc.method, note: doc.note,
})
const same = (a: Header, b: Header, key: keyof Header) =>
  key === 'ym' ? a.ym.format('YYYY-MM') === b.ym.format('YYYY-MM') : key === 'date' ? a.date.isSame(b.date, 'day') : a[key] === b[key]

/**
 * Îndreptarea spre plată (salariu sau avans): aici se rețin CNAM, scutirea și impozitul pe venit. Salariul se face în baza
 * unui calcul aprobat (doar angajații lui) sau pe sold (restul lunii din toate calculele aprobate); impozitele se socotesc
 * cumulat pe lună — pe tot venitul plătit în lună, minus ce s-a reținut deja (avansul). Antetul ciornei se scrie de mână
 * (data, felul, baza, luna, modalitatea); altă bază completează rândurile din nou. În ciornă orice sumă se corectează:
 * brutul reface impozitele, netul află brutul, impozitele scrise direct rămân așa. Apoi aprobarea, achitarea, tiparul,
 * lista și fișierul pentru bancă. Din îndreptarea pe salariu — fluturașii angajaților ei (toată luna lor): tiparul, PDF-ul
 * și trimiterea pe e-mail (din îndreptarea aprobată sau achitată).
 */
export default function PaymentEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const { data: doc, reload: reloadDoc } = useFetch<Payment>(`/payroll/payments/${id}/`)
  const { data: lines, loading, reload: reloadLines } = useFetch<PaymentLine[]>(`/payroll/payments/${id}/lines/`)
  const { data: bases } = useFetch<Paged<Payroll>>('/payroll/payrolls/', { status: 'approved', page_size: 500 })
  const [print, setPrint] = useState<'payment_sheet' | 'bank_list' | 'payslip' | null>(null)
  const [slipEmployee, setSlipEmployee] = useState<number | undefined>()
  const [mailOpen, setMailOpen] = useState(false)
  const [paying, setPaying] = useState(false)
  const [form] = Form.useForm()
  const [header] = Form.useForm<Header>()
  const [dirty, setDirty] = useState(false)
  const kind = Form.useWatch('kind', header)
  const base = Form.useWatch('payroll', header)
  const reload = () => { reloadDoc(); reloadLines() }
  const draft = !!doc && doc.status === 'draft' && !doc.deletion_mark && hasPerm('payroll.edit')

  // antetul se pune din document la deschidere și după salvare
  useEffect(() => {
    if (!doc) return
    header.setFieldsValue(toHeader(doc))
    setDirty(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.id, doc?.date, doc?.kind, doc?.payroll, doc?.year, doc?.month, doc?.method, doc?.note])

  /** Salvează antetul; dacă se schimbă baza rândurilor și sunt corectări de mână, întreabă întâi. true — salvat. */
  const saveHeader = async () => {
    if (!dirty || !doc) return true
    let v: Header
    try {
      v = await header.validateFields()
    } catch {
      return false
    }
    const refill = REFILL.some((k) => !same(v, toHeader(doc), k))
    if (refill && (lines ?? []).some((x) => x.manual)) {
      const ok = await new Promise<boolean>((resolve) => Modal.confirm({
        title: t('pp.refillConfirm'), onOk: () => resolve(true), onCancel: () => resolve(false),
      }))
      if (!ok) return false
    }
    try {
      await api.patch(`/payroll/payments/${id}/`, {
        date: v.date.format('YYYY-MM-DD'), kind: v.kind, payroll: v.kind === 'salary' ? v.payroll ?? null : null,
        ...(v.payroll ? {} : { year: v.ym.year(), month: v.ym.month() + 1 }), method: v.method, note: v.note ?? '',
      })
      setDirty(false)
      reload()
      return true
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  useUnsavedGuard(dirty, saveHeader)
  const title = doc ? t('pp.heading', { number: doc.number, date: dayjs(doc.date).format('DD.MM.YYYY') }) : ''
  useTabTitle(doc ? { key: 'desk.tab.payment', params: { number: doc.number } } : null)

  if (!doc) return <Card><Spin /></Card>
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
  const post = async (action: string, body?: unknown) => {
    if (await saveHeader()) await run(() => api.post(`/payroll/payments/${id}/${action}/`, body))
  }
  const pay = async () => {
    const v = await form.validateFields()
    await post('pay', { paid_on: v.paid_on.format('YYYY-MM-DD'), reference: v.reference })
    setPaying(false)
  }
  const patch = (r: PaymentLine, field: string, value: unknown) => run(() => api.patch(`/payroll/payment-lines/${r.id}/`, { [field]: value }))
  const num = (v: string) => Number(String(v).replace(/\s/g, '').replace(',', '.'))
  const sumCell = (field: 'gross' | 'exemption' | 'cnam' | 'income_tax' | 'deductions' | 'amount', bold = false) => ({
    dataIndex: field, width: field === 'amount' ? 140 : 120, align: 'right' as const,
    render: (v: string, r: PaymentLine) => draft
      ? <InputNumber key={`${r.id}-${field}-${v}`} size="small" min={0} step={10} defaultValue={Number(v)} style={{ width: field === 'amount' ? 120 : 105 }}
          onBlur={(e) => { const n = num(e.target.value); if (!Number.isNaN(n) && n !== Number(v)) patch(r, field, n) }} />
      : bold ? <b>{money(v)}</b> : money(v),
  })
  const monthLabel = `${dayjs().month(doc.month - 1).format('MMMM')} ${doc.year}`
  const salary = doc.kind === 'salary'
  const baseOptions = [
    { value: 0, label: t('pp.onBalance') },
    ...(bases?.results ?? []).map((x) => ({
      value: x.id, label: `${t('pp.baseLabel', { number: x.number, month: String(x.month).padStart(2, '0'), year: x.year })}${x.subdivision_name ? ` · ${x.subdivision_name}` : ''}`,
    })),
  ]

  return (
    <Card className="doc-form" title={<Space wrap>
      {title}<Tag>{t(`pp.kinds.${doc.kind}`)}</Tag><Tag color={PAYMENT_STATUS_COLOR[doc.status]}>{doc.status_label}</Tag>
      {doc.it_park && <Tooltip title={t('itp.paymentHint')}><Tag color="purple">{t('itp.finalTag')}</Tag></Tooltip>}
      {doc.payroll && <Tag color={PAYROLL_STATUS_COLOR.approved} style={{ cursor: 'pointer' }} onClick={() => navigate(`/payroll/${doc.payroll}`)}>
        {t('pp.baseRef', { label: doc.payroll_number })}</Tag>}
    </Space>} extra={<Space wrap>
      {!doc.deletion_mark && <>
        {draft && <Button icon={<SaveOutlined />} disabled={!dirty} onClick={saveHeader}>{t('common.save')}</Button>}
        {draft && <Popconfirm title={t('pp.refillConfirm')} onConfirm={() => post('fill')}><Button icon={<ReloadOutlined />}>{t('pp.refill')}</Button></Popconfirm>}
        {doc.status === 'draft' && hasPerm('payroll.approve') && <Button type="primary" icon={<CheckOutlined />} onClick={() => post('approve')}>{t('pay.approve')}</Button>}
        {doc.status === 'approved' && hasPerm('payroll.approve') && <Button type="primary" icon={<DollarOutlined />}
          onClick={() => { form.setFieldsValue({ paid_on: dayjs(), reference: doc.reference }); setPaying(true) }}>{t('pp.pay')}</Button>}
        {doc.status !== 'draft' && hasPerm('payroll.approve') && <Popconfirm title={t('pp.reopenConfirm')} onConfirm={() => post('reopen')}>
          <Button icon={<RollbackOutlined />}>{t('wt.doc.reopen')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrint('payment_sheet')}>{t('pp.printSheet')}</Button>
        {doc.totals.card > 0 && <Button icon={<BankOutlined />} onClick={() => setPrint('bank_list')}>{t('pp.bankList')}</Button>}
        {doc.totals.card > 0 && hasPerm('payroll.export') && <Button icon={<DownloadOutlined />} onClick={() =>
          downloadFile(`/payroll/payments/${id}/bank-file/`, {}, `banca-${doc.year}-${String(doc.month).padStart(2, '0')}-${doc.number}.csv`)
            .catch((e) => message.error(errorText(e)))}>{t('pp.bankFile')}</Button>}
        {salary && <Button icon={<FileTextOutlined />} onClick={() => { setSlipEmployee(undefined); setPrint('payslip') }}>{t('pay.printSlips')}</Button>}
        {salary && <Button icon={<FilePdfOutlined />} onClick={() => downloadFile(`/payroll/payments/${id}/payslip-pdf/`, {},
          `fluturasi-${doc.year}-${String(doc.month).padStart(2, '0')}-${doc.number}.pdf`).catch((e) => message.error(errorText(e)))}>{t('pay.slipsPdf')}</Button>}
        {salary && hasPerm('payroll.edit') && <Tooltip title={doc.status === 'draft' ? t('pay.mailOnlyApproved') : ''}>
          <Button icon={<MailOutlined />} disabled={doc.status === 'draft'} onClick={() => setMailOpen(true)}>{t('pay.mailSlips')}</Button>
        </Tooltip>}
        {doc.status !== 'paid' && hasPerm('payroll.delete') && <MarkButton endpoint="/payroll/payments/" row={doc} onDone={reloadDoc} text />}
      </>}
      <CloseForm to="/payroll/payments" />
    </Space>}>
      <MarkedBanner endpoint="/payroll/payments/" row={doc} onDone={reloadDoc} canUnmark={hasPerm('payroll.delete')} />
      <Form form={header} layout="vertical" disabled={!draft} onValuesChange={(changed: Partial<Header>) => {
        if (changed.kind === 'advance') header.setFieldValue('payroll', null)
        if (changed.payroll) {
          const b = bases?.results.find((x) => x.id === changed.payroll)
          if (b) header.setFieldValue('ym', dayjs(`${b.year}-${String(b.month).padStart(2, '0')}-01`))
        }
        setDirty(true)
      }}>
        <Row gutter={12}>
          <Col xs={12} md={3}><Form.Item name="date" label={t('ord.date')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={3}><Form.Item name="kind" label={t('pp.kind')} rules={[{ required: true }]}>
            <Select options={['salary', 'advance'].map((k) => ({ value: k, label: t(`pp.kinds.${k}`) }))} /></Form.Item></Col>
          <Col xs={24} md={7}><Form.Item name="payroll" label={t('pp.base')} getValueProps={(v) => ({ value: v ?? 0 })}
            normalize={(v) => (v ? v : null)} extra={kind === 'advance' ? t('pp.advanceNoBase') : undefined}>
            <Select showSearch optionFilterProp="label" disabled={kind === 'advance'} options={baseOptions} /></Form.Item></Col>
          <Col xs={12} md={3}><Form.Item name="ym" label={t('pay.month')} rules={[{ required: true }]} extra={base ? t('pp.monthFromBase') : undefined}>
            <DatePicker picker="month" format="MM.YYYY" disabled={!!base} allowClear={false} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="method" label={t('pp.method')} rules={[{ required: true }]}>
            <Select options={['all', 'card', 'cash'].map((k) => ({ value: k, label: t(`pp.methods.${k}`) }))} /></Form.Item></Col>
          <Col xs={24} md={4}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row>
      </Form>
      {draft && dirty && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('pp.refillHint')} />}
      <Descriptions size="small" bordered column={{ xs: 1, sm: 2, lg: 4 }} style={{ marginBottom: 12 }}
        styles={{ label: { whiteSpace: 'nowrap' }, content: { whiteSpace: 'nowrap' } }} items={[
          { key: 'month', label: t('pay.month'), children: monthLabel },
          { key: 'card', label: t('pp.card'), children: money(doc.totals.card) },
          { key: 'cash', label: t('pp.cash'), children: money(doc.totals.cash) },
          { key: 'gross', label: t('pay.gross'), children: money(doc.totals.gross) },
          { key: 'ex', label: t('pay.exemption'), children: money(doc.totals.exemption) },
          { key: 'cnam', label: 'CNAM', children: money(doc.totals.cnam) },
          { key: 'tax', label: t('pay.tax'), children: money(doc.totals.income_tax) },
          { key: 'total', label: t('pp.total'), children: <b>{money(doc.totals.total)}</b> },
          ...(doc.paid_on ? [{ key: 'paid', label: t('pp.paidOn'), children: `${dayjs(doc.paid_on).format('DD.MM.YYYY')} ${doc.reference}` }] : []),
        ]} />
      <Table<PaymentLine> rowKey="id" size="small" loading={loading} dataSource={lines ?? []} pagination={false} exportName={`${title} — ${monthLabel}`}
        columns={[
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 90 },
          { title: t('staff.fullName'), dataIndex: 'employee_name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}?tab=pay`)}>{v}</a> },
          { title: t('pp.method'), dataIndex: 'method', width: 100, render: (v: string) => t(`pp.methods.${v}`) },
          { title: 'IBAN', dataIndex: 'iban', width: 240 },
          { title: t('pay.gross'), ...sumCell('gross') },
          { title: t('pay.exemption'), ...sumCell('exemption') },
          { title: 'CNAM', ...sumCell('cnam') },
          { title: t('pay.tax'), ...sumCell('income_tax') },
          { title: t('pay.deductions'), ...sumCell('deductions') },
          { title: t('pp.toPay'), ...sumCell('amount', true) },
          { title: '', key: 'm', width: 40, render: (_: unknown, r: PaymentLine) => r.manual ? <Tooltip title={t('pp.manualHint')}><Tag color="orange">✎</Tag></Tooltip> : null },
          ...(salary ? [{ title: '', key: 'slip', width: 40, render: (_: unknown, r: PaymentLine) => (
            <Tooltip title={t('pay.printSlip')}><Button size="small" type="text" icon={<FileTextOutlined />}
              onClick={() => { setSlipEmployee(r.employee); setPrint('payslip') }} /></Tooltip>) }] : []),
          { title: t('org.notes'), dataIndex: 'note', render: (v: string, r) => draft
            ? <Input key={`${r.id}-${v}`} size="small" defaultValue={v} onBlur={(e) => { if (e.target.value !== v) run(() => api.patch(`/payroll/payment-lines/${r.id}/`, { note: e.target.value })) }} />
            : v },
          ...(draft ? [{ title: '', key: 'del', width: 40, render: (_: unknown, r: PaymentLine) => (
            <Popconfirm title={t('common.confirmDelete')} onConfirm={() => run(() => api.delete(`/payroll/payment-lines/${r.id}/`))}>
              <Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>) }] : []),
        ]} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>{t(doc.kind === 'advance' ? 'pp.advanceLegend' : 'pp.salaryLegend')}</Typography.Paragraph>
      <Modal open={paying} title={t('pp.pay')} onOk={pay} onCancel={() => setPaying(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="paid_on" label={t('pp.paidOn')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" /></Form.Item>
          <Form.Item name="reference" label={t('pp.reference')} extra={t('pp.referenceHint')}><Input /></Form.Item>
        </Form>
      </Modal>
      {mailOpen && <PayslipMail paymentId={doc.id} onClose={() => setMailOpen(false)} />}
      {print && <PrintDialog open onClose={() => setPrint(null)} docType={print}
        url={`/payroll/payments/${id}/${print === 'bank_list' ? 'bank-list' : print === 'payslip' ? 'payslip' : 'print'}/`}
        params={print === 'payslip' && slipEmployee ? { employee: slipEmployee } : {}} optionKeys={[]}
        title={t(print === 'bank_list' ? 'pp.bankList' : print === 'payslip' ? 'pay.printSlips' : 'pp.printSheet')} />}
    </Card>
  )
}

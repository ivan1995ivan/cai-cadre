import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, DatePicker, Form, Input, Popconfirm, Row, Select, Space, Spin, Tag, Typography, message } from 'antd'
import { CheckOutlined, DeleteOutlined, PlusOutlined, PrinterOutlined, RollbackOutlined, SaveOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import CloseForm from '../../components/CloseForm'
import EmployeeSelect from '../../components/EmployeeSelect'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import PrintDialog from '../../components/PrintDialog'
import { ROW_TONE } from '../../components/rowTone'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { PayItemChange, PayItemChangeLine } from '../../api/payroll'
import type { Employment } from '../../api/staff'
import { useApp } from '../../auth/AppContext'
import { PlannedRowFields, useEmployeeRows, usePersonalTypes } from './PlannedRows'
import { useTabTitle } from '../../layout/tabs'

const STATUS_COLOR: Record<string, string> = { draft: 'gold', approved: 'green' }

/** Documentele „Modificarea acumulărilor planificate” (Salarizare): schimbările fără ordin de personal. */
export default function PayItemChangesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [year, setYear] = useState(dayjs().year())
  const [status, setStatus] = useState<string | undefined>()
  const { data, loading } = useFetch<Paged<PayItemChange>>('/payroll/item-changes/', { year, status, page_size: 500 })
  const rows = data?.results ?? []
  const create = async () => {
    try {
      const r = await api.post<PayItemChange>('/payroll/item-changes/', { date: dayjs().format('YYYY-MM-DD'), lines: [] })
      navigate(`/payroll/item-changes/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <Card title={t('menu.payItemChanges')} extra={<Space>
      <Select style={{ width: 100 }} value={year} onChange={setYear}
        options={Array.from({ length: 5 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />
      <Select allowClear style={{ width: 140 }} placeholder={t('ord.status')} value={status} onChange={setStatus}
        options={['draft', 'approved'].map((s) => ({ value: s, label: t(`pay.pl.status.${s}`) }))} />
    </Space>}>
      <Space style={{ marginBottom: 12 }} wrap>
        {hasPerm('payroll.create') && <Button type="primary" icon={<PlusOutlined />} onClick={create}>{t('pay.pl.newDoc')}</Button>}
        <Typography.Text type="secondary">{t('pay.pl.docHint')}</Typography.Text>
      </Space>
      <Table<PayItemChange> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} exportName={t('menu.payItemChanges')}
        rowTone={(r) => ROW_TONE.payItemChange(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/payroll/item-changes/${r.id}`) })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 140, render: (v: string, r) => <a onClick={() => navigate(`/payroll/item-changes/${r.id}`)}>{v}</a> },
          { title: t('ord.date'), dataIndex: 'date', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('ord.status'), dataIndex: 'status', width: 110, render: (v: string, r) => <Tag color={STATUS_COLOR[v]}>{t(`pay.pl.status.${v}`, { defaultValue: r.status_label })}</Tag> },
          { title: t('pay.pl.employees'), dataIndex: 'employees' },
          { title: t('pay.pl.rows'), key: 'n', width: 80, align: 'right', render: (_: unknown, r) => r.lines.length },
          { title: t('org.notes'), dataIndex: 'note' },
        ]} />
    </Card>
  )
}

/** Raportul de muncă al angajatului din rând (gol — cel de bază). */
function JobSelect({ employee, value, onChange, disabled }: { employee: number | null; value: number | null; onChange: (v: number | null) => void; disabled?: boolean }) {
  const { t } = useTranslation()
  const { data: jobs } = useFetch<Employment[]>(employee ? '/staff/employments/' : null, { employee })
  return <Select allowClear style={{ width: 240 }} placeholder={t('pay.pl.mainJob')} disabled={disabled} value={value ?? undefined}
    onChange={(v) => onChange(v ?? null)}
    options={(jobs ?? []).filter((j) => j.status !== 'ended').map((j) => ({ value: j.id, label: `${t(`staff.kinds.${j.kind}`, { defaultValue: j.kind_label })}: ${j.occupation_name}` }))} />
}

function LineRow({ line, set, onRemove, typeOptions, disabled }: {
  line: PayItemChangeLine
  set: (patch: Partial<PayItemChangeLine>) => void
  onRemove: () => void
  typeOptions: { value: number; label: string }[]
  disabled: boolean
}) {
  const { t } = useTranslation()
  const existing = useEmployeeRows(line.employee)
  return (
    <Space wrap size={4} style={{ padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6, width: '100%' }}>
      <EmployeeSelect value={line.employee} label={line.employee_name} disabled={disabled} style={{ width: 260 }}
        onChange={(v) => set({ employee: (v as number | null) ?? null, employment: null, target: null })} />
      <JobSelect employee={line.employee} value={line.employment} disabled={disabled} onChange={(v) => set({ employment: v })} />
      <PlannedRowFields row={line} set={set} typeOptions={typeOptions} existing={existing} disabled={disabled} fromHint={t('pay.pl.fromDoc')} />
      {!disabled && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={onRemove} />}
    </Space>
  )
}

/** Documentul „Modificarea acumulărilor planificate”: rândurile (angajatul, raportul, tipul, acțiunea, valorile, perioada,
 *  temeiul), aprobarea (intră în fila „Salariu”), anularea aprobării (se întorc), tiparul. */
export function PayItemChangeEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const { hasPerm } = useApp()
  const { data: doc, reload } = useFetch<PayItemChange>(`/payroll/item-changes/${id}/`)
  useTabTitle(doc ? { key: 'desk.tab.itemChange', params: { number: doc.number } } : null)
  const { options } = usePersonalTypes()
  const [lines, setLines] = useState<PayItemChangeLine[]>([])
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [print, setPrint] = useState(false)
  const [header] = Form.useForm()
  const draft = !!doc && doc.status === 'draft' && !doc.deletion_mark && hasPerm('payroll.edit')

  useEffect(() => {
    if (!doc) return
    setLines(doc.lines)
    header.setFieldsValue({ date: dayjs(doc.date), note: doc.note })
    setDirty(false)
  }, [doc, header])

  const save = async (quiet = false) => {
    if (!doc) return false
    try {
      const h = await header.validateFields()
      await api.patch(`/payroll/item-changes/${doc.id}/`, {
        date: h.date.format('YYYY-MM-DD'), note: h.note ?? '',
        lines: lines.map((l) => ({ id: l.id, employee: l.employee, employment: l.employment, pay_type: l.pay_type, action: l.action,
          target: l.target ?? null, amount: l.amount ?? null, percent: l.percent ?? null, quantity: l.quantity ?? null,
          date_from: l.date_from ?? null, date_to: l.date_to ?? null, document: l.document ?? '' })),
      })
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

  const act = async (what: 'approve' | 'unapprove') => {
    setBusy(true)
    try {
      if (what === 'approve' && dirty && !(await save(true))) return
      await api.post(`/payroll/item-changes/${id}/${what}/`)
      message.success(t(what === 'approve' ? 'pay.pl.approved' : 'pay.pl.unapproved'))
      reload()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  if (!doc) return <Spin />
  const set = (i: number, patch: Partial<PayItemChangeLine>) => { setLines(lines.map((l, k) => (k === i ? { ...l, ...patch } : l))); setDirty(true) }
  return (
    <Card title={<Space wrap>{t('menu.payItemChanges')}<b>{doc.number}</b><Tag color={STATUS_COLOR[doc.status]}>{t(`pay.pl.status.${doc.status}`, { defaultValue: doc.status_label })}</Tag></Space>}
      extra={<Space wrap>
        {draft && <Button icon={<SaveOutlined />} onClick={() => save()}>{t('common.save')}</Button>}
        {draft && hasPerm('payroll.approve') && <Popconfirm title={t('pay.pl.approveConfirm')} onConfirm={() => act('approve')}>
          <Button type="primary" icon={<CheckOutlined />} loading={busy}>{t('pay.pl.approve')}</Button></Popconfirm>}
        {doc.status === 'approved' && hasPerm('payroll.approve') && <Popconfirm title={t('pay.pl.unapproveConfirm')} onConfirm={() => act('unapprove')}>
          <Button icon={<RollbackOutlined />} loading={busy}>{t('pay.pl.unapprove')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrint(true)}>{t('lv.print')}</Button>
        {doc.status === 'draft' && hasPerm('payroll.delete') && <MarkButton endpoint="/payroll/item-changes/" row={doc} onDone={reload} text />}
        <CloseForm to="/payroll/item-changes" />
      </Space>}>
      <MarkedBanner endpoint="/payroll/item-changes/" row={doc} onDone={reload} canUnmark={hasPerm('payroll.delete')} />
      {doc.status === 'approved' && <Alert type="success" showIcon style={{ marginBottom: 12 }} title={t('pay.pl.approvedHint')} />}
      <Form form={header} layout="vertical" disabled={!draft} onValuesChange={() => setDirty(true)}>
        <Row gutter={16}>
          <Col xs={24} md={6}><Form.Item name="date" label={t('ord.date')} rules={[{ required: true }]} extra={t('pay.pl.dateHint')}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={18}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row>
      </Form>
      <Space orientation="vertical" style={{ width: '100%' }} size={6}>
        {lines.map((l, i) => <LineRow key={l.id ?? `n${i}`} line={l} set={(p) => set(i, p)} typeOptions={options} disabled={!draft}
          onRemove={() => { setLines(lines.filter((_x, k) => k !== i)); setDirty(true) }} />)}
        {draft && <Button icon={<PlusOutlined />} onClick={() => { setLines([...lines, { employee: null, employment: null, pay_type: null, action: 'add' }]); setDirty(true) }}>
          {t('pay.pl.addRow')}</Button>}
        <Typography.Text type="secondary">{t('pay.pl.docRowsHint')}</Typography.Text>
      </Space>
      {print && <PrintDialog open onClose={() => setPrint(false)} docType="pay_item_change" url={`/payroll/item-changes/${doc.id}/print/`}
        params={{}} optionKeys={[]} title={`${t('menu.payItemChanges')} ${doc.number}`} />}
    </Card>
  )
}

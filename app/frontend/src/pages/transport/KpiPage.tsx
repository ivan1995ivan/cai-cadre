import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Popconfirm, Row, Select, Space, Spin, Tag, Tooltip, Typography, message } from 'antd'
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
import type { KpiDetail, KpiLine, KpiSheet } from '../../api/transport'

const STATUS_COLOR: Record<string, string> = { draft: 'gold', approved: 'green' }
const money = (v: number | string) => Number(v).toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const num = (v: number | string | null, digits = 2) => (v === null || v === '' ? '—' : Number(v).toLocaleString('ro-RO', { maximumFractionDigits: digits }))
const scoreColor = (v: number | null) => (v === null ? 'default' : v >= 80 ? 'green' : v >= 50 ? 'gold' : 'red')

/** Fișele KPI ale lunii (Salarizare → KPI-ul șoferilor). */
export default function KpiSheetsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [year, setYear] = useState(dayjs().year())
  const [creating, setCreating] = useState(false)
  const { data, loading } = useFetch<Paged<KpiSheet>>('/transport/kpi-sheets/', { year, page_size: 500 })
  const rows = data?.results ?? []
  return (
    <Card title={t('menu.kpiSheets')} extra={<Select style={{ width: 100 }} value={year} onChange={setYear}
      options={Array.from({ length: 5 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />}>
      <Space style={{ marginBottom: 12 }} wrap>
        {hasPerm('transport.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>{t('kpi.new')}</Button>}
        <Typography.Text type="secondary">{t('kpi.hint')}</Typography.Text>
      </Space>
      <Table<KpiSheet> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} exportName={t('menu.kpiSheets')}
        rowTone={(r) => ROW_TONE.payItemChange(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/transport/kpi-sheets/${r.id}`) })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 130, render: (v: string, r) => <a onClick={() => navigate(`/transport/kpi-sheets/${r.id}`)}>{v}</a> },
          { title: t('kpi.month'), key: 'm', width: 100, render: (_: unknown, r) => `${String(r.month).padStart(2, '0')}.${r.year}` },
          { title: t('kpi.date'), dataIndex: 'date', width: 110, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('ord.status'), dataIndex: 'status', width: 110, render: (v: string) => <Tag color={STATUS_COLOR[v]}>{t(`tr.status.${v}`)}</Tag> },
          { title: t('mv.subdivision'), dataIndex: 'subdivision_name', render: (v: string) => v || t('mv.allCompany') },
          { title: t('kpi.people'), key: 'p', width: 90, align: 'right', render: (_: unknown, r) => r.totals.people },
          { title: t('kpi.avgScore'), key: 's', width: 120, align: 'right', render: (_: unknown, r) => (r.totals.avg_score === null ? '—' : `${num(r.totals.avg_score)} %`) },
          { title: t('kpi.amount'), key: 'a', width: 130, align: 'right', render: (_: unknown, r) => money(r.totals.amount) },
        ]} />
      {creating && <CreateDialog onClose={() => setCreating(false)} onCreated={(id) => navigate(`/transport/kpi-sheets/${id}`)} />}
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
      const m: Dayjs = v.month
      const r = await api.post<KpiSheet>('/transport/kpi-sheets/', {
        year: m.year(), month: m.month() + 1, date: v.date.format('YYYY-MM-DD'), subdivision: v.subdivision ?? null })
      await api.post(`/transport/kpi-sheets/${r.data.id}/fill/`)
      onCreated(r.data.id)
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Card size="small" style={{ marginTop: 12 }} title={t('kpi.new')} extra={<Space>
      <Button onClick={onClose}>{t('common.cancel')}</Button>
      <Button type="primary" loading={busy} onClick={submit}>{t('kpi.create')}</Button></Space>}>
      <Form form={form} layout="vertical" initialValues={{ month: dayjs().subtract(1, 'month').startOf('month'), date: dayjs() }}>
        <Row gutter={16}>
          <Col xs={24} md={6}><Form.Item name="month" label={t('kpi.month')} rules={[{ required: true }]} extra={t('kpi.monthHint')}>
            <DatePicker picker="month" format="MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={6}><Form.Item name="date" label={t('kpi.date')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="subdivision" label={t('mv.subdivision')} extra={t('kpi.subdivisionHint')}>
            <SubdivisionSelect /></Form.Item></Col>
        </Row>
      </Form>
    </Card>
  )
}

/** Fișa KPI: rândurile șoferilor cu indicatorii (valoarea → nota, ponderea), punctajul și prima; valorile se pot scrie de mână
 *  (rămân la completarea din nou); aprobarea pune prima în salariul lunii. */
export function KpiSheetEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const { hasPerm } = useApp()
  const { data: doc, reload } = useFetch<KpiSheet>(`/transport/kpi-sheets/${id}/`)
  useTabTitle(doc ? { key: 'desk.tab.kpiSheet', params: { number: doc.number } } : null)
  const [busy, setBusy] = useState(false)
  const [print, setPrint] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [header] = Form.useForm()
  const draft = !!doc && doc.status === 'draft' && !doc.deletion_mark && hasPerm('transport.edit')

  useEffect(() => {
    if (!doc) return
    header.setFieldsValue({ date: dayjs(doc.date), note: doc.note })
    setDirty(false)
  }, [doc, header])

  const save = async (quiet = false) => {
    if (!doc) return false
    try {
      const h = await header.validateFields()
      await api.patch(`/transport/kpi-sheets/${doc.id}/`, { date: h.date.format('YYYY-MM-DD'), note: h.note ?? '' })
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
      await api.post(`/transport/kpi-sheets/${id}/${what}/`, body)
      if (done) message.success(done)
      reload()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  if (!doc) return <Spin />
  const codes = Array.from(new Map(doc.lines.flatMap((l) => l.details.map((d) => [d.code, d] as const))).values())
  return (
    <Card title={<Space wrap>{t('kpi.title')}<b>{doc.number}</b><Tag color={STATUS_COLOR[doc.status]}>{t(`tr.status.${doc.status}`)}</Tag></Space>}
      extra={<Space wrap>
        {draft && <Button icon={<SaveOutlined />} onClick={() => save()}>{t('common.save')}</Button>}
        {draft && <Button icon={<ReloadOutlined />} loading={busy} onClick={() => post('fill', {}, t('kpi.filled'))}>{t('kpi.fill')}</Button>}
        {draft && hasPerm('transport.approve') && <Popconfirm title={t('kpi.approveConfirm')} onConfirm={() => post('approve', {}, t('kpi.approved'))}>
          <Button type="primary" icon={<CheckOutlined />} loading={busy}>{t('kpi.approve')}</Button></Popconfirm>}
        {doc.status === 'approved' && hasPerm('transport.approve') && <Popconfirm title={t('kpi.unapproveConfirm')} onConfirm={() => post('unapprove', {}, t('kpi.unapproved'))}>
          <Button icon={<RollbackOutlined />} loading={busy}>{t('kpi.unapprove')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrint(true)}>{t('lv.print')}</Button>
        {doc.status === 'draft' && hasPerm('transport.delete') && <MarkButton endpoint="/transport/kpi-sheets/" row={doc} onDone={reload} text />}
        <CloseForm to="/transport/kpi-sheets" />
      </Space>}>
      <MarkedBanner endpoint="/transport/kpi-sheets/" row={doc} onDone={reload} canUnmark={hasPerm('transport.delete')} />
      {doc.status === 'approved' && <Alert type="success" showIcon style={{ marginBottom: 12 }} title={t('kpi.approvedHint')} />}
      <Form form={header} layout="vertical" disabled={!draft} onValuesChange={() => setDirty(true)}>
        <Row gutter={16}>
          <Col xs={24} md={4}><Form.Item label={t('kpi.month')}><Input disabled value={`${String(doc.month).padStart(2, '0')}.${doc.year}`} /></Form.Item></Col>
          <Col xs={24} md={5}><Form.Item name="date" label={t('kpi.date')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={15}><Form.Item label={t('mv.subdivision')}><Input disabled value={doc.subdivision_name || t('mv.allCompany')} /></Form.Item></Col>
          <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row>
      </Form>
      <Typography.Paragraph type="secondary">{t('kpi.rulesHint')}</Typography.Paragraph>
      <Table<KpiLine> rowKey="id" size="small" dataSource={doc.lines} pagination={false} exportName={`${t('kpi.title')} ${doc.number}`}
        scroll={{ x: 'max-content' }} locale={{ emptyText: t('kpi.empty') }}
        columns={[
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 80, fixed: 'left' },
          { title: t('kpi.driver'), dataIndex: 'employee_name', width: 180, fixed: 'left',
            render: (v: string, r) => <>{v}<br /><Typography.Text type="secondary">{r.occupation} · {r.scheme_code}</Typography.Text></> },
          ...codes.map((c) => ({
            title: <Tooltip title={c.name}>{c.code}</Tooltip>, key: c.code, width: 115,
            render: (_: unknown, r: KpiLine) => {
              const d = r.details.find((x) => x.code === c.code)
              return d ? <DetailCell detail={d} editable={draft} onSet={(value) => post('line', { line: r.id, overrides: { [d.code]: value } })} /> : null
            },
          })),
          { title: t('kpi.base'), dataIndex: 'base', width: 95, align: 'right', render: money },
          { title: t('kpi.score'), dataIndex: 'score', width: 95, align: 'right',
            render: (v: string | null) => <Tag color={scoreColor(v === null ? null : Number(v))}>{v === null ? '—' : `${num(v)} %`}</Tag> },
          { title: t('kpi.amount'), dataIndex: 'amount', width: 105, align: 'right', render: (v: string) => <b>{money(v)}</b> },
          { title: t('mv.how'), dataIndex: 'note', width: 300, render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
        ]}
        summary={() => (doc.lines.length ? (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={codes.length + 4} align="right"><b>{t('mv.total')}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={1} align="right"><b>{money(doc.totals.amount)}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={2} />
          </Table.Summary.Row>) : null)} />
      {print && <PrintDialog open onClose={() => setPrint(false)} docType="kpi_sheet" url={`/transport/kpi-sheets/${doc.id}/print/`}
        params={{}} optionKeys={[]} title={`${t('kpi.title')} ${doc.number}`} />}
    </Card>
  )
}

/** Indicatorul pe rând: valoarea (din date sau scrisă de mână) → nota; explicația la trecerea cu mausul. */
function DetailCell({ detail, editable, onSet }: { detail: KpiDetail; editable: boolean; onSet: (v: number | '') => void }) {
  const { t } = useTranslation()
  const [value, setValue] = useState<number | null>(detail.value)
  useEffect(() => setValue(detail.value), [detail.value])
  const tip = <>{detail.how}<br />{t('kpi.weight')}: {num(detail.weight)} · {t('kpi.full')}: {num(detail.full_at)} · {t('kpi.zero')}: {num(detail.zero_at)}</>
  return (
    <Tooltip title={tip}>
      <Space size={2} orientation="vertical">
        {editable ? <Space size={2}>
          <InputNumber size="small" min={0} value={value} style={{ width: 72 }} placeholder="—" onChange={(v) => setValue(v)}
            onBlur={() => { if (value !== null && value !== detail.value) onSet(value) }}
            onPressEnter={() => { if (value !== null && value !== detail.value) onSet(value) }} />
          {detail.manual && <Button size="small" type="text" icon={<UndoOutlined />} title={t('kpi.reset')} onClick={() => onSet('')} />}
        </Space> : <span>{num(detail.value)} {detail.unit}{detail.manual && <Tag style={{ marginInlineStart: 4 }}>{t('mv.manual')}</Tag>}</span>}
        <Tag color={scoreColor(detail.score)}>{detail.score === null ? t('kpi.noData') : `${num(detail.score)} %`}</Tag>
      </Space>
    </Tooltip>
  )
}

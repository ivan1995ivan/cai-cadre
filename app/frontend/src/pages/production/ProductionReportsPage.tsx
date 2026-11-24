import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Popconfirm, Row, Segmented, Select, Space, Spin, Tag, Tooltip, Typography, message,
} from 'antd'
import { CheckOutlined, DeleteOutlined, PlusOutlined, PrinterOutlined, RollbackOutlined, SaveOutlined, TeamOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import CloseForm from '../../components/CloseForm'
import ExcelImport from '../../components/ExcelImport'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import PrintDialog from '../../components/PrintDialog'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { money } from '../../api/payroll'
import { blankLine, type Brigade, type Operation, type ProductionLine, type ProductionMember, type ProductionReport } from '../../api/production'
import { useApp, useLocalName } from '../../auth/AppContext'
import { useTabTitle } from '../../layout/tabs'
import { PersonJob, num } from './ProductionSettings'

const STATUS_COLOR: Record<string, string> = { draft: 'gold', approved: 'green' }

/** Rapoartele de producție (Salarizare): lucrările în acord, individuale sau pe brigadă. */
export default function ProductionReportsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [month, setMonth] = useState(dayjs().startOf('month'))
  const [status, setStatus] = useState<string | undefined>()
  const { data, loading } = useFetch<Paged<ProductionReport>>('/production/reports/', { year: month.year(), month: month.month() + 1, status, page_size: 500 })
  const rows = data?.results ?? []
  const create = async (kind: 'individual' | 'brigade') => {
    try {
      const day = month.isSame(dayjs(), 'month') ? dayjs() : month.endOf('month')
      const r = await api.post<ProductionReport>('/production/reports/', { date: day.format('YYYY-MM-DD'), kind, brigade: null, lines: [], members: [] })
      navigate(`/production/reports/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const total = rows.filter((r) => r.status === 'approved' && !r.deletion_mark).reduce((s, r) => s + r.totals.amount, 0)
  return (
    <Card title={t('menu.productionReports')} extra={<Space>
      <DatePicker picker="month" format="MM.YYYY" allowClear={false} value={month} onChange={(d) => d && setMonth(d.startOf('month'))} />
      <Select allowClear style={{ width: 140 }} placeholder={t('ord.status')} value={status} onChange={setStatus}
        options={['draft', 'approved'].map((s) => ({ value: s, label: t(`prod.rep.status.${s}`) }))} />
    </Space>}>
      <Space style={{ marginBottom: 12 }} wrap>
        {hasPerm('production.create') && <>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => create('individual')}>{t('prod.rep.newIndividual')}</Button>
          <Button icon={<TeamOutlined />} onClick={() => create('brigade')}>{t('prod.rep.newBrigade')}</Button>
        </>}
        <Typography.Text type="secondary">{t('prod.rep.hint')}</Typography.Text>
      </Space>
      <Table<ProductionReport> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} exportName={t('menu.productionReports')}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/production/reports/${r.id}`) })}
        summary={() => rows.length ? <Table.Summary.Row><Table.Summary.Cell index={0} colSpan={5}><b>{t('prod.rep.approvedTotal')}</b></Table.Summary.Cell>
          <Table.Summary.Cell index={5} align="right"><b>{money(total)}</b></Table.Summary.Cell><Table.Summary.Cell index={6} colSpan={2} /></Table.Summary.Row> : null}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 120, render: (v: string, r) => <a onClick={() => navigate(`/production/reports/${r.id}`)}>{v}</a> },
          { title: t('ord.date'), dataIndex: 'date', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('prod.rep.kind'), dataIndex: 'kind', width: 110, render: (v: string) => t(`prod.rep.kinds.${v}`) },
          { title: t('ord.status'), dataIndex: 'status', width: 100, render: (v: string, r) => <Tag color={STATUS_COLOR[v]}>{t(`prod.rep.status.${v}`, { defaultValue: r.status_label })}</Tag> },
          { title: t('prod.rep.who'), dataIndex: 'who' },
          { title: t('prod.rep.amount'), key: 'amount', width: 120, align: 'right', render: (_: unknown, r) => money(r.totals.amount) },
          { title: t('prod.rep.normed'), key: 'normed', width: 100, align: 'right', render: (_: unknown, r) => num(r.totals.normed_hours, 2) },
          { title: t('org.notes'), dataIndex: 'note' },
        ]} />
    </Card>
  )
}

function useOperations() {
  const { t } = useTranslation()
  const localName = useLocalName()
  const { data } = useFetch<Operation[]>('/production/operations/', { active: 1 })
  return (data ?? []).map((o) => ({ value: o.id, label: `${o.code} — ${localName(o)} (${t(`prod.units.${o.unit}`, { defaultValue: o.unit_label })})` }))
}

const n = (v: unknown) => (v === '' || v === null || v === undefined ? null : Number(v))

function LineRow({ line, set, onRemove, operations, individual, disabled }: {
  line: ProductionLine; set: (p: Partial<ProductionLine>) => void; onRemove: () => void
  operations: { value: number; label: string }[]; individual: boolean; disabled: boolean
}) {
  const { t } = useTranslation()
  const box = { padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6, width: '100%' }
  return (
    <Space wrap size={4} style={box}>
      {individual && <PersonJob employee={line.employee} employeeName={line.employee_name} employment={line.employment} disabled={disabled}
        onChange={(p) => set({ employee: p.employee, employment: p.employment, employee_name: p.employee_name ?? line.employee_name })} />}
      <Select showSearch optionFilterProp="label" style={{ width: 300 }} placeholder={t('prod.rep.operation')} disabled={disabled}
        value={line.operation ?? undefined} onChange={(v) => set({ operation: v ?? null })} options={operations} />
      <Tooltip title={t('prod.rep.quantity')}><InputNumber min={0} style={{ width: 120 }} placeholder={t('prod.rep.quantity')} disabled={disabled}
        value={n(line.quantity)} onChange={(v) => set({ quantity: v ?? 0 })} /></Tooltip>
      <Tooltip title={t('prod.rep.defectNofault')}><InputNumber min={0} style={{ width: 105 }} prefix={t('prod.rep.dNofault')} disabled={disabled}
        value={n(line.defect_nofault)} onChange={(v) => set({ defect_nofault: v ?? 0 })} /></Tooltip>
      <Tooltip title={t('prod.rep.defectPartial')}><InputNumber min={0} style={{ width: 105 }} prefix={t('prod.rep.dPartial')} disabled={disabled}
        value={n(line.defect_partial)} onChange={(v) => set({ defect_partial: v ?? 0 })} /></Tooltip>
      {Number(line.defect_partial) > 0 && <Tooltip title={t('prod.rep.defectPct')}><InputNumber min={0} max={100} style={{ width: 95 }} suffix="%" disabled={disabled}
        value={n(line.defect_partial_pct)} onChange={(v) => set({ defect_partial_pct: v ?? null })} /></Tooltip>}
      <Tooltip title={t('prod.rep.defectWorker')}><InputNumber min={0} style={{ width: 105 }} prefix={t('prod.rep.dWorker')} disabled={disabled}
        value={n(line.defect_worker)} onChange={(v) => set({ defect_worker: v ?? 0 })} /></Tooltip>
      {individual && <Tooltip title={t('prod.rep.hoursHint')}><InputNumber min={0} max={744} style={{ width: 110 }} suffix={t('prod.rep.h')} disabled={disabled}
        placeholder={t('prod.rep.hours')} value={n(line.hours)} onChange={(v) => set({ hours: v ?? null })} /></Tooltip>}
      <Input style={{ width: 180 }} placeholder={t('org.notes')} disabled={disabled} value={line.note} onChange={(e) => set({ note: e.target.value })} />
      {line.id && line.how && <Tooltip title={line.how}>
        {Number(line.amount) || line.rate ? <Tag color={line.progressive ? 'purple' : 'blue'}>{money(line.amount) || '0'} lei · {num(line.normed_hours, 2)} {t('prod.rep.h')}</Tag>
          : <Tag color="red">{t('prod.rep.notPriced')}</Tag>}
      </Tooltip>}
      {!disabled && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={onRemove} />}
    </Space>
  )
}

function MemberRow({ m, set, onRemove, disabled }: { m: ProductionMember; set: (p: Partial<ProductionMember>) => void; onRemove: () => void; disabled: boolean }) {
  const { t } = useTranslation()
  return (
    <Space wrap size={4} style={{ padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6, width: '100%' }}>
      <PersonJob employee={m.employee} employeeName={m.employee_name} employment={m.employment} disabled={disabled}
        onChange={(p) => set({ employee: p.employee, employment: p.employment, employee_name: p.employee_name ?? m.employee_name })} />
      <InputNumber min={0} max={744} style={{ width: 120 }} suffix={t('prod.rep.h')} placeholder={t('prod.rep.hours')} disabled={disabled}
        value={n(m.hours)} onChange={(v) => set({ hours: v ?? 0 })} />
      <Tooltip title={t('prod.ktuHint')}><InputNumber min={0} max={10} step={0.1} style={{ width: 120 }} prefix="KTU" disabled={disabled}
        value={n(m.coefficient)} onChange={(v) => set({ coefficient: v ?? 1 })} /></Tooltip>
      {m.id && <Tag color="blue">{money(m.amount) || '0'} lei · {num(m.normed_hours, 2)} {t('prod.rep.h')}{m.hourly ? ` · ${num(m.hourly, 2)} lei/oră` : ''}</Tag>}
      {!disabled && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={onRemove} />}
    </Space>
  )
}

/** Raportul de producție: antetul (data, felul, brigada, secția), lucrările, membrii brigăzii, aprobarea, tiparul, importul. */
export function ProductionReportEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const { hasPerm } = useApp()
  const { data: doc, reload } = useFetch<ProductionReport>(`/production/reports/${id}/`)
  useTabTitle(doc ? { key: 'desk.tab.productionReport', params: { number: doc.number } } : null)
  const operations = useOperations()
  const { data: brigades } = useFetch<Brigade[]>('/production/brigades/', { active: 1 })
  const [lines, setLines] = useState<ProductionLine[]>([])
  const [members, setMembers] = useState<ProductionMember[]>([])
  const [problems, setProblems] = useState<string[]>([])
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [print, setPrint] = useState(false)
  const [header] = Form.useForm()
  const kind = Form.useWatch('kind', header) ?? doc?.kind
  const draft = !!doc && doc.status === 'draft' && !doc.deletion_mark && hasPerm('production.edit')

  useEffect(() => {
    if (!doc) return
    setLines(doc.lines)
    setMembers(doc.members)
    setProblems(doc.problems)
    header.setFieldsValue({ date: dayjs(doc.date), kind: doc.kind, brigade: doc.brigade, subdivision: doc.subdivision, note: doc.note,
      shortfall_cause: doc.shortfall_cause || '' })
    setDirty(false)
  }, [doc, header])

  const save = async (quiet = false) => {
    if (!doc) return false
    try {
      const h = await header.validateFields()
      const r = await api.patch<ProductionReport>(`/production/reports/${doc.id}/`, {
        date: h.date.format('YYYY-MM-DD'), kind: h.kind, brigade: h.kind === 'brigade' ? h.brigade ?? null : null,
        subdivision: h.subdivision ?? null, note: h.note ?? '', shortfall_cause: h.shortfall_cause ?? '',
        lines: lines.filter((l) => l.operation).map((l) => ({ id: l.id, employment: h.kind === 'individual' ? l.employment : null, operation: l.operation,
          quantity: l.quantity || 0, defect_nofault: l.defect_nofault || 0, defect_partial: l.defect_partial || 0,
          defect_partial_pct: l.defect_partial_pct ?? null, defect_worker: l.defect_worker || 0, hours: l.hours ?? null, note: l.note ?? '' })),
        members: h.kind === 'brigade' ? members.filter((m) => m.employment).map((m) => ({ id: m.id, employment: m.employment, hours: m.hours || 0,
          coefficient: m.coefficient ?? 1 })) : [],
      })
      setDirty(false)
      setProblems(r.data.problems)
      if (!quiet) message.success(t('common.saved'))
      reload()
      return true
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  useUnsavedGuard(dirty && draft, () => save(true))

  const act = async (what: 'approve' | 'unapprove' | 'fill-members') => {
    setBusy(true)
    try {
      if (what !== 'unapprove' && dirty && !(await save(true))) return
      await api.post(`/production/reports/${id}/${what}/`)
      message.success(t(`prod.rep.done.${what}`))
      reload()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  if (!doc) return <Spin />
  const setLine = (i: number, p: Partial<ProductionLine>) => { setLines(lines.map((l, k) => (k === i ? { ...l, ...p } : l))); setDirty(true) }
  const setMember = (i: number, p: Partial<ProductionMember>) => { setMembers(members.map((m, k) => (k === i ? { ...m, ...p } : m))); setDirty(true) }
  const individual = kind !== 'brigade'
  return (
    <Card title={<Space wrap>{t('prod.rep.title')}<b>{doc.number}</b><Tag color={STATUS_COLOR[doc.status]}>{t(`prod.rep.status.${doc.status}`, { defaultValue: doc.status_label })}</Tag></Space>}
      extra={<Space wrap>
        {draft && <Button icon={<SaveOutlined />} onClick={() => save()}>{t('common.save')}</Button>}
        {draft && hasPerm('production.approve') && <Popconfirm title={t('prod.rep.approveConfirm')} onConfirm={() => act('approve')}>
          <Button type="primary" icon={<CheckOutlined />} loading={busy}>{t('prod.rep.approve')}</Button></Popconfirm>}
        {doc.status === 'approved' && hasPerm('production.approve') && <Popconfirm title={t('prod.rep.unapproveConfirm')} onConfirm={() => act('unapprove')}>
          <Button icon={<RollbackOutlined />} loading={busy}>{t('prod.rep.unapprove')}</Button></Popconfirm>}
        {draft && <ExcelImport code="lines" url={`/production/reports/${doc.id}/import/`} label={t('prod.rep.importLines')} onDone={reload}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>{t('prod.rep.importLinesHint')}</Typography.Paragraph>
        </ExcelImport>}
        {draft && !individual && <ExcelImport code="members" url={`/production/reports/${doc.id}/import/`} label={t('prod.rep.importMembers')} onDone={reload}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>{t('prod.rep.importMembersHint')}</Typography.Paragraph>
        </ExcelImport>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrint(true)}>{t('lv.print')}</Button>
        {doc.status === 'draft' && hasPerm('production.delete') && <MarkButton endpoint="/production/reports/" row={doc} onDone={reload} text />}
        <CloseForm to="/production/reports" />
      </Space>}>
      <MarkedBanner endpoint="/production/reports/" row={doc} onDone={reload} canUnmark={hasPerm('production.delete')} />
      {doc.status === 'approved' && <Alert type="success" showIcon style={{ marginBottom: 12 }} title={t('prod.rep.approvedHint')} />}
      {doc.status === 'draft' && problems.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('prod.rep.problems')}
        description={<ul style={{ margin: 0, paddingLeft: 18 }}>{problems.map((p) => <li key={p}>{p}</li>)}</ul>} />}
      <Form form={header} layout="vertical" disabled={!draft} onValuesChange={() => setDirty(true)}>
        <Row gutter={16}>
          <Col xs={24} md={4}><Form.Item name="date" label={t('ord.date')} rules={[{ required: true }]} extra={t('prod.rep.dateHint')}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={7}><Form.Item name="kind" label={t('prod.rep.kind')}>
            <Segmented block options={['individual', 'brigade'].map((k) => ({ value: k, label: t(`prod.rep.kinds.${k}`) }))} /></Form.Item></Col>
          {!individual && <Col xs={24} md={5}><Form.Item name="brigade" label={t('prod.rep.brigade')} rules={[{ required: true }]}>
            <Select options={(brigades ?? []).map((b) => ({ value: b.id, label: `${b.code} — ${b.name}` }))} /></Form.Item></Col>}
          <Col xs={24} md={4}><Form.Item name="subdivision" label={t('prod.op.subdivision')}><SubdivisionSelect /></Form.Item></Col>
          <Col xs={24} md={individual ? 9 : 4}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="shortfall_cause" label={t('prod.rep.shortfall')} extra={t('prod.rep.shortfallHint')}>
            <Select options={['', 'employer', 'nobody'].map((k) => ({ value: k, label: t(`prod.rep.shortfalls.${k || 'none'}`) }))} />
          </Form.Item></Col>
        </Row>
      </Form>
      <Typography.Title level={5}>{t('prod.rep.lines')}</Typography.Title>
      <Space orientation="vertical" style={{ width: '100%' }} size={6}>
        {lines.map((l, i) => <LineRow key={l.id ?? `n${i}`} line={l} set={(p) => setLine(i, p)} operations={operations} individual={individual}
          disabled={!draft} onRemove={() => { setLines(lines.filter((_x, k) => k !== i)); setDirty(true) }} />)}
        {draft && <Button icon={<PlusOutlined />} onClick={() => {
          const last = lines[lines.length - 1]
          setLines([...lines, { ...blankLine(), ...(individual && last ? { employee: last.employee, employee_name: last.employee_name, employment: last.employment } : {}) }])
          setDirty(true)
        }}>{t('prod.rep.addLine')}</Button>}
        <Typography.Text type="secondary">{t(individual ? 'prod.rep.linesHint' : 'prod.rep.brigadeLinesHint')}</Typography.Text>
      </Space>
      {!individual && <>
        <Typography.Title level={5} style={{ marginTop: 16 }}>{t('prod.rep.members')}</Typography.Title>
        <Space orientation="vertical" style={{ width: '100%' }} size={6}>
          {members.map((m, i) => <MemberRow key={m.id ?? `m${i}`} m={m} set={(p) => setMember(i, p)} disabled={!draft}
            onRemove={() => { setMembers(members.filter((_x, k) => k !== i)); setDirty(true) }} />)}
          {draft && <Space wrap>
            <Button icon={<PlusOutlined />} onClick={() => { setMembers([...members, { employment: null, hours: 0, coefficient: 1 }]); setDirty(true) }}>{t('prod.rep.addMember')}</Button>
            <Button icon={<TeamOutlined />} loading={busy} disabled={!doc.brigade} onClick={() => act('fill-members')}>{t('prod.rep.fillMembers')}</Button>
          </Space>}
          <Typography.Text type="secondary">{t('prod.rep.membersHint')}</Typography.Text>
        </Space>
      </>}
      <Space style={{ marginTop: 16 }} size={24} wrap>
        <span>{t('prod.rep.amount')}: <b>{money(doc.totals.amount) || '0'} lei</b></span>
        <span>{t('prod.rep.normed')}: <b>{num(doc.totals.normed_hours, 2)}</b></span>
        <span>{t('prod.rep.hours')}: <b>{num(doc.totals.hours, 2)}</b></span>
        {dirty && <Typography.Text type="warning">{t('prod.rep.unsavedTotals')}</Typography.Text>}
      </Space>
      {print && <PrintDialog open onClose={() => setPrint(false)} docType="production_report" url={`/production/reports/${doc.id}/print/`}
        params={{}} optionKeys={[]} title={`${t('prod.rep.title')} ${doc.number}`} />}
    </Card>
  )
}

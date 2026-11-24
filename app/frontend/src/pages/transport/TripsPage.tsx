import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, Checkbox, Col, DatePicker, Form, Input, InputNumber, Popconfirm, Row, Select, Space, Spin, Tag, Typography, message,
} from 'antd'
import { CheckOutlined, DeleteOutlined, FieldTimeOutlined, PlusOutlined, PrinterOutlined, RollbackOutlined, SaveOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import CloseForm from '../../components/CloseForm'
import ExcelImport from '../../components/ExcelImport'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import PrintDialog from '../../components/PrintDialog'
import { ROW_TONE } from '../../components/rowTone'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'
import { useTabTitle } from '../../layout/tabs'
import { SCOPES, TRIP_KINDS, blankLeg, hm, type Country, type Trip, type TripDiem, type TripLeg, type TripTacho, type Vehicle } from '../../api/transport'

const STATUS_COLOR: Record<string, string> = { draft: 'gold', approved: 'green' }
const DT = 'DD.MM.YYYY HH:mm'
const money = (v: number | string) => Number(v).toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const num = (v: number | string, digits = 2) => Number(v).toLocaleString('ro-RO', { maximumFractionDigits: digits })

/** Cursele (foile de parcurs): lista lunii întoarcerii, cursa nouă, importul din Excel. */
export default function TripsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [month, setMonth] = useState<Dayjs>(dayjs().startOf('month'))
  const [status, setStatus] = useState<string | undefined>()
  const { data, loading, reload } = useFetch<Paged<Trip>>('/transport/trips/',
    { year: month.year(), month: month.month() + 1, status, page_size: 500 })
  const rows = data?.results ?? []
  const approved = rows.filter((r) => r.status === 'approved')
  return (
    <Card title={t('menu.trips')} extra={<Space wrap>
      <DatePicker picker="month" format="MM.YYYY" value={month} allowClear={false} onChange={(v) => v && setMonth(v.startOf('month'))} />
      <Select allowClear style={{ width: 140 }} placeholder={t('ord.status')} value={status} onChange={setStatus}
        options={['draft', 'approved'].map((s) => ({ value: s, label: t(`tr.status.${s}`) }))} />
    </Space>}>
      <Space style={{ marginBottom: 12 }} wrap>
        {hasPerm('transport.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/transport/trips/new')}>{t('tr.trip.new')}</Button>}
        {hasPerm('transport.create') && <ExcelImport code="import" url="/transport/trips/" label={t('tr.trip.import')} onDone={reload}>
          <Typography.Paragraph type="secondary">{t('tr.trip.importHint')}</Typography.Paragraph></ExcelImport>}
        <Typography.Text type="secondary">{t('tr.trip.hint')}</Typography.Text>
      </Space>
      <Table<Trip> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} exportName={t('menu.trips')}
        rowTone={(r) => ROW_TONE.payItemChange(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/transport/trips/${r.id}`) })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 120, render: (v: string, r) => <a onClick={() => navigate(`/transport/trips/${r.id}`)}>{v}</a> },
          { title: t('tr.trip.departure'), dataIndex: 'departure', width: 140, render: (v: string) => dayjs(v).format(DT) },
          { title: t('tr.trip.arrival'), dataIndex: 'arrival', width: 140, render: (v: string) => dayjs(v).format(DT) },
          { title: t('ord.status'), dataIndex: 'status', width: 100, render: (v: string) => <Tag color={STATUS_COLOR[v]}>{t(`tr.status.${v}`)}</Tag> },
          { title: t('tr.trip.driver'), dataIndex: 'driver_label' },
          { title: t('tr.trip.vehicle'), dataIndex: 'vehicle_plate', width: 110 },
          { title: t('tr.trip.scope'), dataIndex: 'scope', width: 120, render: (v: string) => t(`tr.scopes.${v}`) },
          { title: t('tr.trip.countries'), key: 'c', width: 140, render: (_: unknown, r) => r.legs.map((l) => l.country_code).join(' → ') },
          { title: t('tr.trip.km'), dataIndex: 'km', width: 90, align: 'right', render: (v: string) => num(v, 1) },
          { title: t('tr.trip.kmAmount'), key: 'ka', width: 110, align: 'right', render: (_: unknown, r) => money(r.totals.km_amount) },
          { title: t('tr.trip.perDiem'), key: 'pd', width: 110, align: 'right', render: (_: unknown, r) => money(r.totals.per_diem) },
        ]}
        summary={() => approved.length ? (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={9} align="right">{t('tr.trip.approvedTotal')}</Table.Summary.Cell>
            <Table.Summary.Cell index={9} align="right"><b>{money(approved.reduce((s, r) => s + r.totals.km_amount, 0))}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={10} align="right"><b>{money(approved.reduce((s, r) => s + r.totals.per_diem, 0))}</b></Table.Summary.Cell>
          </Table.Summary.Row>) : null} />
    </Card>
  )
}

function LegRow({ leg, countries, set, onRemove, disabled }: {
  leg: TripLeg
  countries: Country[]
  set: (patch: Partial<TripLeg>) => void
  onRemove: () => void
  disabled: boolean
}) {
  const { t } = useTranslation()
  return (
    <Space wrap size={4} style={{ padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6, width: '100%' }}>
      <Select showSearch optionFilterProp="label" style={{ width: 200 }} placeholder={t('tr.leg.country')} disabled={disabled}
        value={leg.country ?? undefined} onChange={(v) => set({ country: v })}
        options={countries.filter((c) => c.code !== 'MD').map((c) => ({ value: c.id, label: `${c.code} — ${c.name_ro}` }))} />
      <DatePicker showTime={{ format: 'HH:mm' }} format={DT} placeholder={t('tr.leg.entered')} disabled={disabled} style={{ width: 170 }}
        value={leg.entered ? dayjs(leg.entered) : null} onChange={(v) => set({ entered: v ? v.toISOString() : null })} />
      <DatePicker showTime={{ format: 'HH:mm' }} format={DT} placeholder={t('tr.leg.left')} disabled={disabled} style={{ width: 170 }}
        value={leg.left ? dayjs(leg.left) : null} onChange={(v) => set({ left: v ? v.toISOString() : null })} />
      <Checkbox disabled={disabled} checked={leg.loading} onChange={(e) => set({ loading: e.target.checked })}>{t('tr.leg.loading')}</Checkbox>
      <Checkbox disabled={disabled} checked={leg.unloading} onChange={(e) => set({ unloading: e.target.checked })}>{t('tr.leg.unloading')}</Checkbox>
      <Checkbox disabled={disabled} checked={leg.meals} onChange={(e) => set({ meals: e.target.checked })}>{t('tr.leg.meals')}</Checkbox>
      <InputNumber min={0} placeholder={t('tr.leg.km')} disabled={disabled} style={{ width: 100 }} value={leg.km === null ? null : Number(leg.km)}
        onChange={(v) => set({ km: v ?? null })} />
      {!disabled && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={onRemove} />}
    </Space>
  )
}

/** Tahograful în timpul cursei: timpii fiecărui șofer de pe card, acoperirea cu descărcări, încălcările. */
function TripTachoPanel({ trip }: { trip: Trip }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data } = useFetch<TripTacho>(`/transport/trips/${trip.id}/tacho/`, { v: trip.departure + trip.arrival })
  if (!data || (!data.any_files && !data.people.some((p) => p.has_data))) return null
  return (
    <>
      <Typography.Title level={5} style={{ marginTop: 16 }}>{t('tr.tacho.inTrip')}</Typography.Title>
      {data.people.map((p) => (
        <div key={p.employee} style={{ marginBottom: 8 }}>
          <Space wrap>
            <b>{p.name}</b>
            {!p.has_data ? <Tag color="red">{t('tr.tacho.noFiles')}</Tag> : !p.covered && <Tag color="gold">{t('tr.tacho.partial')}</Tag>}
            {p.has_data && (['driving', 'work', 'availability', 'rest'] as const).map((k) => (
              <span key={k}>{t(`tr.tacho.sum.${k}`)}: <b>{hm(p.totals[k])}</b></span>))}
            {p.has_data && <a onClick={() => navigate(`/transport/tachograph?tab=days&employee=${p.employee}&month=${dayjs(trip.departure).format('YYYY-MM')}`)}>
              {t('tr.tacho.openDays')}</a>}
          </Space>
          {p.findings.length > 0 && <ul style={{ margin: '4px 0 0', paddingInlineStart: 18 }}>
            {p.findings.map((f, i) => <li key={i}><Tag color={f.level === 'error' ? 'red' : 'gold'}>{dayjs(f.start).format(DT)}</Tag>
              <b>{f.title}</b>: {f.text}</li>)}</ul>}
        </div>))}
    </>
  )
}

/** Cursa: șoferii, vehiculul, felul și aria, plecarea / întoarcerea, km, segmentele pe țări; la salvare se socotesc plata pe km și
 *  diurna pe zile; aprobarea le fixează și cursa intră în salariul lunii întoarcerii. */
export function TripEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const isNew = id === 'new'
  const { data: loaded, reload } = useFetch<Trip>(isNew ? null : `/transport/trips/${id}/`)
  const doc = isNew ? null : loaded
  useTabTitle(doc ? { key: 'desk.tab.trip', params: { number: doc.number } } : null)
  const [header] = Form.useForm()
  const [legs, setLegs] = useState<TripLeg[]>([])
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [print, setPrint] = useState(false)
  const departure = Form.useWatch('departure', header) as Dayjs | undefined
  const { data: drivers } = useFetch<{ id: number; label: string }[]>('/transport/trips/drivers/',
    { date: (departure ?? dayjs()).format('YYYY-MM-DD') })
  const { data: vehicles } = useFetch<Vehicle[]>('/transport/vehicles/', { active: 1 })
  const { data: countries } = useFetch<Country[]>('/transport/countries/', { active: 1 })
  const draft = isNew ? hasPerm('transport.create') : (!!doc && doc.status === 'draft' && !doc.deletion_mark && hasPerm('transport.edit'))

  useEffect(() => {
    if (isNew) {
      header.setFieldsValue({ kind: 'goods', scope: 'international', departure: dayjs().hour(6).minute(0).second(0), adr: false, meals_provided: false })
      return
    }
    if (!doc) return
    header.setFieldsValue({ ...doc, departure: dayjs(doc.departure), arrival: dayjs(doc.arrival), km: doc.km ? Number(doc.km) : null,
      per_diem_pct: doc.per_diem_pct === null ? null : Number(doc.per_diem_pct) })
    setLegs(doc.legs)
    setDirty(false)
  }, [doc, isNew, header])

  const save = async (quiet = false) => {
    try {
      const h = await header.validateFields()
      const body = { ...h, departure: h.departure.toISOString(), arrival: h.arrival.toISOString(), co_driver: h.co_driver ?? null,
        trailer: h.trailer ?? null, km: h.km ?? 0, per_diem_pct: h.per_diem_pct ?? null, odometer_out: h.odometer_out ?? null,
        odometer_in: h.odometer_in ?? null, route: h.route ?? '', note: h.note ?? '',
        legs: legs.map((l) => ({ id: l.id, country: l.country, entered: l.entered, left: l.left, loading: l.loading, unloading: l.unloading,
          meals: l.meals, km: l.km === '' ? null : l.km, note: l.note ?? '' })) }
      if (isNew) {
        const r = await api.post<Trip>('/transport/trips/', body)
        setDirty(false)
        navigate(`/transport/trips/${r.data.id}`, { replace: true })
        return true
      }
      await api.patch(`/transport/trips/${id}/`, body)
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
      await api.post(`/transport/trips/${id}/${what}/`)
      message.success(t(`tr.trip.done.${what}`))
      reload()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const fromTacho = async () => {
    try {
      if (dirty && !(await save(true))) return
      const r = await api.get<{ legs: TripLeg[] }>(`/transport/trips/${id}/tacho-legs/`)
      setLegs(r.data.legs)
      setDirty(true)
      message.success(t('tr.tacho.legsDone', { n: r.data.legs.length }))
    } catch (e) {
      message.error(errorText(e))
    }
  }

  if (!isNew && !doc) return <Spin />
  const tractors = (vehicles ?? []).filter((v) => v.kind !== 'trailer')
  const trailers = (vehicles ?? []).filter((v) => v.kind === 'trailer')
  const setLeg = (i: number, patch: Partial<TripLeg>) => { setLegs(legs.map((l, k) => (k === i ? { ...l, ...patch } : l))); setDirty(true) }
  const status = doc?.status ?? 'draft'
  return (
    <Card title={<Space wrap>{t('tr.trip.title')}{doc && <b>{doc.number}</b>}<Tag color={STATUS_COLOR[status]}>{t(`tr.status.${status}`)}</Tag></Space>}
      extra={<Space wrap>
        {draft && <Button icon={<SaveOutlined />} onClick={() => save()}>{t('common.save')}</Button>}
        {doc && draft && hasPerm('transport.approve') && <Popconfirm title={t('tr.trip.approveConfirm')} onConfirm={() => act('approve')}>
          <Button type="primary" icon={<CheckOutlined />} loading={busy}>{t('tr.trip.approve')}</Button></Popconfirm>}
        {doc?.status === 'approved' && hasPerm('transport.approve') && <Popconfirm title={t('tr.trip.unapproveConfirm')} onConfirm={() => act('unapprove')}>
          <Button icon={<RollbackOutlined />} loading={busy}>{t('tr.trip.unapprove')}</Button></Popconfirm>}
        {doc && <Button icon={<PrinterOutlined />} onClick={() => setPrint(true)}>{t('lv.print')}</Button>}
        {doc?.status === 'draft' && hasPerm('transport.delete') && <MarkButton endpoint="/transport/trips/" row={doc} onDone={reload} text />}
        <CloseForm to="/transport/trips" />
      </Space>}>
      {doc && <MarkedBanner endpoint="/transport/trips/" row={doc} onDone={reload} canUnmark={hasPerm('transport.delete')} />}
      {doc?.status === 'approved' && <Alert type="success" showIcon style={{ marginBottom: 12 }} title={t('tr.trip.approvedHint')} />}
      {doc && doc.status === 'draft' && doc.problems.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('tr.trip.problems')}
        description={<ul style={{ margin: 0, paddingInlineStart: 18 }}>{doc.problems.map((p) => <li key={p}>{p}</li>)}</ul>} />}
      {doc && doc.warnings.length > 0 && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('tr.trip.warnings')}
        description={<ul style={{ margin: 0, paddingInlineStart: 18 }}>{doc.warnings.map((p) => <li key={p}>{p}</li>)}</ul>} />}
      <Form form={header} layout="vertical" disabled={!draft} onValuesChange={() => setDirty(true)}>
        <Row gutter={16}>
          <Col xs={24} md={8}><Form.Item name="driver" label={t('tr.trip.driver')} rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={(drivers ?? []).map((d) => ({ value: d.id, label: d.label }))} /></Form.Item></Col>
          <Col xs={24} md={8}><Form.Item name="co_driver" label={t('tr.trip.coDriver')}>
            <Select allowClear showSearch optionFilterProp="label" options={(drivers ?? []).map((d) => ({ value: d.id, label: d.label }))} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="vehicle" label={t('tr.trip.vehicle')} rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={tractors.map((v) => ({ value: v.id, label: `${v.plate} ${v.brand}`.trim() }))} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="trailer" label={t('tr.trip.trailer')}>
            <Select allowClear showSearch optionFilterProp="label" options={trailers.map((v) => ({ value: v.id, label: v.plate }))} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="kind" label={t('tr.trip.kind')}>
            <Select options={TRIP_KINDS.map((k) => ({ value: k, label: t(`tr.kinds.${k}`) }))} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="scope" label={t('tr.trip.scope')}>
            <Select options={SCOPES.map((k) => ({ value: k, label: t(`tr.scopes.${k}`) }))} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="departure" label={t('tr.trip.departure')} rules={[{ required: true }]}>
            <DatePicker showTime={{ format: 'HH:mm' }} format={DT} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="arrival" label={t('tr.trip.arrival')} rules={[{ required: true }]} extra={t('tr.trip.arrivalHint')}>
            <DatePicker showTime={{ format: 'HH:mm' }} format={DT} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="odometer_out" label={t('tr.trip.odometerOut')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="odometer_in" label={t('tr.trip.odometerIn')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="km" label={t('tr.trip.km')} extra={t('tr.trip.kmHint')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={4}><Form.Item name="per_diem_pct" label={t('tr.trip.perDiemPct')} extra={t('tr.trip.perDiemPctHint')}>
            <InputNumber min={0} max={300} suffix="%" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={12}><Form.Item name="route" label={t('tr.trip.route')}><Input /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="adr" valuePropName="checked" label=" "><Checkbox>{t('tr.trip.adr')}</Checkbox></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="meals_provided" valuePropName="checked" label=" " extra={t('tr.trip.mealsHint')}>
            <Checkbox>{t('tr.trip.meals')}</Checkbox></Form.Item></Col>
          <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row>
      </Form>
      <Typography.Title level={5}>{t('tr.leg.title')}</Typography.Title>
      <Typography.Paragraph type="secondary">{t('tr.leg.hint')}</Typography.Paragraph>
      <Space orientation="vertical" style={{ width: '100%' }} size={6}>
        {legs.map((l, i) => <LegRow key={l.id ?? `n${i}`} leg={l} countries={countries ?? []} disabled={!draft} set={(p) => setLeg(i, p)}
          onRemove={() => { setLegs(legs.filter((_x, k) => k !== i)); setDirty(true) }} />)}
        {draft && <Space wrap>
          <Button icon={<PlusOutlined />} onClick={() => {
            const prev = legs[legs.length - 1]
            setLegs([...legs, { ...blankLeg(), entered: prev?.left ?? null }])
            setDirty(true)
          }}>{t('tr.leg.add')}</Button>
          {doc && <Popconfirm title={t('tr.tacho.legsConfirm')} onConfirm={fromTacho}>
            <Button icon={<FieldTimeOutlined />}>{t('tr.tacho.legs')}</Button></Popconfirm>}
        </Space>}
      </Space>
      {doc && <>
        <Typography.Title level={5} style={{ marginTop: 16 }}>{t('tr.trip.pay')}</Typography.Title>
        <Typography.Paragraph>{doc.how || '—'}</Typography.Paragraph>
        <Table<TripDiem> rowKey="id" size="small" dataSource={doc.diems} pagination={false} exportName={`${t('tr.trip.title')} ${doc.number}`}
          locale={{ emptyText: t('tr.diem.none') }}
          columns={[
            { title: t('tr.diem.person'), dataIndex: 'employee_name', width: 200 },
            { title: t('tr.diem.day'), dataIndex: 'day', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
            { title: t('tr.diem.country'), dataIndex: 'country_code', width: 70, render: (v: string) => v || 'MD' },
            { title: t('tr.diem.hours'), dataIndex: 'hours', width: 70, align: 'right', render: (v: string) => num(v) },
            { title: '%', dataIndex: 'pct', width: 70, align: 'right', render: (v: string) => num(v) },
            { title: t('tr.diem.norm'), key: 'n', width: 110, align: 'right', render: (_: unknown, r) => `${num(r.norm)} ${r.currency}` },
            { title: t('tr.diem.fx'), dataIndex: 'fx_rate', width: 90, align: 'right', render: (v: string, r) => (r.currency === 'MDL' ? '' : num(v, 4)) },
            { title: t('tr.diem.amount'), dataIndex: 'amount', width: 110, align: 'right', render: money },
            { title: t('tr.diem.taxable'), dataIndex: 'taxable', width: 110, align: 'right', render: (v: string) => (Number(v) ? money(v) : '') },
            { title: t('tr.diem.how'), dataIndex: 'how', render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
          ]}
          summary={() => doc.diems.length ? (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={7} align="right"><b>{t('tr.diem.total')}</b></Table.Summary.Cell>
              <Table.Summary.Cell index={7} align="right"><b>{money(doc.totals.per_diem)}</b></Table.Summary.Cell>
              <Table.Summary.Cell index={8} align="right"><b>{doc.totals.per_diem_taxable ? money(doc.totals.per_diem_taxable) : ''}</b></Table.Summary.Cell>
              <Table.Summary.Cell index={9} />
            </Table.Summary.Row>) : null} />
      </>}
      {doc && <TripTachoPanel trip={doc} />}
      {print && doc && <PrintDialog open onClose={() => setPrint(false)} docType="trip_sheet" url={`/transport/trips/${doc.id}/print/`}
        params={{}} optionKeys={[]} title={`${t('tr.trip.title')} ${doc.number}`} />}
    </Card>
  )
}

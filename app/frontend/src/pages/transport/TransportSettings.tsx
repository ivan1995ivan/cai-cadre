import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, InputNumber, Modal, Select, Space, Tag, Typography, message } from 'antd'
import { DeleteOutlined, PlusOutlined, ProfileOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import CrudTable, { type CrudField } from '../../components/CrudTable'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'
import {
  INCIDENT_KINDS, KPI_SOURCES, SCOPES, TRIP_KINDS, VEHICLE_KINDS, type Country, type KpiIndicator, type KpiScheme, type KpiSchemeItem,
} from '../../api/transport'

const num = (v: unknown, digits = 4) => (v === null || v === undefined || v === '' ? ''
  : Number(v).toLocaleString('ro-RO', { maximumFractionDigits: digits }))

/** Normele diurnei unei țări, cu istoric (din data dată). */
function NormsDialog({ country, onClose }: { country: Country; onClose: () => void }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const fields: CrudField[] = [
    { key: 'date_from', label: t('tr.country.dateFrom'), type: 'date', required: true, width: 120 },
    { key: 'amount', label: t('tr.country.amount'), type: 'number', required: true, width: 120 },
    { key: 'currency', label: t('tr.country.currency'), required: true, width: 90 },
    { key: 'document', label: t('tr.country.document') },
  ]
  return (
    <Modal open onCancel={onClose} footer={null} width={820} title={`${t('tr.country.norms')}: ${country.code} — ${country.name_ro}`}>
      <CrudTable endpoint="/transport/per-diem-norms/" params={{ country: country.id }} fields={fields} canEdit={hasPerm('transport.edit')}
        defaults={{ country: country.id, currency: 'EUR', date_from: dayjs().startOf('year').format('YYYY-MM-DD') }}
        title={<Typography.Text type="secondary">{t('tr.country.normsHint')}</Typography.Text>} />
    </Modal>
  )
}

/** Schema KPI: indicatorii cu ponderile (și alte valori de notare decât ale indicatorului), cui se aplică. */
function SchemeDialog({ scheme, onClose }: { scheme: KpiScheme; onClose: () => void }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('transport.edit')
  const { data: indicators } = useFetch<KpiIndicator[]>('/transport/kpi-indicators/')
  const { data: drivers } = useFetch<{ id: number; label: string }[]>('/transport/trips/drivers/')
  const [items, setItems] = useState<KpiSchemeItem[]>(scheme.items)
  const [dirty, setDirty] = useState(false)
  useEffect(() => setItems(scheme.items), [scheme])
  const set = (i: number, patch: Partial<KpiSchemeItem>) => { setItems(items.map((x, k) => (k === i ? { ...x, ...patch } : x))); setDirty(true) }
  const byId = Object.fromEntries((indicators ?? []).map((x) => [x.id, x]))
  const total = items.reduce((s, x) => s + Number(x.weight || 0), 0)
  const save = async () => {
    try {
      await api.patch(`/transport/kpi-schemes/${scheme.id}/`, { items: items.map((x) => ({ indicator: x.indicator, weight: x.weight,
        mode: x.mode || '', full_at: x.full_at === '' ? null : x.full_at, zero_at: x.zero_at === '' ? null : x.zero_at })) })
      setDirty(false)
      message.success(t('common.saved'))
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const assignFields: CrudField[] = [
    { key: 'occupation', label: t('tr.kpiScheme.occupation'), ref: 'occupation', render: (_v, r) => String(r.occupation_name || '') },
    { key: 'employment', label: t('tr.kpiScheme.employment'), type: 'select', extra: t('tr.kpiScheme.employmentHint'),
      options: (drivers ?? []).map((d) => ({ value: d.id, label: d.label })), render: (_v, r) => String(r.employment_label || '') },
    { key: 'date_from', label: t('tr.kpiScheme.from'), type: 'date', required: true, width: 110 },
    { key: 'date_to', label: t('tr.kpiScheme.to'), type: 'date', width: 110 },
  ]
  return (
    <Modal open onCancel={onClose} footer={null} width={980} title={`${t('tr.kpiScheme.items')}: ${scheme.code} — ${scheme.name}`}>
      <Typography.Paragraph type="secondary">{t('tr.kpiScheme.itemsHint')}</Typography.Paragraph>
      <Table<KpiSchemeItem> rowKey={(r) => String(r.indicator)} size="small" dataSource={items} pagination={false}
        columns={[
          { title: t('tr.kpiInd.indicator'), dataIndex: 'indicator', render: (v: number, _r, i) => (
            <Select disabled={!canEdit} style={{ width: 280 }} value={v} onChange={(x) => set(i, { indicator: x })}
              options={(indicators ?? []).filter((x) => x.is_active || x.id === v).map((x) => ({ value: x.id, label: `${x.code} — ${x.name_ro}` }))} />) },
          { title: t('kpi.weight'), dataIndex: 'weight', width: 100, render: (v: string, _r, i) => (
            <InputNumber disabled={!canEdit} min={0.01} value={Number(v)} onChange={(x) => set(i, { weight: x ?? 0 })} style={{ width: 80 }} />) },
          { title: t('tr.kpiInd.mode'), dataIndex: 'mode', width: 200, render: (v: KpiSchemeItem['mode'], r, i) => (
            <Select<KpiSchemeItem['mode']> disabled={!canEdit} style={{ width: 190 }} value={v} onChange={(x) => set(i, { mode: x })}
              options={[{ value: '', label: `${t('tr.kpiScheme.asIndicator')}${byId[r.indicator] ? ` (${t(`tr.kpiInd.modes.${byId[r.indicator].mode}`)})` : ''}` },
                { value: 'linear', label: t('tr.kpiInd.modes.linear') }, { value: 'step', label: t('tr.kpiInd.modes.step') }]} />) },
          { title: t('kpi.full'), dataIndex: 'full_at', width: 120, render: (v: string | null, r, i) => (
            <InputNumber disabled={!canEdit} value={v === null ? null : Number(v)} placeholder={byId[r.indicator]?.full_at}
              onChange={(x) => set(i, { full_at: x })} style={{ width: 100 }} />) },
          { title: t('kpi.zero'), dataIndex: 'zero_at', width: 120, render: (v: string | null, r, i) => (
            <InputNumber disabled={!canEdit} value={v === null ? null : Number(v)} placeholder={byId[r.indicator]?.zero_at}
              onChange={(x) => set(i, { zero_at: x })} style={{ width: 100 }} />) },
          { title: '', key: 'x', width: 50, render: (_: unknown, _r, i) => canEdit && (
            <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => { setItems(items.filter((_x, k) => k !== i)); setDirty(true) }} />) },
        ]} />
      <Space style={{ margin: '8px 0 16px' }} wrap>
        {canEdit && <Button icon={<PlusOutlined />} onClick={() => {
          const free = (indicators ?? []).find((x) => x.is_active && !items.some((y) => y.indicator === x.id))
          if (free) { setItems([...items, { indicator: free.id, weight: 10, mode: '', full_at: null, zero_at: null }]); setDirty(true) }
        }}>{t('tr.kpiScheme.addItem')}</Button>}
        {canEdit && <Button type="primary" disabled={!dirty} onClick={save}>{t('common.save')}</Button>}
        <Typography.Text type="secondary">{t('tr.kpiScheme.totalWeight', { n: total.toLocaleString('ro-RO') })}</Typography.Text>
      </Space>
      <Typography.Title level={5}>{t('tr.kpiScheme.assignments')}</Typography.Title>
      <CrudTable endpoint="/transport/kpi-assignments/" params={{ scheme: scheme.id }} fields={assignFields} canEdit={canEdit}
        defaults={{ scheme: scheme.id, date_from: dayjs().startOf('month').format('YYYY-MM-DD') }}
        title={<Typography.Text type="secondary">{t('tr.kpiScheme.assignmentsHint')}</Typography.Text>} />
    </Modal>
  )
}

export type TransportPart = 'vehicles' | 'kmRates' | 'countries' | 'kpiIndicators' | 'kpiSchemes'

/** Setările transportului (Administrare → Setări): vehiculele, tarifele pe km, țările cu normele diurnei. */
export default function TransportSettingsPage({ part, title }: { part: TransportPart; title: string }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('transport.edit')
  const [norms, setNorms] = useState<Country | null>(null)
  const [scheme, setScheme] = useState<KpiScheme | null>(null)
  const [tick, setTick] = useState(0)
  const any = { value: '', label: t('tr.any') }

  const vehicleFields: CrudField[] = [
    { key: 'plate', label: t('tr.veh.plate'), required: true, width: 130 },
    { key: 'kind', label: t('tr.veh.kind'), type: 'select', required: true, width: 170,
      options: VEHICLE_KINDS.map((k) => ({ value: k, label: t(`tr.vehicleKinds.${k}`) })), render: (v) => t(`tr.vehicleKinds.${v}`) },
    { key: 'brand', label: t('tr.veh.brand'), width: 130 },
    { key: 'model', label: t('tr.veh.model'), width: 130 },
    { key: 'category', label: t('tr.veh.category'), width: 90 },
    { key: 'tachograph', label: t('tr.veh.tachograph'), type: 'bool', width: 90 },
    { key: 'fuel_norm', label: t('tr.veh.fuelNorm'), type: 'number', width: 110 },
    { key: 'gps_id', label: t('tr.veh.gpsId'), width: 130, extra: t('tr.veh.gpsIdHint') },
    { key: 'subdivision', label: t('tr.veh.subdivision'), input: () => <SubdivisionSelect />, render: (_v, r) => String(r.subdivision_name ?? '') },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
    { key: 'note', label: t('org.notes'), inTable: false },
  ]
  const rateFields: CrudField[] = [
    { key: 'date_from', label: t('tr.rate.dateFrom'), type: 'date', required: true, width: 120 },
    { key: 'trip_kind', label: t('tr.trip.kind'), type: 'select', width: 190,
      options: [any, ...TRIP_KINDS.map((k) => ({ value: k, label: t(`tr.kinds.${k}`) }))], render: (v) => (v ? t(`tr.kinds.${v}`) : t('tr.any')) },
    { key: 'scope', label: t('tr.trip.scope'), type: 'select', width: 150,
      options: [any, ...SCOPES.map((k) => ({ value: k, label: t(`tr.scopes.${k}`) }))], render: (v) => (v ? t(`tr.scopes.${v}`) : t('tr.any')) },
    { key: 'vehicle_kind', label: t('tr.veh.kind'), type: 'select', width: 170,
      options: [any, ...VEHICLE_KINDS.filter((k) => k !== 'trailer').map((k) => ({ value: k, label: t(`tr.vehicleKinds.${k}`) }))],
      render: (v) => (v ? t(`tr.vehicleKinds.${v}`) : t('tr.any')) },
    { key: 'rate', label: t('tr.rate.rate'), type: 'number', required: true, width: 120, render: (v) => num(v) },
    { key: 'document', label: t('tr.rate.document') },
  ]
  const countryFields: CrudField[] = [
    { key: 'code', label: t('tr.country.code'), required: true, width: 80 },
    { key: 'name_ro', label: t('org.nameRo'), required: true },
    { key: 'name_ru', label: t('org.nameRu'), inTable: false },
    { key: 'name_en', label: t('org.nameEn'), inTable: false },
    { key: 'current', label: t('tr.country.current'), display: true, width: 170,
      render: (v) => {
        const c = v as Country['current']
        return c ? <b>{num(c.amount, 2)} {c.currency}</b> : <Typography.Text type="warning">{t('tr.country.noNorm')}</Typography.Text>
      } },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
    { key: 'sort', label: t('org.sort'), type: 'number', inTable: false },
  ]
  const indicatorFields: CrudField[] = [
    { key: 'code', label: t('tr.kpiInd.code'), required: true, width: 100 },
    { key: 'name_ro', label: t('org.nameRo'), required: true },
    { key: 'name_ru', label: t('org.nameRu'), inTable: false },
    { key: 'name_en', label: t('org.nameEn'), inTable: false },
    { key: 'source', label: t('tr.kpiInd.source'), type: 'select', required: true, width: 230,
      options: KPI_SOURCES.map((k) => ({ value: k, label: t(`tr.kpiInd.sources.${k}`) })), render: (v) => t(`tr.kpiInd.sources.${v}`) },
    { key: 'kinds', label: t('tr.kpiInd.kinds'), type: 'multiselect', inTable: false, extra: t('tr.kpiInd.kindsHint'),
      options: INCIDENT_KINDS.map((k) => ({ value: k, label: t(`tr.inc.kinds.${k}`) })) },
    { key: 'measure', label: t('tr.kpiInd.measure'), type: 'select', inTable: false,
      options: ['count', 'amount'].map((k) => ({ value: k, label: t(`tr.kpiInd.measures.${k}`) })) },
    { key: 'mode', label: t('tr.kpiInd.mode'), type: 'select', width: 150,
      options: ['linear', 'step'].map((k) => ({ value: k, label: t(`tr.kpiInd.modes.${k}`) })), render: (v) => t(`tr.kpiInd.modes.${v}`) },
    { key: 'full_at', label: t('kpi.full'), type: 'number', required: true, width: 100, render: (v) => num(v, 2), extra: t('tr.kpiInd.fullHint') },
    { key: 'zero_at', label: t('kpi.zero'), type: 'number', required: true, width: 100, render: (v) => num(v, 2) },
    { key: 'unit', label: t('tr.kpiInd.unit'), width: 70 },
    { key: 'description', label: t('tr.kpiInd.description'), type: 'textarea', inTable: false },
    { key: 'sort', label: t('org.sort'), type: 'number', inTable: false },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
  ]
  const schemeFields: CrudField[] = [
    { key: 'code', label: t('tr.kpiInd.code'), required: true, width: 100 },
    { key: 'name', label: t('tr.kpiScheme.name'), required: true },
    { key: 'base_kind', label: t('tr.kpiScheme.baseKind'), type: 'select', required: true, width: 190,
      options: ['fixed', 'pct'].map((k) => ({ value: k, label: t(`tr.kpiScheme.bases.${k}`) })),
      render: (v, r) => (v === 'pct' ? `${num(r.base_pct, 2)} % ${t('tr.kpiScheme.ofSalary')}` : `${num(r.base_amount, 2)} lei`) },
    { key: 'base_amount', label: t('tr.kpiScheme.baseAmount'), type: 'number', inTable: false, extra: t('tr.kpiScheme.baseHint') },
    { key: 'base_pct', label: t('tr.kpiScheme.basePct'), type: 'number', inTable: false },
    { key: 'min_score', label: t('tr.kpiScheme.minScore'), type: 'number', width: 110, render: (v) => `${num(v, 2)} %`, extra: t('tr.kpiScheme.minScoreHint') },
    { key: 'prorate', label: t('tr.kpiScheme.prorate'), type: 'bool', width: 110, extra: t('tr.kpiScheme.prorateHint') },
    { key: 'needs_trips', label: t('tr.kpiScheme.needsTrips'), type: 'bool', width: 110, extra: t('tr.kpiScheme.needsTripsHint') },
    { key: 'items', label: t('tr.kpiScheme.items'), display: true, width: 260,
      render: (v) => (v as KpiSchemeItem[]).map((x) => <Tag key={x.indicator}>{x.indicator_code} · {num(x.weight)}</Tag>) },
    { key: 'assignments', label: t('tr.kpiScheme.assignments'), display: true, width: 220,
      render: (v) => (v as KpiScheme['assignments']).map((a) => a.occupation_name || a.employment_label.split(' — ')[0]).join('; ') || '—' },
    { key: 'document', label: t('tr.rate.document'), inTable: false },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
  ]
  const parts: Record<TransportPart, React.ReactNode> = {
    vehicles: <CrudTable endpoint="/transport/vehicles/" fields={vehicleFields} canEdit={canEdit} search
      defaults={{ kind: 'truck', tachograph: true }}
      title={<Typography.Text type="secondary">{t('tr.veh.hint')}</Typography.Text>} />,
    kmRates: <CrudTable endpoint="/transport/km-rates/" fields={rateFields} canEdit={canEdit}
      defaults={{ trip_kind: '', scope: '', vehicle_kind: '', date_from: dayjs().startOf('month').format('YYYY-MM-DD') }}
      title={<Typography.Text type="secondary">{t('tr.rate.hint')}</Typography.Text>} />,
    countries: <CrudTable key={tick} endpoint="/transport/countries/" fields={countryFields} canEdit={canEdit} search
      defaults={{ sort: 100 }}
      rowActions={(row) => <Button size="small" icon={<ProfileOutlined />} onClick={() => setNorms(row as unknown as Country)}>{t('tr.country.norms')}</Button>}
      title={<Typography.Text type="secondary">{t('tr.country.hint')} <Tag>{t('tr.country.checkTag')}</Tag></Typography.Text>} />,
    kpiIndicators: <CrudTable endpoint="/transport/kpi-indicators/" fields={indicatorFields} canEdit={canEdit}
      defaults={{ source: 'incidents', kinds: [], measure: 'count', mode: 'linear', full_at: 0, zero_at: 2, sort: 100, is_active: true }}
      title={<Typography.Text type="secondary">{t('tr.kpiInd.hint')}</Typography.Text>} />,
    kpiSchemes: <CrudTable key={`s${tick}`} endpoint="/transport/kpi-schemes/" fields={schemeFields} canEdit={canEdit}
      defaults={{ base_kind: 'fixed', base_amount: 0, base_pct: 0, min_score: 0, prorate: true, needs_trips: true, is_active: true }}
      rowActions={(row) => <Button size="small" icon={<ProfileOutlined />} onClick={() => setScheme(row as unknown as KpiScheme)}>{t('tr.kpiScheme.open')}</Button>}
      title={<Typography.Text type="secondary">{t('tr.kpiScheme.hint')}</Typography.Text>} />,
  }
  return (
    <Card title={title}>
      {parts[part]}
      {norms && <NormsDialog country={norms} onClose={() => { setNorms(null); setTick((n) => n + 1) }} />}
      {scheme && <SchemeDialog scheme={scheme} onClose={() => { setScheme(null); setTick((n) => n + 1) }} />}
    </Card>
  )
}

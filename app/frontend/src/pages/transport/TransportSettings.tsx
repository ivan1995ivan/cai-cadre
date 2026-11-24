import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, Modal, Tag, Typography } from 'antd'
import { ProfileOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import { useApp } from '../../auth/AppContext'
import { SCOPES, TRIP_KINDS, VEHICLE_KINDS, type Country } from '../../api/transport'

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

export type TransportPart = 'vehicles' | 'kmRates' | 'countries'

/** Setările transportului (Administrare → Setări): vehiculele, tarifele pe km, țările cu normele diurnei. */
export default function TransportSettingsPage({ part, title }: { part: TransportPart; title: string }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('transport.edit')
  const [norms, setNorms] = useState<Country | null>(null)
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
  }
  return (
    <Card title={title}>
      {parts[part]}
      {norms && <NormsDialog country={norms} onClose={() => { setNorms(null); setTick((n) => n + 1) }} />}
    </Card>
  )
}

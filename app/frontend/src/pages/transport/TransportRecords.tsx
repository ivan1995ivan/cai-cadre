import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, DatePicker, Popconfirm, Select, Space, Tag, Typography, Button, message } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import CrudTable, { type CrudField } from '../../components/CrudTable'
import EmployeeSelect from '../../components/EmployeeSelect'
import ExcelImport from '../../components/ExcelImport'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'
import { INCIDENT_KINDS, hm, type GpsDay, type Trip, type Vehicle } from '../../api/transport'

const money = (v: unknown) => Number(v || 0).toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const num = (v: unknown, digits = 1) => (v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('ro-RO', { maximumFractionDigits: digits }))

/** Evenimentele șoferilor (daune, accidente, amenzi, reclamații): intră în indicatorii KPI care le numără. */
export function IncidentsPage() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const [month, setMonth] = useState<Dayjs>(dayjs().startOf('month'))
  const { data: trips } = useFetch<Paged<Trip>>('/transport/trips/', { year: month.year(), month: month.month() + 1, page_size: 500 })
  const fields: CrudField[] = [
    { key: 'date', label: t('tr.inc.date'), type: 'date', required: true, width: 110 },
    { key: 'employee', label: t('tr.inc.employee'), required: true, width: 220, input: () => <EmployeeSelect />,
      render: (_v, r) => String(r.employee_name ?? '') },
    { key: 'kind', label: t('tr.inc.kind'), type: 'select', required: true, width: 190,
      options: INCIDENT_KINDS.map((k) => ({ value: k, label: t(`tr.inc.kinds.${k}`) })), render: (v) => t(`tr.inc.kinds.${v}`) },
    { key: 'at_fault', label: t('tr.inc.atFault'), type: 'bool', width: 110, extra: t('tr.inc.atFaultHint') },
    { key: 'amount', label: t('tr.inc.amount'), type: 'number', width: 110, render: (v) => (Number(v) ? money(v) : '') },
    { key: 'trip', label: t('tr.inc.trip'), type: 'select', width: 150, extra: t('tr.inc.tripHint'),
      options: (trips?.results ?? []).map((x) => ({ value: x.id, label: `${x.number} — ${x.driver_label.split(' — ')[0]}` })),
      render: (_v, r) => String(r.trip_label ?? '') },
    { key: 'document', label: t('tr.inc.document') },
    { key: 'note', label: t('org.notes'), type: 'textarea', inTable: false },
  ]
  return (
    <Card title={t('menu.driverIncidents')} extra={<DatePicker picker="month" format="MM.YYYY" value={month} allowClear={false}
      onChange={(v) => v && setMonth(v.startOf('month'))} />}>
      <CrudTable endpoint="/transport/incidents/" params={{ month: month.format('YYYY-MM') }} fields={fields} canEdit={hasPerm('transport.edit')}
        defaults={{ date: month.format('YYYY-MM-DD'), at_fault: true, kind: 'damage_cargo', amount: 0 }}
        title={<Typography.Text type="secondary">{t('tr.inc.hint')}</Typography.Text>} />
    </Card>
  )
}

/** Zilele vehiculelor din GPS: importul raportului zilnic (Excel / CSV exportat din sistemul de monitorizare), lista pe lună. */
export function GpsDaysPage() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const [month, setMonth] = useState<Dayjs>(dayjs().startOf('month'))
  const [vehicle, setVehicle] = useState<number | undefined>()
  const { data: vehicles } = useFetch<Vehicle[]>('/transport/vehicles/', { trailer: 0 })
  const { data, loading, reload } = useFetch<GpsDay[]>('/transport/gps-days/', { month: month.format('YYYY-MM'), vehicle })
  const rows = data ?? []
  const remove = async (id: number) => {
    try {
      await api.delete(`/transport/gps-days/${id}/`)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const total = rows.reduce((s, r) => s + Number(r.km), 0)
  return (
    <Card title={t('menu.gpsDays')} extra={<Space wrap>
      <Select allowClear showSearch optionFilterProp="label" style={{ width: 200 }} placeholder={t('tr.gps.allVehicles')} value={vehicle}
        onChange={setVehicle} options={(vehicles ?? []).map((v) => ({ value: v.id, label: `${v.plate}${v.gps_id ? ` · ${v.gps_id}` : ''}` }))} />
      <DatePicker picker="month" format="MM.YYYY" value={month} allowClear={false} onChange={(v) => v && setMonth(v.startOf('month'))} />
    </Space>}>
      <Space style={{ marginBottom: 12 }} wrap>
        {hasPerm('transport.create') && <ExcelImport code="import" url="/transport/gps-days/" label={t('tr.gps.import')} onDone={reload}
          accept=".xlsx,.csv,.txt" dropText={t('tr.gps.drop')}>
          <Typography.Paragraph type="secondary">{t('tr.gps.importHint')}</Typography.Paragraph></ExcelImport>}
        <Typography.Text type="secondary">{t('tr.gps.hint')}</Typography.Text>
      </Space>
      <Table<GpsDay> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} exportName={t('menu.gpsDays')}
        columns={[
          { title: t('tr.trip.vehicle'), dataIndex: 'plate', width: 110 },
          { title: t('tr.gps.day'), dataIndex: 'day', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('tr.gps.km'), dataIndex: 'km', width: 90, align: 'right', render: (v: string) => num(v) },
          { title: t('tr.gps.moving'), dataIndex: 'moving_min', width: 100, align: 'right', render: (v: number | null) => (v === null ? '' : hm(v)) },
          { title: t('tr.gps.engine'), dataIndex: 'engine_min', width: 100, align: 'right', render: (v: number | null) => (v === null ? '' : hm(v)) },
          { title: t('tr.gps.startStop'), key: 'ss', width: 120, render: (_: unknown, r) => [r.first_start, r.last_stop].map((x) => (x ? x.slice(0, 5) : '…')).join(' – ') },
          { title: t('tr.gps.fuel'), dataIndex: 'fuel_l', width: 90, align: 'right', render: (v: string | null) => num(v, 2) },
          { title: t('tr.gps.odometer'), key: 'o', width: 160, render: (_: unknown, r) => (r.odometer_start ?? r.odometer_end
            ? `${r.odometer_start ?? '…'} – ${r.odometer_end ?? '…'}` : '') },
          { title: t('tr.tacho.countries'), dataIndex: 'countries', width: 110, render: (v: string) => v.split(',').filter(Boolean).map((c) => <Tag key={c}>{c}</Tag>) },
          { title: t('tr.gps.source'), dataIndex: 'source', render: (v: string, r) => <Typography.Text type="secondary">{v} · {dayjs(r.imported_at).format('DD.MM.YYYY HH:mm')}</Typography.Text> },
          ...(hasPerm('transport.delete') ? [{ title: '', key: 'x', width: 50, render: (_: unknown, r: GpsDay) => (
            <Popconfirm title={t('tr.gps.removeConfirm')} onConfirm={() => remove(r.id)}><Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>) }] : []),
        ]}
        summary={() => (rows.length ? (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={2} align="right"><b>{t('mv.total')}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={2} align="right"><b>{num(total)}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={3} colSpan={hasPerm('transport.delete') ? 8 : 7} />
          </Table.Summary.Row>) : null)} />
    </Card>
  )
}

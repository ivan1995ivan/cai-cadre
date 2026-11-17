import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Card, Col, DatePicker, Row, Select, Space, Statistic, Tag, Typography } from 'antd'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { useFetch } from '../../api/hooks'
import type { Occupancy, OccupancyRow } from '../../api/org'

const num = (v: string | number) => Number(v).toLocaleString('ro-MD', { maximumFractionDigits: 2 })

/** Ocuparea posturilor după statele în vigoare la data aleasă: aprobate / ocupate / temporar vacante / vacante. */
export default function OccupancyPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [date, setDate] = useState(dayjs())
  const [onlyVacant, setOnlyVacant] = useState<'all' | 'vacant' | 'over'>('all')
  const { data, loading } = useFetch<Occupancy>('/org/occupancy/', { date: date.format('YYYY-MM-DD') })
  const rows = (data?.rows ?? []).filter((r) => onlyVacant === 'all' || (onlyVacant === 'vacant' ? Number(r.vacant) > 0 : r.over))

  return (
    <Card title={t('menu.occupancy')} extra={<Space>
      <Typography.Text>{t('org.occ.onDate')}</Typography.Text>
      <DatePicker format="DD.MM.YYYY" value={date} onChange={(d) => d && setDate(d)} allowClear={false} />
      <Select value={onlyVacant} onChange={setOnlyVacant} style={{ width: 200 }} options={[
        { value: 'all', label: t('org.occ.all') }, { value: 'vacant', label: t('org.occ.onlyVacant') },
        { value: 'over', label: t('org.occ.onlyOver') }]} />
    </Space>}>
      {data && !data.staff_list && <Alert showIcon type="warning" title={t('org.occ.noStaffList')} />}
      {data?.staff_list && (
        <>
          <Typography.Paragraph type="secondary">
            {t('org.occ.basedOn')} <a onClick={() => navigate(`/staff-list/${data.staff_list!.id}`)}>
              {dayjs(data.staff_list.effective_from).format('DD.MM.YYYY')}{data.staff_list.number ? `, nr. ${data.staff_list.number}` : ''}</a>
          </Typography.Paragraph>
          {!data.employees_module && <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('org.occ.noEmployeesYet')} />}
          {data.totals && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col xs={12} md={6}><Statistic title={t('org.occ.approved')} value={num(data.totals.approved)} /></Col>
              <Col xs={12} md={6}><Statistic title={t('org.occ.occupied')} value={num(data.totals.occupied)} /></Col>
              <Col xs={12} md={6}><Statistic title={t('org.occ.temporary')} value={num(data.totals.temporary)} /></Col>
              <Col xs={12} md={6}><Statistic title={t('org.occ.vacant')} value={num(data.totals.vacant)} /></Col>
            </Row>
          )}
          <Table<OccupancyRow> rowKey={(r) => `${r.subdivision_id}-${r.occupation_id}`} size="small" loading={loading}
            dataSource={rows} pagination={rows.length > 100 ? { pageSize: 100 } : false}
            columns={[
              { title: t('org.subdivision'), dataIndex: 'subdivision', width: 260 },
              { title: t('org.corm'), dataIndex: 'occupation_code', width: 110 },
              { title: t('org.sl.position'), dataIndex: 'occupation', width: 300 },
              { title: t('org.occ.approved'), dataIndex: 'approved', width: 100, align: 'right', render: num },
              { title: t('org.occ.occupied'), dataIndex: 'occupied', width: 100, align: 'right', render: num },
              { title: t('org.occ.temporary'), dataIndex: 'temporary', width: 120, align: 'right', render: num },
              { title: t('org.occ.vacant'), dataIndex: 'vacant', width: 100, align: 'right',
                render: (v: string, r) => r.over ? <Tag color="red">{num(v)}</Tag> : Number(v) > 0 ? <Tag color="gold">{num(v)}</Tag> : num(v) },
              ...(data.employees_module ? [{ title: t('org.occ.holders'), dataIndex: 'holders', width: 260,
                render: (h: OccupancyRow['holders']) => h.map((x) => `${x.name} (${x.units})`).join(', ') }] : []),
            ]} />
        </>
      )}
    </Card>
  )
}

import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'
import { Card, Col, Empty, List, Progress, Row, Space, Statistic, Tag, Typography } from 'antd'
import {
  AlertOutlined, CalendarOutlined, CarOutlined, FileTextOutlined, GiftOutlined, MedicineBoxOutlined, TeamOutlined, UserAddOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import { useFetch } from '../api/hooks'
import { useApp } from '../auth/AppContext'
import { DaysTag, LEVEL_COLOR, type AlertRow } from './AlertsPage'

interface Stats {
  employees?: number
  suspended?: number
  on_leave?: number
  sick?: number
  travel?: number
  units?: { approved: number; occupied: number; vacant: number }
  leave_plan?: { year: number; planned: number; planned_to_date: number; taken: number }
  birthdays?: { id: number; name: string; date: string }[]
  orders_draft?: number | null
  unacknowledged?: number
  leave_requests?: number
  alerts: { total: number; month: number; urgent: number; top: AlertRow[] }
}

/** Panoul de start: indicatorii întreprinderii (sau ai subdiviziunilor șefului) și termenele cele mai apropiate. */
export default function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { me, companyName, hasPerm } = useApp()
  const portalOnly = !me?.is_admin && hasPerm('portal.view') && !hasPerm('employees.view')
  const { data, loading } = useFetch<Stats>(portalOnly ? null : '/alerts/dashboard/')
  const units = data?.units
  const tile = (key: string, value: number | undefined | null, icon: React.ReactNode, link?: string, color?: string) =>
    value === undefined || value === null ? null : (
      <Col key={key} xs={12} md={8} xl={4}>
        <Card hoverable={!!link} onClick={() => link && navigate(link)} loading={loading}>
          <Statistic title={t(`dashboard.${key}`)} value={value} prefix={icon} styles={{ content: color ? { color } : undefined }} />
        </Card>
      </Col>
    )
  if (portalOnly) return <Navigate to="/portal" replace />
  return (
    <div>
      <Typography.Title level={4} style={{ marginTop: 0 }}>{companyName || t('dashboard.title')}</Typography.Title>
      <Typography.Paragraph type="secondary">{t('dashboard.welcome', { name: me?.full_name ?? '' })} · {dayjs().format('DD.MM.YYYY')}</Typography.Paragraph>
      <Row gutter={[16, 16]}>
        {tile('employees', data?.employees, <TeamOutlined />, '/employees')}
        {tile('onLeave', data?.on_leave, <CalendarOutlined />, '/leave')}
        {tile('sick', data?.sick, <MedicineBoxOutlined />, '/sick-leave')}
        {tile('travel', data?.travel, <CarOutlined />)}
        {tile('alertsMonth', data?.alerts.month, <AlertOutlined />, '/alerts', data?.alerts.urgent ? '#cf1322' : undefined)}
        {tile('leaveRequests', data?.leave_requests, <UserAddOutlined />, '/leave?tab=requests')}
        {tile('ordersDraft', data?.orders_draft, <FileTextOutlined />, '/orders')}
        {tile('unacknowledged', data?.unacknowledged, <FileTextOutlined />, '/alerts')}
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {units && units.approved > 0 && <Col xs={24} lg={8}>
          <Card title={t('dashboard.units')} onClick={() => navigate('/staff-list/occupancy')} hoverable>
            <Progress type="dashboard" percent={Math.round((units.occupied / units.approved) * 100)} />
            <Space orientation="vertical" size={0} style={{ marginLeft: 12 }}>
              <Typography.Text>{t('dashboard.approved')}: <b>{units.approved}</b></Typography.Text>
              <Typography.Text>{t('dashboard.occupied')}: <b>{units.occupied}</b></Typography.Text>
              <Typography.Text type={units.vacant ? 'warning' : undefined}>{t('dashboard.vacancies')}: <b>{units.vacant}</b></Typography.Text>
            </Space>
          </Card>
        </Col>}
        {data?.leave_plan && data.leave_plan.planned > 0 && <Col xs={24} lg={8}>
          <Card title={t('dashboard.leavePlan', { year: data.leave_plan.year })} onClick={() => navigate('/leave/schedule')} hoverable>
            <Progress type="dashboard" percent={data.leave_plan.planned_to_date
              ? Math.round((data.leave_plan.taken / data.leave_plan.planned_to_date) * 100) : 0} />
            <Space orientation="vertical" size={0} style={{ marginLeft: 12 }}>
              <Typography.Text>{t('dashboard.leavePlanned')}: <b>{data.leave_plan.planned}</b></Typography.Text>
              <Typography.Text>{t('dashboard.leaveToDate')}: <b>{data.leave_plan.planned_to_date}</b></Typography.Text>
              <Typography.Text>{t('dashboard.leaveTaken')}: <b>{data.leave_plan.taken}</b></Typography.Text>
            </Space>
          </Card>
        </Col>}
        <Col xs={24} lg={units && units.approved > 0 ? 10 : 16}>
          <Card title={t('dashboard.nearest')} extra={<a onClick={() => navigate('/alerts')}>{t('dashboard.allAlerts', { count: data?.alerts.total ?? 0 })}</a>}>
            {data?.alerts.top.length ? <List size="small" dataSource={data.alerts.top} renderItem={(a) => (
              <List.Item onClick={() => a.link && navigate(a.link)} style={{ cursor: a.link ? 'pointer' : undefined }}
                extra={<DaysTag days={a.days} />}>
                <List.Item.Meta title={<Tag color={LEVEL_COLOR[a.level]}>{t(`al.kinds.${a.kind}`)}</Tag>} description={a.text} />
              </List.Item>)} /> : <Empty description={t('dashboard.noAlerts')} />}
          </Card>
        </Col>
        {!!data?.birthdays?.length && <Col xs={24} lg={6}>
          <Card title={<Space><GiftOutlined />{t('dashboard.birthdays')}</Space>}>
            <List size="small" dataSource={data.birthdays} renderItem={(b) => (
              <List.Item onClick={() => navigate(`/employees/${b.id}`)} style={{ cursor: 'pointer' }}>
                {b.name}<Typography.Text type="secondary">{dayjs(b.date).format('DD.MM')}</Typography.Text>
              </List.Item>)} />
          </Card>
        </Col>}
      </Row>
    </div>
  )
}

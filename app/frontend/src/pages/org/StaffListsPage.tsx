import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Space, Tag, Typography } from 'antd'
import { PlusOutlined, TeamOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { StaffList } from '../../api/org'
import { useApp } from '../../auth/AppContext'
import { message } from 'antd'

export const STATUS_COLOR: Record<string, string> = { draft: 'gold', approved: 'green', cancelled: 'default' }

/** Versiunile statelor de personal; cele aprobate rămân ca istoric, ultima în vigoare e marcată. */
export default function StaffListsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const { data, loading } = useFetch<{ results: StaffList[] }>('/org/staff-lists/', { page_size: 200 })
  const rows = data?.results ?? []
  const today = dayjs().format('YYYY-MM-DD')
  const current = rows.filter((r) => r.status === 'approved' && r.effective_from <= today)
    .sort((a, b) => b.effective_from.localeCompare(a.effective_from))[0]

  const create = async () => {
    try {
      const r = await api.post<StaffList>('/org/staff-lists/', { effective_from: today })
      navigate(`/staff-list/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <Card title={t('menu.staffList')} extra={<Space>
      <Button icon={<TeamOutlined />} onClick={() => navigate('/staff-list/occupancy')}>{t('menu.occupancy')}</Button>
      {hasPerm('org.create') && <Button type="primary" icon={<PlusOutlined />} onClick={create}>{t('org.sl.new')}</Button>}
    </Space>}>
      {!loading && rows.length === 0 && <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('org.sl.emptyHint')} />}
      <Table<StaffList> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} rowTone={(r) => ROW_TONE.staffList(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/staff-list/${r.id}`) })}
        columns={[
          { title: t('org.sl.effectiveFrom'), dataIndex: 'effective_from', width: 140, render: (v: string, r) => (
            <Space><a onClick={() => navigate(`/staff-list/${r.id}`)}>{dayjs(v).format('DD.MM.YYYY')}</a>
              {current?.id === r.id && <Tag color="green">{t('org.sl.current')}</Tag>}</Space>) },
          { title: t('org.sl.number'), dataIndex: 'number', width: 90 },
          { title: t('org.sl.status'), dataIndex: 'status', width: 120,
            render: (v: string) => <Tag color={STATUS_COLOR[v]}>{t(`org.sl.statuses.${v}`)}</Tag> },
          { title: t('org.sl.approvedBy'), dataIndex: 'approved_by' },
          { title: t('org.sl.lines'), dataIndex: 'lines_count', width: 90, align: 'right' },
          { title: t('org.sl.previous'), dataIndex: 'previous_label', width: 260,
            render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
        ]} />
    </Card>
  )
}

import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Card, Space, Table, Typography } from 'antd'
import { LinkOutlined } from '@ant-design/icons'

import { useFetch } from '../../api/hooks'

interface RelatedRow { kind: string; label: string; employee: string; detail: string; link: string }

/** „Documente legate” ale ordinului semnat: ce a rezultat din punctele lui și de unde a pornit. */
export default function RelatedDocs({ order }: { order: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data } = useFetch<{ made: RelatedRow[]; sources: RelatedRow[] }>(`/orders/orders/${order}/related/`)
  if (!data || (!data.made.length && !data.sources.length)) return null
  const columns = [
    { title: t('ord.related.what'), dataIndex: 'label', render: (v: string, r: RelatedRow) => (r.link ? <a onClick={() => navigate(r.link)}>{v}</a> : v) },
    { title: t('ord.related.employee'), dataIndex: 'employee', width: 220 },
    { title: t('ord.related.detail'), dataIndex: 'detail', render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
  ]
  return (
    <Card title={<Space><LinkOutlined />{t('ord.related.title')}</Space>}>
      {data.sources.length > 0 && <>
        <Typography.Text strong>{t('ord.related.sources')}</Typography.Text>
        <Table<RelatedRow> size="small" rowKey={(r) => `${r.kind}-${r.label}-${r.employee}`} dataSource={data.sources} pagination={false}
          columns={columns} style={{ margin: '6px 0 14px' }} />
      </>}
      {data.made.length > 0 && <>
        <Typography.Text strong>{t('ord.related.made')}</Typography.Text>
        <Table<RelatedRow> size="small" rowKey={(r) => `${r.kind}-${r.label}-${r.employee}-${r.detail}`} dataSource={data.made}
          pagination={data.made.length > 20 ? { pageSize: 20 } : false} columns={columns} style={{ marginTop: 6 }} />
      </>}
    </Card>
  )
}

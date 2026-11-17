import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Card, Col, Empty, Input, Row, Space, Spin, Tag, Typography } from 'antd'
import { BarChartOutlined, LinkOutlined, SearchOutlined } from '@ant-design/icons'

import { useFetch } from '../../api/hooks'
import { fold } from '../../utils/text'

export interface CatalogItem {
  key: string
  group: string
  group_title: string
  title: string
  hint: string
  filters: string[]
  link: string
}

/** Catalogul rapoartelor pe grupe; rapoartele care au pagina lor în modul se deschid acolo. Căutarea (fără diacritice)
 *  caută în denumire, descriere și grupă; Enter deschide raportul când a rămas unul singur. */
export default function ReportsPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { data, loading } = useFetch<CatalogItem[]>('/reports/', { lang: i18n.language })
  const [search, setSearch] = useState('')
  const found = useMemo(() => {
    const q = fold(search.trim())
    return q ? (data ?? []).filter((r) => fold(`${r.title} ${r.hint} ${r.group_title}`).includes(q)) : data ?? []
  }, [data, search])
  const open = (r: CatalogItem) => navigate(r.link || `/reports/${r.key}`)
  const groups: { key: string; title: string; items: CatalogItem[] }[] = []
  for (const item of found) {
    let g = groups.find((x) => x.key === item.group)
    if (!g) groups.push(g = { key: item.group, title: item.group_title, items: [] })
    g.items.push(item)
  }
  if (loading && !data) return <Spin />
  if (!data?.length) return <Card title={t('menu.reports')}><Empty /></Card>
  return (
    <div>
      <Space wrap style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>{t('menu.reports')}</Typography.Title>
        <Input allowClear autoFocus prefix={<SearchOutlined />} placeholder={t('rep.search')} style={{ width: 360 }}
          value={search} onChange={(e) => setSearch(e.target.value)} onPressEnter={() => { if (found.length === 1) open(found[0]) }} />
      </Space>
      {!groups.length && <Empty description={t('rep.none')} />}
      {groups.map((g) => (
        <div key={g.key} style={{ marginBottom: 24 }}>
          <Typography.Title level={5}>{g.title}</Typography.Title>
          <Row gutter={[16, 16]}>
            {g.items.map((r) => (
              <Col key={r.key} xs={24} md={12} xl={8}>
                <Card hoverable size="small" style={{ height: '100%' }} onClick={() => open(r)}
                  title={<span>{r.link ? <LinkOutlined /> : <BarChartOutlined />} {r.title}</span>}
                  extra={r.link ? <Tag>{t('rep.inModule')}</Tag> : null}>
                  <Typography.Text type="secondary">{r.hint}</Typography.Text>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      ))}
    </div>
  )
}

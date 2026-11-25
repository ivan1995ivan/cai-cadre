import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Input, Select, Space, Tag } from 'antd'
import { BookOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import NewOrderDialog from './NewOrderDialog'
import type { Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { OrgMeta } from '../../api/org'
import { ORDER_STATUS_COLOR, type Order } from '../../api/orders'
import { useApp } from '../../auth/AppContext'
import { useEnumOptions } from '../org/DictionariesPage'

/** Lista ordinelor: filtre pe registru, an, stare, grupă; ordin nou din tipul ales. */
export default function OrdersList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const opts = useEnumOptions()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({ year: dayjs().year() })
  const [page, setPage] = useState(1)
  const { data, loading } = useFetch<Paged<Order>>('/orders/orders/', { ...filters, page, page_size: 50 })
  const { data: meta } = useFetch<OrgMeta>('/org/meta/')
  const [creating, setCreating] = useState(false)
  const set = (k: string, v: string | number | undefined) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1) }


  return (
    <Card title={t('menu.orders')} extra={<Space>
      <Button icon={<BookOutlined />} onClick={() => navigate('/orders/register')}>{t('menu.ordersRegister')}</Button>
      {hasPerm('orders.create') && <Button type="primary" icon={<PlusOutlined />}
        onClick={() => setCreating(true)}>{t('ord.new')}</Button>}
    </Space>}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search allowClear placeholder={t('ord.searchHint')} style={{ width: 260 }} onSearch={(v) => set('q', v || undefined)} />
        <Select style={{ width: 110 }} value={filters.year} onChange={(v) => set('year', v)}
          options={Array.from({ length: 6 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />
        <Select allowClear style={{ width: 240 }} placeholder={t('org.register')} value={filters.register as string | undefined}
          onChange={(v) => set('register', v)} options={opts('org.registers', meta?.order_registers)} />
        <Select allowClear style={{ width: 240 }} placeholder={t('org.group')} value={filters.group as string | undefined}
          onChange={(v) => set('group', v)} options={opts('org.orderGroup', meta?.order_groups)} />
        <Select allowClear style={{ width: 150 }} placeholder={t('ord.status')} value={filters.status as string | undefined}
          onChange={(v) => set('status', v)} options={['draft', 'signed', 'cancelled'].map((s) => ({ value: s, label: t(`ord.statuses.${s}`) }))} />
      </Space>
      <Table<Order> rowKey="id" size="small" loading={loading} dataSource={data?.results ?? []} exportName={t('menu.orders')}
        rowTone={(r) => ROW_TONE.order(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/orders/${r.id}`) })}
        pagination={{ current: page, pageSize: 50, total: data?.count ?? 0, onChange: setPage, showTotal: (n) => t('common.total', { count: n }) }}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', key: 'number', width: 90, render: (v: string, r) => <a onClick={() => navigate(`/orders/${r.id}`)}>{v || t('ord.noNumber')}</a> },
          { title: t('ord.date'), dataIndex: 'date', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('ord.type'), dataIndex: 'type_name', width: 230 },
          { title: t('ord.title'), dataIndex: 'title' },
          { title: t('ord.employees'), dataIndex: 'employees', width: 240 },
          { title: t('ord.status'), dataIndex: 'status', width: 110, render: (v: string) => <Tag color={ORDER_STATUS_COLOR[v]}>{t(`ord.statuses.${v}`)}</Tag> },
        ]} />

      <NewOrderDialog open={creating} onClose={() => setCreating(false)} />
    </Card>
  )
}

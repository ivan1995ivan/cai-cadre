import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Space, Table, Tag, Typography } from 'antd'
import dayjs from 'dayjs'

import { useFetch } from '../../api/hooks'
import type { Absence, IncentiveRec, OrderItem, SanctionRec } from '../../api/orders'

const d = (v: string | null) => (v ? dayjs(v).format('DD.MM.YYYY') : '')

interface ItemRow extends OrderItem { order_label?: string; order_status?: string }

/** Fila „Ordine și absențe” din fișa angajatului: tot ce s-a emis pentru el și ce a rezultat (concedii, sancțiuni...). */
export default function OrdersTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data: items } = useFetch<ItemRow[]>('/orders/items/', { employee })
  const { data: absences } = useFetch<Absence[]>('/orders/absences/', { employee })
  const { data: sanctions } = useFetch<SanctionRec[]>('/orders/sanctions/', { employee })
  const { data: incentives } = useFetch<IncentiveRec[]>('/orders/incentives/', { employee })
  const today = dayjs().format('YYYY-MM-DD')
  const orderLink = (o: { id: number; label: string } | null) => (o ? <a onClick={() => navigate(`/orders/${o.id}`)}>{o.label}</a> : '')

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={20}>
      <div>
        <Typography.Text strong>{t('ord.tab.orders')}</Typography.Text>
        <Table<ItemRow> size="small" rowKey="id" pagination={{ pageSize: 10 }} dataSource={items ?? []} style={{ marginTop: 6 }}
          columns={[
            { title: t('ord.tab.order'), key: 'order', width: 190, render: (_: unknown, r) => (
              <Space size={4}><a onClick={() => navigate(`/orders/${r.order}`)}>{r.order_label || t('ord.open')}</a>
                {r.order_status === 'cancelled' && <Tag color="red">{t('ord.statuses.cancelled')}</Tag>}</Space>) },
            { title: t('ord.pointText'), dataIndex: 'text' },
            { title: t('ord.acknowledgedCol'), dataIndex: 'acknowledged_on', width: 130, render: d },
          ]} />
      </div>
      <div>
        <Typography.Text strong>{t('ord.tab.absences')}</Typography.Text>
        <Table<Absence> size="small" rowKey="id" pagination={{ pageSize: 10 }} dataSource={absences ?? []} style={{ marginTop: 6 }}
          columns={[
            { title: t('ord.tab.kind'), dataIndex: 'kind_label', width: 260 },
            { title: t('staff.sen.from'), dataIndex: 'date_from', width: 110, render: d },
            { title: t('staff.sen.to'), dataIndex: 'date_to', width: 110, render: d },
            { title: t('ord.p.days'), dataIndex: 'days', width: 70, align: 'right' },
            { title: t('ord.tab.details'), key: 'det', render: (_: unknown, r) => [r.destination, r.note,
              r.recalled_on ? t('ord.tab.recalled', { date: d(r.recalled_on), days: r.days_returned }) : ''].filter(Boolean).join(' · ') },
            { title: t('ord.tab.order'), dataIndex: 'order', width: 160, render: orderLink },
          ]} />
      </div>
      <div>
        <Typography.Text strong>{t('ord.tab.sanctions')}</Typography.Text>
        <Table<SanctionRec> size="small" rowKey="id" pagination={false} dataSource={sanctions ?? []} style={{ marginTop: 6 }}
          columns={[
            { title: t('ord.p.sanction'), dataIndex: 'kind_name', width: 160 },
            { title: t('ord.date'), dataIndex: 'date', width: 110, render: d },
            { title: t('ord.p.misconduct'), dataIndex: 'misconduct' },
            { title: t('ord.tab.status'), key: 'st', width: 200, render: (_: unknown, r) => r.lifted_on
              ? <Tag>{t('ord.tab.lifted', { date: d(r.lifted_on) })}</Tag>
              : r.valid_until < today ? <Tag>{t('ord.tab.expired')}</Tag> : <Tag color="red">{t('ord.tab.activeUntil', { date: d(r.valid_until) })}</Tag> },
            { title: t('ord.tab.order'), dataIndex: 'order', width: 160, render: orderLink },
          ]} />
      </div>
      <div>
        <Typography.Text strong>{t('ord.tab.incentives')}</Typography.Text>
        <Table<IncentiveRec> size="small" rowKey="id" pagination={false} dataSource={incentives ?? []} style={{ marginTop: 6 }}
          columns={[
            { title: t('ord.tab.kind'), dataIndex: 'kind_name', width: 160 },
            { title: t('ord.date'), dataIndex: 'date', width: 110, render: d },
            { title: t('ord.p.amount'), key: 'sum', width: 140, render: (_: unknown, r) => r.amount ? `${Number(r.amount).toLocaleString('ro-MD')} lei` : r.percent ? `${r.percent}%` : '' },
            { title: t('ord.p.forWhat'), dataIndex: 'note' },
            { title: t('ord.tab.order'), dataIndex: 'order', width: 160, render: orderLink },
          ]} />
      </div>
    </Space>
  )
}

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Select, Space, Tag } from 'antd'
import { PrinterOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import PrintDialog from '../../components/PrintDialog'
import { useFetch } from '../../api/hooks'
import type { OrgMeta } from '../../api/org'
import { ORDER_STATUS_COLOR, type Order } from '../../api/orders'
import { useEnumOptions } from '../org/DictionariesPage'

/** Registrul ordinelor pe an: în ordinea numerelor, cu numerele lipsă semnalate. */
export default function RegisterPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const opts = useEnumOptions()
  const [register, setRegister] = useState('order_personnel')
  const [year, setYear] = useState(dayjs().year())
  const [printOpen, setPrintOpen] = useState(false)
  const { data: meta } = useFetch<OrgMeta>('/org/meta/')
  const { data, loading } = useFetch<{ orders: Order[]; gaps: string[] }>('/orders/orders/register/', { register, year })
  return (
    <Card title={t('menu.ordersRegister')} extra={<Space wrap>
      <Select style={{ width: 260 }} value={register} onChange={setRegister} options={opts('org.registers', meta?.order_registers)} />
      <Select style={{ width: 110 }} value={year} onChange={setYear}
        options={Array.from({ length: 6 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />
      <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('org.sl.print')}</Button>
    </Space>}>
      {!!data?.gaps.length && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('ord.gaps', { list: data.gaps.join(', ') })} />}
      <Table<Order> rowKey="id" size="small" loading={loading} dataSource={data?.orders ?? []} pagination={false} exportName={t('menu.ordersRegister')}
        rowTone={(r) => ROW_TONE.order(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/orders/${r.id}`) })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', key: 'number', width: 90, render: (v: string, r) => <a onClick={() => navigate(`/orders/${r.id}`)}>{v}</a> },
          { title: t('ord.date'), dataIndex: 'date', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('ord.title'), dataIndex: 'title' },
          { title: t('ord.employees'), dataIndex: 'employees', width: 260 },
          { title: t('ord.status'), dataIndex: 'status', width: 110, render: (v: string) => <Tag color={ORDER_STATUS_COLOR[v]}>{t(`ord.statuses.${v}`)}</Tag> },
        ]} />
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="orders_register" url="/orders/orders/print-register/"
        params={{ register, year }} optionKeys={[]} title={t('menu.ordersRegister')} />
    </Card>
  )
}

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, DatePicker, InputNumber, Modal, Segmented, Space, Typography, message } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import { api, errorText } from '../../api/client'
import type { OrderItem } from '../../api/orders'

interface Share { item: number; employee: number; name: string; basis: number; amount: number }
const money = (v: number) => v.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

/** Împărțirea unei sume pe punctele ordinului de premiere: egal, după salariul de funcție sau după orele din pontaj; sumele se
 *  pun în puncte (se pot corecta apoi de mână). */
export default function DistributeDialog({ order, items, open, onClose, onDone }: {
  order: number
  items: OrderItem[]
  open: boolean
  onClose: () => void
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [total, setTotal] = useState<number | null>(null)
  const [method, setMethod] = useState<'equal' | 'salary' | 'hours'>('equal')
  const [month, setMonth] = useState<Dayjs>(dayjs().subtract(1, 'month'))
  const [rows, setRows] = useState<Share[] | null>(null)
  const [busy, setBusy] = useState(false)
  const calc = async () => {
    try {
      const r = await api.post<{ rows: Share[] }>(`/orders/orders/${order}/distribute/`,
        { total, method, year: month.year(), month: month.month() + 1 })
      setRows(r.data.rows)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const apply = async () => {
    if (!rows) return
    setBusy(true)
    try {
      for (const row of rows) {
        const item = items.find((x) => x.id === row.item)
        await api.patch(`/orders/items/${row.item}/`, { params: { ...(item?.params ?? {}), amount: row.amount, percent: null } })
      }
      message.success(t('ord.dist.done', { n: rows.length }))
      onDone()
      onClose()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal open={open} onCancel={onClose} width={760} title={t('ord.dist.title')}
      footer={<Space><Button onClick={onClose}>{t('common.cancel')}</Button>
        <Button type="primary" disabled={!rows} loading={busy} onClick={apply}>{t('ord.dist.apply')}</Button></Space>}>
      <Typography.Paragraph type="secondary">{t('ord.dist.hint')}</Typography.Paragraph>
      <Space wrap style={{ marginBottom: 12 }}>
        <InputNumber min={0.01} step={100} value={total} onChange={(v) => { setTotal(v); setRows(null) }} suffix="lei"
          placeholder={t('ord.dist.total')} style={{ width: 180 }} />
        <Segmented value={method} onChange={(v) => { setMethod(v as typeof method); setRows(null) }}
          options={(['equal', 'salary', 'hours'] as const).map((m) => ({ value: m, label: t(`ord.dist.methods.${m}`) }))} />
        {method === 'hours' && <DatePicker picker="month" format="MM.YYYY" value={month} allowClear={false}
          onChange={(v) => { if (v) { setMonth(v); setRows(null) } }} />}
        <Button disabled={!total} onClick={calc}>{t('ord.dist.calc')}</Button>
      </Space>
      {rows && <Table<Share> rowKey="item" size="small" dataSource={rows} pagination={false}
        columns={[
          { title: t('mv.employee'), dataIndex: 'name' },
          { title: t(`ord.dist.basis.${method}`), dataIndex: 'basis', width: 150, align: 'right',
            render: (v: number) => (method === 'equal' ? '' : v.toLocaleString('ro-RO', { maximumFractionDigits: 2 })) },
          { title: t('ord.dist.amount'), dataIndex: 'amount', width: 150, align: 'right', render: (v: number) => <b>{money(v)}</b> },
        ]}
        summary={() => <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={2} align="right"><b>{t('mv.total')}</b></Table.Summary.Cell>
          <Table.Summary.Cell index={2} align="right"><b>{money(rows.reduce((s, r) => s + r.amount, 0))}</b></Table.Summary.Cell>
        </Table.Summary.Row>} />}
    </Modal>
  )
}

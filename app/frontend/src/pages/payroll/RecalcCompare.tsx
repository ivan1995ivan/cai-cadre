import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Modal, Space, Tag, Typography, message } from 'antd'

import Table from '../../components/AppTable'
import { api, errorText } from '../../api/client'

interface Row {
  employee: number
  name: string
  tab_number: string
  status: 'new' | 'removed' | 'changed'
  old_gross: number | null
  new_gross: number | null
  old_net: number | null
  new_net: number | null
  diff_net: number
  items: { code: string; old: number; new: number }[]
}

const money = (v: number | null) => (v === null ? '—' : v.toLocaleString('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

/** Recalcularea cu comparație: ce s-ar schimba pe fiecare angajat dacă luna s-ar calcula acum (vechi → nou, rândurile pe
 *  tipuri care diferă); se aplică doar pentru cei bifați, ceilalți rămân cum erau. */
export default function RecalcCompare({ payroll, open, onClose, onApplied }: {
  payroll: number
  open: boolean
  onClose: () => void
  onApplied: () => void
}) {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Row[] | null>(null)
  const [selected, setSelected] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    if (!open) return
    setRows(null)
    api.post<{ rows: Row[] }>(`/payroll/payrolls/${payroll}/preview/`)
      .then((r) => { setRows(r.data.rows); setSelected(r.data.rows.map((x) => x.employee)) })
      .catch((e) => { message.error(errorText(e)); onClose() })
  }, [open, payroll]) // eslint-disable-line react-hooks/exhaustive-deps
  const apply = async () => {
    setBusy(true)
    try {
      await api.post(`/payroll/payrolls/${payroll}/apply/`, { employees: selected })
      message.success(t('pay.cmp.applied', { n: selected.length }))
      onApplied()
      onClose()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal open={open} onCancel={onClose} width={1100} title={t('pay.cmp.title')}
      footer={<Space>
        <Button onClick={onClose}>{t('common.cancel')}</Button>
        <Button type="primary" loading={busy} disabled={!selected.length} onClick={apply}>{t('pay.cmp.apply', { n: selected.length })}</Button>
      </Space>}>
      <Typography.Paragraph type="secondary">{t('pay.cmp.hint')}</Typography.Paragraph>
      {rows && !rows.length && <Alert type="success" showIcon title={t('pay.cmp.none')} />}
      {(rows === null || rows.length > 0) && <Table<Row> rowKey="employee" size="small" loading={rows === null} dataSource={rows ?? []}
        pagination={false} scroll={{ y: 480 }} exportName={t('pay.cmp.title')}
        rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as number[]) }}
        columns={[
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 80 },
          { title: t('mv.employee'), dataIndex: 'name', width: 200,
            render: (v: string, r) => <>{v}{r.status !== 'changed' && <Tag style={{ marginInlineStart: 6 }} color={r.status === 'new' ? 'green' : 'red'}>
              {t(`pay.cmp.status.${r.status}`)}</Tag>}</> },
          { title: t('pay.cmp.gross'), key: 'g', width: 190, align: 'right', render: (_: unknown, r) => `${money(r.old_gross)} → ${money(r.new_gross)}` },
          { title: t('pay.cmp.net'), key: 'n', width: 190, align: 'right', render: (_: unknown, r) => `${money(r.old_net)} → ${money(r.new_net)}` },
          { title: t('pay.cmp.diff'), dataIndex: 'diff_net', width: 110, align: 'right',
            render: (v: number) => <b style={{ color: v > 0 ? '#389e0d' : v < 0 ? '#cf1322' : undefined }}>{v > 0 ? '+' : ''}{money(v)}</b> },
          { title: t('pay.cmp.items'), dataIndex: 'items', render: (items: Row['items']) => items.map((i) =>
            <Tag key={i.code}>{i.code}: {money(i.old)} → {money(i.new)}</Tag>) },
        ]} />}
    </Modal>
  )
}

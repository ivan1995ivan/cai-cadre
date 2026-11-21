import { useTranslation } from 'react-i18next'
import { Button, DatePicker, Input, InputNumber, Select, Space, Tag, Typography } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { useFetch } from '../../api/hooks'
import { PAY_ACTIONS, type EmployeePayItem, type PayType, type PlannedRow } from '../../api/payroll'
import { useApp, useLocalName } from '../../auth/AppContext'

const ACTION_COLOR: Record<string, string> = { add: 'green', modify: 'blue', stop: 'red' }

/** Tipurile care se pun pe angajat (fără cele automate), pentru alegere în rânduri. */
export function usePersonalTypes() {
  const localName = useLocalName()
  const { data } = useFetch<PayType[]>('/payroll/types/', { active: 1, personal: 1 })
  const types = data ?? []
  return { types, options: types.map((x) => ({ value: x.id, label: `${x.code} — ${localName(x)} (${x.category_label})` })) }
}

/** Rândurile din fila „Salariu” ale angajatului (pentru „modifică” / „oprește”: alegerea rândului). */
export function useEmployeeRows(employee: number | null | undefined) {
  const { hasPerm } = useApp()
  const { data } = useFetch<EmployeePayItem[]>(employee && hasPerm('payroll.view') ? '/payroll/employee-items/' : null, { employee })
  return data ?? []
}

const d = (v: string | null | undefined) => (v ? dayjs(v) : null)
export const fmtDate = (v: string | null | undefined) => (v ? dayjs(v).format('DD.MM.YYYY') : '')

/** Un rând „Acumulări și rețineri”: tipul, acțiunea, rândul vizat, suma / procentul / cantitatea, de la / până la, temeiul. */
export function PlannedRowFields({ row, set, typeOptions, existing, disabled, fromHint }: {
  row: PlannedRow
  set: (patch: Partial<PlannedRow>) => void
  typeOptions: { value: number; label: string }[]
  existing: EmployeePayItem[]
  disabled?: boolean
  fromHint?: string
}) {
  const { t } = useTranslation()
  const mine = existing.filter((x) => x.pay_type === row.pay_type)
  return (
    <>
      <Tag color={ACTION_COLOR[row.action]}>{t(`pay.pl.actions.${row.action}`)}</Tag>
      <Select showSearch optionFilterProp="label" style={{ width: 300 }} placeholder={t('pay.item')} value={row.pay_type ?? undefined}
        disabled={disabled} onChange={(v) => set({ pay_type: v, target: null })} options={typeOptions} />
      <Select style={{ width: 130 }} value={row.action} disabled={disabled} onChange={(v) => set({ action: v })}
        options={PAY_ACTIONS.map((a) => ({ value: a, label: t(`pay.pl.actions.${a}`) }))} />
      {row.action !== 'add' && mine.length > 0 && <Select allowClear style={{ width: 260 }} placeholder={t('pay.pl.target')} disabled={disabled}
        value={row.target ?? undefined} onChange={(v) => set({ target: v ?? null })}
        options={mine.map((x) => ({ value: x.id, label: `${fmtDate(x.date_from)} – ${fmtDate(x.date_to) || '…'}: ${x.amount ?? ''}${x.percent ? ` ${Number(x.percent)} %` : ''}` }))} />}
      {row.action !== 'stop' && <>
        <InputNumber style={{ width: 110 }} placeholder={t('pay.amount')} min={0} disabled={disabled} value={row.amount as number | null}
          onChange={(v) => set({ amount: v })} />
        <InputNumber style={{ width: 80 }} placeholder="%" min={0} disabled={disabled} value={row.percent as number | null} onChange={(v) => set({ percent: v })} />
        <InputNumber style={{ width: 100 }} placeholder={t('pay.fx.quantity')} min={0} disabled={disabled} value={row.quantity as number | null}
          onChange={(v) => set({ quantity: v })} />
      </>}
      <DatePicker style={{ width: 135 }} format="DD.MM.YYYY" placeholder={row.action === 'stop' ? t('pay.pl.stopFrom') : (fromHint || t('staff.sen.from'))}
        disabled={disabled} value={d(row.date_from)} onChange={(v) => set({ date_from: v ? v.format('YYYY-MM-DD') : null })} />
      <DatePicker style={{ width: 135 }} format="DD.MM.YYYY" placeholder={row.action === 'stop' ? t('pay.pl.lastDay') : t('staff.sen.to')}
        disabled={disabled} value={d(row.date_to)} onChange={(v) => set({ date_to: v ? v.format('YYYY-MM-DD') : null })} />
      <Input style={{ width: 240 }} placeholder={t('pay.pl.basis')} disabled={disabled} value={row.document ?? ''} onChange={(e) => set({ document: e.target.value })} />
    </>
  )
}

/** Tabelul „Acumulări și rețineri” al punctului de ordin (`params.pay_items`): la semnare rândurile intră în fila „Salariu”. */
export default function PlannedRowsInput({ value, onChange, employee, disabled, onFromOccupation }: {
  value?: PlannedRow[]
  onChange?: (v: PlannedRow[]) => void
  employee: number | null
  disabled?: boolean
  onFromOccupation?: () => void
}) {
  const { t } = useTranslation()
  const { options } = usePersonalTypes()
  const existing = useEmployeeRows(employee)
  const rows = value ?? []
  const set = (i: number, patch: Partial<PlannedRow>) => onChange?.(rows.map((r, k) => (k === i ? { ...r, ...patch } : r)))
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={6}>
      {rows.map((r, i) => (
        <Space key={i} wrap size={4} style={{ padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6 }}>
          <PlannedRowFields row={r} set={(p) => set(i, p)} typeOptions={options} existing={existing} disabled={disabled}
            fromHint={t('pay.pl.fromOrder')} />
          {!disabled && <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange?.(rows.filter((_x, k) => k !== i))} />}
        </Space>
      ))}
      {!disabled && <Space wrap>
        <Button size="small" icon={<PlusOutlined />} onClick={() => onChange?.([...rows, { pay_type: null, action: 'add' }])}>{t('pay.pl.addRow')}</Button>
        {onFromOccupation && <Button size="small" onClick={onFromOccupation}>{t('pay.pl.fromOccupation')}</Button>}
      </Space>}
      <Typography.Text type="secondary">{t('pay.pl.hint')}</Typography.Text>
    </Space>
  )
}

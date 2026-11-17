import { useEffect, useState, type CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Input, Modal, Segmented, Select, Space, Tag, Tooltip, Typography } from 'antd'
import { EllipsisOutlined } from '@ant-design/icons'

import { api, type Paged } from '../api/client'
import { useFetch } from '../api/hooks'
import type { EmployeeRow } from '../api/staff'
import Table from './AppTable'
import SubdivisionSelect from './SubdivisionSelect'

type Option = { value: number; label: string }

const STATUS_COLOR: Record<string, string> = { active: 'green', suspended: 'orange', dismissed: 'default', candidate: 'blue' }
const labelOf = (e: Pick<EmployeeRow, 'full_name' | 'tab_number' | 'occupation'>) =>
  `${e.full_name} · ${e.tab_number}${e.occupation ? ` · ${e.occupation}` : ''}`

/**
 * Alegerea angajatului, ca în 1C (după ClientSelect din CRM acoperiș gard): scrieți în câmp (numele, nr. de tabel, IDNP)
 * sau apăsați „…” și alegeți din lista angajaților — cu subdiviziunea, funcția și starea, filtru pe subdiviziune și pe
 * cei care lucrează acum / toți. Denumirile celor deja aleși se iau de pe server după `ids` (fără deschiderea dosarului).
 */
export default function EmployeeSelect({ value, onChange, mode, label, allowClear = true, disabled, placeholder, style }: {
  value?: number | number[] | null
  onChange?: (value: number | number[] | null, rows?: EmployeeRow[]) => void
  mode?: 'multiple'
  /** denumirea angajatului ales, dacă pagina o are deja (altfel se cere de pe server) */
  label?: string
  allowClear?: boolean
  disabled?: boolean
  placeholder?: string
  style?: CSSProperties
}) {
  const { t } = useTranslation()
  const [options, setOptions] = useState<Option[]>([])
  const [rows, setRows] = useState<Record<number, EmployeeRow>>({})
  const [listOpen, setListOpen] = useState(false)
  const chosen = Array.isArray(value) ? value : value ? [value] : []

  const remember = (list: EmployeeRow[]) => {
    setRows((cur) => ({ ...cur, ...Object.fromEntries(list.map((e) => [e.id, e])) }))
    return list.map((e) => ({ value: e.id, label: labelOf(e) }))
  }
  const merge = (cur: Option[], add: Option[]) => [...add, ...cur.filter((o) => !add.some((a) => a.value === o.value))]

  // denumirile celor aleși care nu sunt în listă (forma deschisă pentru corectare)
  const missing = chosen.filter((id) => !options.some((o) => o.value === id))
  useEffect(() => {
    if (!missing.length) return
    if (label && !Array.isArray(value) && value) {
      setOptions((cur) => merge(cur, [{ value, label }]))
      return
    }
    api.get<Paged<EmployeeRow>>('/staff/employees/', { params: { ids: missing.join(','), status: 'all', page_size: 100 } })
      .then(({ data }) => setOptions((cur) => merge(cur, remember(data.results))))
      .catch(() => undefined)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [missing.join(','), label])

  const search = async (q: string) => {
    if (q.length < 2) return
    const { data } = await api.get<Paged<EmployeeRow>>('/staff/employees/', { params: { q, status: 'all', page_size: 30 } })
    const found = remember(data.results)
    setOptions((cur) => [...cur.filter((o) => chosen.includes(o.value) && !found.some((f) => f.value === o.value)), ...found])
  }
  const emit = (v: number | number[] | null) => {
    const ids = Array.isArray(v) ? v : v ? [v] : []
    onChange?.(v, ids.map((id) => rows[id]).filter(Boolean))
  }
  const pick = (row: EmployeeRow) => {
    setOptions((cur) => merge(cur, remember([row])))
    if (mode === 'multiple') emit(chosen.includes(row.id) ? chosen : [...chosen, row.id])
    else emit(row.id)
    if (mode !== 'multiple') setListOpen(false)
  }

  return (
    <>
      <Space.Compact style={{ width: '100%', ...style }}>
        <Select<number | number[]> showSearch filterOption={false} allowClear={allowClear} disabled={disabled} mode={mode}
          placeholder={placeholder ?? t('empPicker.typeOrPick')} value={value ?? undefined} options={options} style={{ width: '100%' }}
          onSearch={search} notFoundContent={null} onChange={(v) => emit(v ?? null)} />
        <Tooltip title={t('empPicker.open')}>
          <Button icon={<EllipsisOutlined />} disabled={disabled} onClick={() => setListOpen(true)} aria-label={t('empPicker.open')} />
        </Tooltip>
      </Space.Compact>
      <EmployeePicker open={listOpen} multiple={mode === 'multiple'} chosen={chosen} onPick={pick} onClose={() => setListOpen(false)} />
    </>
  )
}

/** Fereastra cu lista angajaților: căutare, subdiviziunea (cu cele de sub ea), cei care lucrează acum sau toți; clic pe rând
 *  = alege (la alegerea mai multora fereastra rămâne deschisă, cei aleși sunt bifați). */
function EmployeePicker({ open, multiple, chosen, onPick, onClose }: {
  open: boolean
  multiple: boolean
  chosen: number[]
  onPick: (row: EmployeeRow) => void
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [subdivision, setSubdivision] = useState<number | null>(null)
  const [status, setStatus] = useState<'current' | 'all'>('current')
  const [page, setPage] = useState(1)
  useEffect(() => {
    if (open) { setQ(''); setPage(1) }
  }, [open])
  const { data, loading } = useFetch<Paged<EmployeeRow>>(open ? '/staff/employees/' : null,
    { q: q || undefined, subdivision: subdivision ?? undefined, status, page, page_size: 15 })
  return (
    <Modal open={open} title={t('empPicker.title')} onCancel={onClose} width="min(1100px, 96vw)" destroyOnHidden
      footer={multiple ? <Button type="primary" onClick={onClose}>{t('empPicker.done', { count: chosen.length })}</Button> : null}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search autoFocus allowClear placeholder={t('empPicker.search')} style={{ width: 300 }}
          onSearch={(v) => { setQ(v); setPage(1) }} onChange={(e) => { if (!e.target.value) { setQ(''); setPage(1) } }} />
        <SubdivisionSelect value={subdivision} style={{ width: 320 }} placeholder={t('org.subdivision')}
          onChange={(v) => { setSubdivision(typeof v === 'number' ? v : null); setPage(1) }} />
        <Segmented value={status} onChange={(v) => { setStatus(v as 'current' | 'all'); setPage(1) }}
          options={[{ value: 'current', label: t('empPicker.current') }, { value: 'all', label: t('empPicker.all') }]} />
      </Space>
      <Table<EmployeeRow> size="small" rowKey="id" loading={loading} dataSource={data?.results} scroll={{ x: 'max-content' }} noSettings
        pagination={{ current: page, total: data?.count, pageSize: 15, onChange: setPage, showSizeChanger: false }}
        rowClassName={(r) => (chosen.includes(r.id) ? 'ant-table-row-selected' : '')}
        onRow={(row) => ({ onClick: () => onPick(row), style: { cursor: 'pointer' } })}
        columns={[
          { title: t('empPicker.tab'), dataIndex: 'tab_number', width: 90 },
          { title: t('empPicker.name'), dataIndex: 'full_name', width: 260 },
          { title: t('org.subdivision'), dataIndex: 'subdivision', width: 240, ellipsis: true },
          { title: t('empPicker.occupation'), dataIndex: 'occupation', width: 240, ellipsis: true },
          { title: t('empPicker.status'), dataIndex: 'status_label', width: 120,
            render: (v: string, r) => <Tag color={STATUS_COLOR[r.status]}>{v}</Tag> },
        ]} />
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t(multiple ? 'empPicker.hintMany' : 'empPicker.hint')}</Typography.Text>
    </Modal>
  )
}

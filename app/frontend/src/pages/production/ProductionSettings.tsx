import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, DatePicker, Form, InputNumber, Modal, Select, Space, Tag, Tooltip, Typography, type FormInstance } from 'antd'
import { DeleteOutlined, PlusOutlined, ProfileOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import EmployeeSelect from '../../components/EmployeeSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import { useFetch } from '../../api/hooks'
import type { Employment } from '../../api/staff'
import { UNITS, type BrigadeMember, type Operation, type TariffGrid, type TariffRank } from '../../api/production'
import { useApp } from '../../auth/AppContext'

export const num = (v: unknown, digits = 4) =>
  v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('ro-MD', { maximumFractionDigits: digits })

/** Raportul de muncă al angajatului ales (gol — încă neales): felul și funcția. */
export function JobSelect({ employee, value, onChange, disabled, width = 230 }: {
  employee: number | null | undefined; value: number | null | undefined; onChange: (v: number | null) => void; disabled?: boolean; width?: number
}) {
  const { t } = useTranslation()
  const { data: jobs } = useFetch<Employment[]>(employee ? '/staff/employments/' : null, { employee })
  const active = (jobs ?? []).filter((j) => j.status !== 'ended' || j.id === value)
  return <Select style={{ width }} disabled={disabled || !employee} value={value ?? undefined} placeholder={t('prod.job')}
    onChange={(v) => onChange(v ?? null)}
    options={active.map((j) => ({ value: j.id, label: `${t(`staff.kinds.${j.kind}`, { defaultValue: j.kind_label })}: ${j.occupation_name}` }))} />
}

/** Angajatul și raportul lui de muncă; la un singur raport activ se alege singur. */
export function PersonJob({ employee, employeeName, employment, onChange, disabled }: {
  employee: number | null | undefined; employeeName?: string; employment: number | null | undefined
  onChange: (patch: { employee: number | null; employment: number | null; employee_name?: string }) => void; disabled?: boolean
}) {
  const [person, setPerson] = useState<number | null>(employee ?? null)
  const { data: jobs } = useFetch<Employment[]>(person && !employment ? '/staff/employments/' : null, { employee: person })
  const active = (jobs ?? []).filter((j) => j.status !== 'ended')
  const single = person && !employment && active.length === 1 ? active[0].id : null
  useEffect(() => {
    if (single) onChange({ employee: person, employment: single })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- doar când apare singurul raport al angajatului ales
  }, [single])
  return (
    <Space size={4} wrap>
      <EmployeeSelect value={person} label={employeeName} disabled={disabled} style={{ width: 240 }}
        onChange={(v, rows) => {
          const id = (v as number | null) ?? null
          setPerson(id)
          onChange({ employee: id, employment: null, employee_name: rows?.find((r) => r.id === id)?.full_name })
        }} />
      <JobSelect employee={person} value={employment} disabled={disabled} onChange={(v) => onChange({ employee: person, employment: v })} />
    </Space>
  )
}

/** Categoriile grilei: categoria, coeficientul, tariful scris direct (gol — categoria I × coeficientul). */
function RanksInput({ value, onChange, form }: { value?: TariffRank[]; onChange?: (v: TariffRank[]) => void; form: FormInstance }) {
  const { t } = useTranslation()
  const base = Number(Form.useWatch('base_rate', form)) || undefined
  const rows = value ?? []
  const set = (i: number, patch: Partial<TariffRank>) => onChange?.(rows.map((r, k) => (k === i ? { ...r, ...patch } : r)))
  const next = rows.length ? Math.max(...rows.map((r) => Number(r.rank) || 0)) + 1 : 1
  return (
    <Space orientation="vertical" size={4} style={{ width: '100%' }}>
      {rows.map((r, i) => {
        const hourly = r.rate !== null && r.rate !== '' && r.rate !== undefined ? Number(r.rate) : base ? base * Number(r.coefficient || 0) : null
        return (
          <Space key={r.id ?? `n${i}`} size={4} wrap>
            <InputNumber min={1} max={30} style={{ width: 110 }} prefix={t('prod.grid.rankShort')} value={Number(r.rank)} onChange={(v) => set(i, { rank: Number(v) })} />
            <InputNumber min={0.001} step={0.01} style={{ width: 150 }} prefix="×" value={r.coefficient as number} onChange={(v) => set(i, { coefficient: v ?? 1 })} />
            <InputNumber min={0} style={{ width: 200 }} placeholder={t('prod.grid.rateDirect')} suffix="lei/oră" value={r.rate as number | null}
              onChange={(v) => set(i, { rate: v ?? null })} />
            {hourly !== null && <Tag color="blue">{num(hourly, 2)} lei/oră</Tag>}
            <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange?.(rows.filter((_x, k) => k !== i))} />
          </Space>
        )
      })}
      <Button size="small" icon={<PlusOutlined />} onClick={() => onChange?.([...rows, { rank: next, coefficient: 1, rate: null }])}>{t('prod.grid.addRank')}</Button>
    </Space>
  )
}

/** Membrii brigăzii: angajatul (raportul de muncă), coeficientul de participare, perioada în brigadă. */
function MembersInput({ value, onChange }: { value?: BrigadeMember[]; onChange?: (v: BrigadeMember[]) => void }) {
  const { t } = useTranslation()
  const rows = value ?? []
  const set = (i: number, patch: Partial<BrigadeMember>) => onChange?.(rows.map((r, k) => (k === i ? { ...r, ...patch } : r)))
  return (
    <Space orientation="vertical" size={6} style={{ width: '100%' }}>
      {rows.map((r, i) => (
        <Space key={r.id ?? `n${i}`} size={4} wrap style={{ padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6 }}>
          <PersonJob employee={r.employee} employeeName={r.employee_name} employment={r.employment} onChange={(p) => set(i, p)} />
          <Tooltip title={t('prod.ktuHint')}><InputNumber min={0} max={10} step={0.1} style={{ width: 120 }} prefix="KTU" value={r.coefficient as number}
            onChange={(v) => set(i, { coefficient: v ?? 1 })} /></Tooltip>
          <DatePicker format="DD.MM.YYYY" placeholder={t('prod.brig.from')} value={r.date_from ? dayjs(r.date_from) : null}
            onChange={(d) => set(i, { date_from: d ? d.format('YYYY-MM-DD') : null })} />
          <DatePicker format="DD.MM.YYYY" placeholder={t('prod.brig.to')} value={r.date_to ? dayjs(r.date_to) : null}
            onChange={(d) => set(i, { date_to: d ? d.format('YYYY-MM-DD') : null })} />
          <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange?.(rows.filter((_x, k) => k !== i))} />
        </Space>
      ))}
      <Button size="small" icon={<PlusOutlined />} onClick={() => onChange?.([...rows, { employment: null, coefficient: 1, date_from: dayjs().format('YYYY-MM-DD'), date_to: null }])}>
        {t('prod.brig.addMember')}</Button>
    </Space>
  )
}

/** Normele și tarifele lucrării, cu istoric (din data dată). */
function RatesDialog({ op, onClose }: { op: Operation; onClose: () => void }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const { data: grids } = useFetch<TariffGrid[]>('/production/tariff-grids/')
  const codes = [...new Set((grids ?? []).filter((g) => !g.deletion_mark).map((g) => g.code))]
  const fields: CrudField[] = [
    { key: 'date_from', label: t('prod.op.dateFrom'), type: 'date', required: true, width: 110 },
    { key: 'norm_kind', label: t('prod.op.normKind'), type: 'select', required: true, width: 190, extra: t('prod.op.normKindHint'),
      options: ['time', 'output'].map((k) => ({ value: k, label: t(`prod.op.normKinds.${k}`) })) },
    { key: 'norm_value', label: t('prod.op.normValue'), type: 'number', required: true, width: 110 },
    { key: 'grid_code', label: t('prod.op.grid'), type: 'select', width: 110, options: codes.map((c) => ({ value: c, label: c })) },
    { key: 'rank', label: t('prod.op.rank'), type: 'number', width: 90 },
    { key: 'piece_rate', label: t('prod.op.pieceRate'), type: 'number', width: 130, extra: t('prod.op.pieceRateHint') },
    { key: 'document', label: t('prod.op.document'), inTable: false },
    { key: 'price', label: t('prod.op.price'), display: true,
      render: (v) => {
        const p = v as { rate: string | null; how: string } | null
        return p?.rate !== null && p?.rate !== undefined ? <Tooltip title={p.how}><b>{num(p.rate)} lei</b></Tooltip>
          : <Typography.Text type="danger">{p?.how}</Typography.Text>
      } },
  ]
  return (
    <Modal open onCancel={onClose} footer={null} width={1000} title={`${t('prod.op.rates')}: ${op.code} — ${op.name_ro}`}>
      <CrudTable endpoint="/production/operation-rates/" params={{ operation: op.id }} fields={fields} canEdit={hasPerm('production.edit')}
        defaults={{ operation: op.id, norm_kind: 'time', date_from: dayjs().startOf('month').format('YYYY-MM-DD') }}
        title={<Typography.Text type="secondary">{t('prod.op.ratesHint')}</Typography.Text>} />
    </Modal>
  )
}

export type ProductionPart = 'grids' | 'operations' | 'brigades'

/** Setările producției (Administrare → Setări): grila tarifară, lucrările în acord, brigăzile. */
export default function ProductionSettingsPage({ part, title }: { part: ProductionPart; title: string }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('production.edit')
  const [rates, setRates] = useState<Operation | null>(null)
  const [tick, setTick] = useState(0)

  const gridFields: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 90, extra: t('prod.grid.codeHint') },
    { key: 'name', label: t('prod.grid.name'), required: true },
    { key: 'date_from', label: t('prod.op.dateFrom'), type: 'date', required: true, width: 110 },
    { key: 'base_rate', label: t('prod.grid.baseRate'), type: 'number', required: true, width: 150 },
    { key: 'ranks', label: t('prod.grid.ranks'), extra: t('prod.grid.ranksHint'),
      input: (form) => <RanksInput form={form} />,
      render: (v) => (v as TariffRank[]).map((r) => <Tag key={r.rank}>{r.rank}: {num(r.hourly, 2)}</Tag>) },
    { key: 'document', label: t('prod.grid.document'), inTable: false },
    { key: 'note', label: t('org.notes'), inTable: false },
  ]
  const opFields: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 100 },
    { key: 'name_ro', label: t('org.nameRo'), required: true },
    { key: 'name_ru', label: t('org.nameRu'), inTable: false },
    { key: 'name_en', label: t('org.nameEn'), inTable: false },
    { key: 'unit', label: t('prod.op.unit'), type: 'select', required: true, width: 90, options: UNITS.map((u) => ({ value: u, label: t(`prod.units.${u}`) })) },
    { key: 'subdivision', label: t('prod.op.subdivision'), inTable: false, input: () => <SubdivisionSelect /> },
    { key: 'progressive', label: t('prod.op.progressive'), type: 'bool', width: 100, extra: t('prod.op.progressiveHint') },
    { key: 'current', label: t('prod.op.current'), display: true, width: 230,
      render: (v) => {
        const c = v as Operation['current']
        if (!c) return <Typography.Text type="warning">{t('prod.op.noRate')}</Typography.Text>
        return c.rate !== null ? <Tooltip title={c.how}>{num(c.rate)} lei · {t(`prod.op.normShort.${c.norm_kind}`, { v: num(c.norm_value) })}</Tooltip>
          : <Typography.Text type="danger">{c.how}</Typography.Text>
      } },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
    { key: 'note', label: t('org.notes'), inTable: false },
    { key: 'sort', label: t('org.sort'), type: 'number', inTable: false },
  ]
  const brigadeFields: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 90 },
    { key: 'name', label: t('prod.brig.name'), required: true },
    { key: 'subdivision', label: t('prod.op.subdivision'), input: () => <SubdivisionSelect />, render: (_v, r) => String(r.subdivision_name ?? '') },
    { key: 'distribution', label: t('prod.brig.distribution'), type: 'select', required: true, width: 230, extra: t('prod.brig.distributionHint'),
      options: ['hours', 'tariff'].map((k) => ({ value: k, label: t(`prod.brig.distributions.${k}`) })) },
    { key: 'members', label: t('prod.brig.members'), input: () => <MembersInput />,
      render: (v) => String((v as BrigadeMember[]).filter((m) => !m.date_to || dayjs(m.date_to).isAfter(dayjs())).length) },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
    { key: 'note', label: t('org.notes'), inTable: false },
  ]
  const parts: Record<ProductionPart, React.ReactNode> = {
    grids: <CrudTable endpoint="/production/tariff-grids/" fields={gridFields} canEdit={canEdit} modalWidth={760}
      defaults={{ ranks: [{ rank: 1, coefficient: 1, rate: null }], date_from: dayjs().startOf('year').format('YYYY-MM-DD') }}
      title={<Typography.Text type="secondary">{t('prod.grid.hint')}</Typography.Text>} />,
    operations: <CrudTable key={tick} endpoint="/production/operations/" fields={opFields} canEdit={canEdit} search
      defaults={{ unit: 'buc', progressive: false, sort: 100 }}
      rowActions={(row) => <Button size="small" icon={<ProfileOutlined />} onClick={() => setRates(row as unknown as Operation)}>{t('prod.op.rates')}</Button>}
      title={<Typography.Text type="secondary">{t('prod.op.hint')}</Typography.Text>} />,
    brigades: <CrudTable endpoint="/production/brigades/" fields={brigadeFields} canEdit={canEdit} modalWidth={1000}
      defaults={{ distribution: 'hours', members: [] }}
      title={<Typography.Text type="secondary">{t('prod.brig.hint')}</Typography.Text>} />,
  }
  return (
    <Card title={title}>
      {parts[part]}
      {rates && <RatesDialog op={rates} onClose={() => { setRates(null); setTick((n) => n + 1) }} />}
    </Card>
  )
}

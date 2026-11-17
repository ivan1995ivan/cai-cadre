import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Checkbox, Input, Select, Space, Typography } from 'antd'
import { DeleteOutlined, FileTextOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import PrintDialog from '../../components/PrintDialog'
import { useFetch } from '../../api/hooks'
import type { Dependent, PayType } from '../../api/payroll'
import type { Employment } from '../../api/staff'
import { useApp, useLocalName } from '../../auth/AppContext'

/** Persoanele întreținute din cererea de scutire (nume, IDNP, dizabilitate). */
function DependentsInput({ value, onChange }: { value?: Dependent[]; onChange?: (v: Dependent[]) => void }) {
  const { t } = useTranslation()
  const rows = value ?? []
  const set = (i: number, patch: Partial<Dependent>) => onChange?.(rows.map((r, k) => (k === i ? { ...r, ...patch } : r)))
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={4}>
      {rows.map((r, i) => (
        <Space key={i} wrap>
          <Input style={{ width: 220 }} placeholder={t('staff.fullName')} value={r.name} onChange={(e) => set(i, { name: e.target.value })} />
          <Input style={{ width: 150 }} placeholder="IDNP" value={r.idnp} onChange={(e) => set(i, { idnp: e.target.value })} />
          <Checkbox checked={r.disabled} onChange={(e) => set(i, { disabled: e.target.checked })}>{t('pay.ex.disabled')}</Checkbox>
          <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange?.(rows.filter((_x, k) => k !== i))} />
        </Space>
      ))}
      <Button size="small" icon={<PlusOutlined />} onClick={() => onChange?.([...rows, { name: '', idnp: '', disabled: false }])}>{t('pay.ex.addDependent')}</Button>
    </Space>
  )
}

/** Fila „Salariu” din fișa angajatului: cererea de scutire și sporurile / reținerile personale. */
export default function PayTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const localName = useLocalName()
  const { data: types } = useFetch<PayType[]>('/payroll/types/', { active: 1, personal: 1 })
  const { data: jobs } = useFetch<Employment[]>('/staff/employments/', { employee })
  const [year] = useState(dayjs().year())
  const [cardYear, setCardYear] = useState(dayjs().year())
  const [cardOpen, setCardOpen] = useState(false)
  const canEdit = hasPerm('payroll.edit')
  const typeOptions = (types ?? []).map((x) => ({ value: x.id, label: `${x.code} — ${localName(x)} (${x.category_label})` }))
  const jobOptions = (jobs ?? []).filter((j) => j.status !== 'ended').map((j) => ({ value: j.id, label: `${j.kind_label}: ${j.occupation_name}, ${j.subdivision_name}` }))

  const exemptionFields: CrudField[] = [
    { key: 'employee', label: '', hidden: true },
    { key: 'year', label: t('lv.sch.year'), type: 'number', required: true, width: 70 },
    { key: 'date', label: t('pay.ex.date'), type: 'date', required: true, width: 110 },
    { key: 'kind', label: t('pay.ex.kind'), type: 'select', required: true, width: 220,
      options: ['personal', 'major', 'none'].map((k) => ({ value: k, label: t(`pay.ex.kinds.${k}`) })) },
    { key: 'spouse', label: t('pay.ex.spouse'), type: 'bool', width: 90 },
    { key: 'spouse_name', label: t('pay.ex.spouseName'), inTable: false },
    { key: 'spouse_idnp', label: t('pay.ex.spouseIdnp'), inTable: false, extra: t('pay.ex.spouseIdnpHint') },
    { key: 'dependents', label: t('pay.ex.dependents'), input: () => <DependentsInput />, render: (v) => String((v as Dependent[])?.length || '') , width: 90 },
    { key: 'code', label: t('pay.ex.code'), width: 80, render: (v) => <b>{String(v ?? '')}</b> },
    { key: 'documents', label: t('pay.ex.documents'), inTable: false },
    { key: 'date_from', label: t('pay.ex.dateFrom'), type: 'date', inTable: false, extra: t('pay.ex.dateFromHint') },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 70 },
  ]
  const itemFields: CrudField[] = [
    { key: 'employee', label: '', hidden: true },
    { key: 'pay_type', label: t('pay.item'), type: 'select', required: true, options: typeOptions, render: (_v, r) => String(r.pay_type_name ?? '') },
    { key: 'employment', label: t('ord.p.employment'), type: 'select', options: jobOptions, inTable: false, extra: t('ord.p.employmentHint') },
    { key: 'amount', label: t('pay.amount'), type: 'number', width: 110, render: (v) => (v ? Number(v).toLocaleString('ro-MD') : '') },
    { key: 'percent', label: '%', type: 'number', width: 70 },
    { key: 'date_from', label: t('staff.sen.from'), type: 'date', required: true, width: 110 },
    { key: 'date_to', label: t('staff.sen.to'), type: 'date', width: 110 },
    { key: 'document', label: t('pay.itemDocument'), width: 220 },
    { key: 'note', label: t('org.notes'), inTable: false },
  ]

  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={20}>
      <Space wrap>
        <Typography.Text strong>{t('pp.annualCard')}</Typography.Text>
        <Select size="small" style={{ width: 90 }} value={cardYear} onChange={setCardYear}
          options={Array.from({ length: 5 }, (_, i) => dayjs().year() - i).map((y) => ({ value: y, label: y }))} />
        <Button size="small" icon={<FileTextOutlined />} onClick={() => setCardOpen(true)}>{t('lv.print')}</Button>
      </Space>
      {cardOpen && <PrintDialog open onClose={() => setCardOpen(false)} docType="annual_card" url={`/payroll/annual-card/${employee}/`}
        params={{ year: cardYear, print: 1 }} optionKeys={[]} title={t('pp.annualCard')} />}
      <CrudTable endpoint="/payroll/exemptions/" params={{ employee }} canEdit={canEdit} fields={exemptionFields}
        defaults={{ employee, year, kind: 'personal', spouse: false, dependents: [], is_active: true, date: dayjs().format('YYYY-MM-DD') }}
        title={<Space orientation="vertical" size={0}><Typography.Text strong>{t('pay.ex.title')}</Typography.Text>
          <Typography.Text type="secondary">{t('pay.ex.hint')}</Typography.Text></Space>} />
      <CrudTable endpoint="/payroll/employee-items/" params={{ employee }} canEdit={canEdit} fields={itemFields}
        defaults={{ employee, date_from: dayjs().startOf('month').format('YYYY-MM-DD') }}
        title={<Space orientation="vertical" size={0}><Typography.Text strong>{t('pay.items.title')}</Typography.Text>
          <Typography.Text type="secondary">{t('pay.items.hint')}</Typography.Text></Space>} />
    </Space>
  )
}

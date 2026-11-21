import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Checkbox, DatePicker, Input, Select, Space, Tag, Typography } from 'antd'
import { DeleteOutlined, FileTextOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import PrintDialog from '../../components/PrintDialog'
import { useFetch } from '../../api/hooks'
import type { Dependent, PayType } from '../../api/payroll'
import type { Employment } from '../../api/staff'
import { useApp, useLocalName } from '../../auth/AppContext'

type FamilyRow = { id: number; full_name: string; idnp: string; birth_date: string | null; relation_name: string; disabled: boolean }
const RELATIONS = ['child', 'parent', 'sibling', 'other'] as const
const DISABILITIES = ['', 'childhood', 'severe', 'accentuated', 'medium'] as const
const H_DISABILITY = new Set(['childhood', 'severe', 'accentuated'])
const blank = (): Dependent => ({ family_member: null, name: '', idnp: '', birth_date: null, relation: 'child', disability: '',
  date_from: null, date_to: null, document: '', income_ok: true })

/** Persoanele întreținute din cererea de scutire (CF art. 35): rânduri cu rudenia, dizabilitatea (→ H), perioada dreptului,
 * documentul și venitul sub plafon; alegerea din „Familia” din dosar completează rândul. */
function DependentsInput({ value, onChange, employee }: { value?: Dependent[]; onChange?: (v: Dependent[]) => void; employee: number }) {
  const { t } = useTranslation()
  const { data: family } = useFetch<FamilyRow[]>('/staff/family/', { employee })
  const rows = value ?? []
  const set = (i: number, patch: Partial<Dependent>) => onChange?.(rows.map((r, k) => (k === i ? { ...r, ...patch } : r)))
  const pick = (i: number, id: number | null) => {
    const f = (family ?? []).find((x) => x.id === id)
    if (!f) { set(i, { family_member: null }); return }
    const rel = /fiu|fiic|son|daughter|сын|доч/i.test(f.relation_name) ? 'child' : /mam|tat|mother|father|мать|отец/i.test(f.relation_name) ? 'parent' : rows[i].relation
    set(i, { family_member: f.id, name: f.full_name, idnp: f.idnp, birth_date: f.birth_date, relation: rel,
      disability: f.disabled && !rows[i].disability ? 'severe' : rows[i].disability })
  }
  const date = (v: string | null) => (v ? dayjs(v) : null)
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={6}>
      {rows.map((r, i) => (
        <Space key={r.id ?? `n${i}`} wrap size={4} style={{ padding: 6, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6 }}>
          <Tag color={H_DISABILITY.has(r.disability) ? 'purple' : 'blue'}>{H_DISABILITY.has(r.disability) ? 'H' : 'N'}</Tag>
          <Select allowClear style={{ width: 190 }} placeholder={t('pay.ex2.fromFamily')} value={r.family_member ?? undefined}
            onChange={(v) => pick(i, v ?? null)} options={(family ?? []).map((f) => ({ value: f.id, label: `${f.full_name} (${f.relation_name})` }))} />
          <Input style={{ width: 200 }} placeholder={t('staff.fullName')} value={r.name} onChange={(e) => set(i, { name: e.target.value })} />
          <Input style={{ width: 140 }} placeholder="IDNP" value={r.idnp} onChange={(e) => set(i, { idnp: e.target.value })} />
          <DatePicker style={{ width: 130 }} format="DD.MM.YYYY" placeholder={t('pay.ex2.birthDate')} value={date(r.birth_date)}
            onChange={(d) => set(i, { birth_date: d ? d.format('YYYY-MM-DD') : null })} />
          <Select style={{ width: 170 }} value={r.relation} onChange={(v) => set(i, { relation: v })}
            options={RELATIONS.map((k) => ({ value: k, label: t(`pay.ex2.rel.${k}`) }))} />
          <Select style={{ width: 200 }} value={r.disability} onChange={(v) => set(i, { disability: v })}
            options={DISABILITIES.map((k) => ({ value: k, label: t(`pay.ex2.dis.${k || 'none'}`) }))} />
          <DatePicker style={{ width: 150 }} format="DD.MM.YYYY" placeholder={t('pay.ex2.rightFrom')} value={date(r.date_from)}
            onChange={(d) => set(i, { date_from: d ? d.format('YYYY-MM-DD') : null })} />
          <DatePicker style={{ width: 150 }} format="DD.MM.YYYY" placeholder={t('pay.ex2.rightTo')} value={date(r.date_to)}
            onChange={(d) => set(i, { date_to: d ? d.format('YYYY-MM-DD') : null })} />
          <Input style={{ width: 260 }} placeholder={t('pay.ex2.document')} value={r.document} onChange={(e) => set(i, { document: e.target.value })} />
          <Checkbox checked={r.income_ok} onChange={(e) => set(i, { income_ok: e.target.checked })}>{t('pay.ex2.incomeOk')}</Checkbox>
          <Button size="small" type="text" danger icon={<DeleteOutlined />} onClick={() => onChange?.(rows.filter((_x, k) => k !== i))} />
        </Space>
      ))}
      <Button size="small" icon={<PlusOutlined />} onClick={() => onChange?.([...rows, blank()])}>{t('pay.ex.addDependent')}</Button>
      <Typography.Text type="secondary">{t('pay.ex2.dependentsHint')}</Typography.Text>
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
  const [printReq, setPrintReq] = useState<number | null>(null)
  const [cardYear, setCardYear] = useState(dayjs().year())
  const [cardOpen, setCardOpen] = useState(false)
  const canEdit = hasPerm('payroll.edit')
  const typeOptions = (types ?? []).map((x) => ({ value: x.id, label: `${x.code} — ${localName(x)} (${x.category_label})` }))
  const jobOptions = (jobs ?? []).filter((j) => j.status !== 'ended').map((j) => ({ value: j.id, label: `${j.kind_label}: ${j.occupation_name}, ${j.subdivision_name}` }))

  const categories = 'abcdef'.split('').map((c) => ({ value: c, label: t('pay.ex2.category', { c }) }))
  const exemptionFields: CrudField[] = [
    { key: 'employee', label: '', hidden: true },
    { key: 'date', label: t('pay.ex.date'), type: 'date', required: true, width: 105 },
    { key: 'number', label: t('pay.ex2.number'), inTable: false },
    { key: 'kind', label: t('pay.ex.kind'), type: 'select', required: true, width: 150,
      options: ['personal', 'major', 'none'].map((k) => ({ value: k, label: t(`pay.ex.kinds.${k}`) })) },
    { key: 'major_category', label: t('pay.ex2.majorCategory'), type: 'select', options: categories, inTable: false, extra: t('pay.ex2.majorHint') },
    { key: 'major_document', label: t('pay.ex2.majorDocument'), inTable: false },
    { key: 'spouse_major', label: t('pay.ex2.spouseMajor'), type: 'bool', inTable: false, extra: t('pay.ex2.spouseMajorHint') },
    { key: 'spouse_name', label: t('pay.ex2.spouseName'), inTable: false },
    { key: 'spouse_idnp', label: t('pay.ex.spouseIdnp'), inTable: false, extra: t('pay.ex.spouseIdnpHint') },
    { key: 'spouse_category', label: t('pay.ex2.spouseCategory'), type: 'select', options: categories, inTable: false },
    { key: 'spouse_document', label: t('pay.ex2.spouseDocument'), inTable: false },
    { key: 'dependents', label: t('pay.ex.dependents'), input: () => <DependentsInput employee={employee} />,
      render: (v) => String((v as Dependent[])?.length || ''), width: 90 },
    { key: 'code', label: t('pay.ex.code'), display: true, width: 90, render: (v) => <b>{String(v ?? '')}</b> },
    { key: 'code_now', label: t('pay.ex2.codeNow'), display: true, width: 110, render: (v) => (v ? <Tag color="green">{String(v)}</Tag> : '—') },
    { key: 'date_from', label: t('pay.ex.dateFrom'), type: 'date', width: 105, extra: t('pay.ex2.dateFromHint') },
    { key: 'date_to', label: t('pay.ex2.dateTo'), type: 'date', width: 105, extra: t('pay.ex2.dateToHint') },
    { key: 'waiver_date', label: t('pay.ex2.waiver'), type: 'date', inTable: false, extra: t('pay.ex2.waiverHint') },
    { key: 'documents', label: t('pay.ex.documents'), inTable: false },
    { key: 'needs_review', label: t('pay.ex2.needsReview'), type: 'bool', inTable: false },
    { key: 'warnings', label: '', display: true, render: (v) => ((v as string[]) ?? []).map((w) => <Typography.Text key={w} type="warning" style={{ display: 'block' }}>{w}</Typography.Text>) },
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
      {printReq && <PrintDialog open onClose={() => setPrintReq(null)} docType="exemption_request" url={`/payroll/exemptions/${printReq}/print/`}
        params={{}} optionKeys={[]} title={t('pay.ex.title')} />}
      <CrudTable endpoint="/payroll/exemptions/" params={{ employee }} canEdit={canEdit} fields={exemptionFields} modalWidth={1100}
        rowActions={(row) => <Button size="small" icon={<FileTextOutlined />} onClick={() => setPrintReq(Number(row.id))}>{t('lv.print')}</Button>}
        defaults={{ employee, kind: 'personal', spouse_major: false, dependents: [], is_active: true, date: dayjs().format('YYYY-MM-DD') }}
        title={<Space orientation="vertical" size={0}><Typography.Text strong>{t('pay.ex.title')}</Typography.Text>
          <Typography.Text type="secondary">{t('pay.ex.hint')}</Typography.Text></Space>} />
      <CrudTable endpoint="/payroll/employee-items/" params={{ employee }} canEdit={canEdit} fields={itemFields}
        defaults={{ employee, date_from: dayjs().startOf('month').format('YYYY-MM-DD') }}
        title={<Space orientation="vertical" size={0}><Typography.Text strong>{t('pay.items.title')}</Typography.Text>
          <Typography.Text type="secondary">{t('pay.items.hint')}</Typography.Text></Space>} />
    </Space>
  )
}

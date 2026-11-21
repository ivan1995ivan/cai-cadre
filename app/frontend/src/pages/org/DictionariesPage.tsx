import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, Modal, Tag, Tooltip, Typography } from 'antd'
import { WalletOutlined } from '@ant-design/icons'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import ExcelImport from '../../components/ExcelImport'
import { useFetch, invalidateCache } from '../../api/hooks'
import type { OrgMeta } from '../../api/org'
import { useDict } from '../../api/staff'
import { useApp } from '../../auth/AppContext'
import { usePersonalTypes } from '../payroll/PlannedRows'

/** Acumulările-tip ale funcției: la angajare completează tabelul „Acumulări și rețineri” din ordin (se corectează acolo). */
function OccupationPayItems({ occupation, name, onClose, canEdit }: { occupation: number; name: string; onClose: () => void; canEdit: boolean }) {
  const { t } = useTranslation()
  const { options } = usePersonalTypes()
  const fields: CrudField[] = [
    { key: 'occupation', label: '', hidden: true },
    { key: 'pay_type', label: t('pay.item'), type: 'select', required: true, options, render: (_v, r) => `${r.pay_type_code} — ${r.pay_type_name}` },
    { key: 'amount', label: t('pay.amount'), type: 'number', width: 110 },
    { key: 'percent', label: '%', type: 'number', width: 80 },
    { key: 'quantity', label: t('pay.fx.quantity'), type: 'number', width: 100 },
    { key: 'sort', label: t('org.sort'), type: 'number', width: 80 },
  ]
  return (
    <Modal open onCancel={onClose} footer={null} width={900} title={`${t('pay.pl.occupationItems')} — ${name}`}>
      <CrudTable endpoint="/payroll/occupation-items/" params={{ occupation }} fields={fields} canEdit={canEdit}
        defaults={{ occupation, sort: 10 }} title={<Typography.Text type="secondary">{t('pay.pl.occupationItemsHint')}</Typography.Text>} />
    </Modal>
  )
}

/** Câmpurile de denumire, comune tuturor clasificatoarelor (RO / RU / EN). */
export function useNameFields(): CrudField[] {
  const { t } = useTranslation()
  const { languages } = useApp()
  return [
    { key: 'name_ro', label: t('org.nameRo'), required: true },
    ...(languages.includes('ru') ? [{ key: 'name_ru', label: t('org.nameRu'), inTable: false }] : []),
    ...(languages.includes('en') ? [{ key: 'name_en', label: t('org.nameEn'), inTable: false }] : []),
  ]
}

export function useEnumOptions() {
  const { t } = useTranslation()
  return (prefix: string, codes: string[] = []) => codes.map((c) => ({ value: c, label: t(`${prefix}.${c}`, { defaultValue: c }) }))
}

/**
 * Un clasificator (Administrare → Setări): funcțiile CORM, specialitățile, temeiurile legale, tipurile de ordine sau unul
 * dintre clasificatoarele mici (DictItem, după tip — `dict` e tipul lui).
 */
export default function DictionaryPage({ dict, title }: { dict: string; title: string }) {
  const { t } = useTranslation()
  const { hasPerm, languages } = useApp()
  const canEdit = hasPerm('dictionaries.edit')
  // listele de alegere (tipurile specialităților, grupele ordinelor) — doar la clasificatoarele care le au
  const { data: meta } = useFetch<OrgMeta>(['specialties', 'order-types'].includes(dict) ? '/org/meta/' : null)
  const staffCategories = useDict('staff_category')
  const names = useNameFields()
  const opts = useEnumOptions()
  const { branding } = useApp()
  const [payFor, setPayFor] = useState<{ id: number; name: string } | null>(null)
  const [reload, setReload] = useState(0)
  const refresh = (endpoint: string) => () => { invalidateCache(endpoint); setReload((n) => n + 1) }

  const common: CrudField[] = [
    { key: 'sort', label: t('org.sort'), type: 'number', inTable: false },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
  ]

  const occupations: CrudField[] = [
    { key: 'code', label: t('org.corm'), width: 110,
      render: (v) => v ? String(v) : <Tag color="orange">{t('org.noCode')}</Tag> },
    ...names,
    { key: 'category', label: t('org.category'), type: 'select', options: staffCategories, ref: { dict: 'staff_category' }, width: 240,
      render: (_v, r) => String(r.category_name ?? ''), extra: <Typography.Text type="secondary">{t('org.categoryAuto')}</Typography.Text> },
    { key: 'isco_code', label: 'ISCO-08', inTable: false },
    { key: 'weekly_hours', label: t('org.weeklyHours'), type: 'number', width: 90 },
    { key: 'base_leave_days', label: t('org.baseLeave'), type: 'number', inTable: false },
    { key: 'extra_leave_days', label: t('org.extraLeave'), type: 'number', width: 90 },
    { key: 'harmful', label: t('org.harmful'), type: 'bool', width: 90 },
    { key: 'notes', label: t('org.notes'), type: 'textarea', inTable: false },
    ...common,
  ]

  const specialties: CrudField[] = [
    { key: 'code', label: t('common.code'), width: 100 },
    ...names,
    { key: 'kind', label: t('org.kind'), type: 'select', options: opts('org.specKind', meta?.specialty_kinds), width: 180 },
    { key: 'isced', label: 'ISCED', width: 90 },
    ...common,
  ]

  const legal: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 110 },
    { key: 'reference', label: t('org.reference'), hidden: false, inTable: true, width: 260,
      input: () => <Typography.Text type="secondary">{t('org.referenceAuto')}</Typography.Text> },
    ...names,
    { key: 'act', label: t('org.act'), required: true, inTable: false },
    { key: 'article', label: t('org.article'), inTable: false },
    { key: 'paragraph', label: t('org.paragraph'), inTable: false },
    { key: 'letter', label: t('org.letter'), inTable: false },
    { key: 'text_ro', label: t('org.textRo'), type: 'textarea', inTable: false },
    { key: 'text_ru', label: t('org.textRu'), type: 'textarea', inTable: false },
    ...common,
  ]

  const { data: bases } = useFetch<{ id: number; code: string; reference: string; name_ro: string }[]>(dict === 'order-types' ? '/org/legal-bases/' : null)
  const orderTypes: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 150 },
    ...names,
    { key: 'group', label: t('org.group'), type: 'select', options: opts('org.orderGroup', meta?.order_groups), required: true, width: 190 },
    { key: 'register', label: t('org.register'), type: 'select', options: opts('org.registers', meta?.order_registers), required: true, inTable: false },
    { key: 'effect', label: t('org.effect'), type: 'select', options: opts('org.effects', meta?.order_effects), required: true, width: 200 },
    { key: 'legal_bases', label: t('org.legalBases'), type: 'multiselect', inTable: false,
      options: (bases ?? []).map((b) => ({ value: b.id, label: `${b.code} — ${b.name_ro}` })) },
    { key: 'title_ro', label: t('org.titleRo'), inTable: false },
    ...(languages.includes('ru') ? [{ key: 'title_ru', label: t('org.titleRu'), inTable: false }] : []),
    { key: 'point_template_ro', label: t('org.pointTemplate'), type: 'textarea', inTable: false,
      extra: <Typography.Text type="secondary">{t('org.pointTemplateHint')}</Typography.Text> },
    { key: 'collective', label: t('org.collective'), type: 'bool', inTable: false },
    { key: 'report_irm19', label: 'IRM19', type: 'bool', width: 70 },
    { key: 'payroll_effect', label: t('org.payrollEffect'), type: 'bool', inTable: false },
    { key: 'from_1c', label: '1C', width: 50, input: () => null,
      render: (v) => v ? <Tooltip title={t('org.from1c')}><Tag>1C</Tag></Tooltip> : null },
    ...common,
  ]

  const dictFields: CrudField[] = [
    { key: 'kind', label: t('org.kind'), hidden: true },
    { key: 'code', label: t('common.code'), width: 140 },
    ...names,
    ...common,
  ]

  const tables: Record<string, React.ReactNode> = {
    occupations: (
      <CrudTable key={`occ${reload}`} endpoint="/org/occupations/" fields={occupations} canEdit={canEdit}
        rowActions={branding?.payroll_enabled === false ? undefined : (row) => (
          <Tooltip title={t('pay.pl.occupationItems')}><Button size="small" icon={<WalletOutlined />}
            onClick={() => setPayFor({ id: Number(row.id), name: String(row.name_ro ?? '') })} /></Tooltip>)}
        defaults={{ category: null, weekly_hours: 40, base_leave_days: 28, extra_leave_days: 0 }}
        title={<Typography.Text type="secondary">{t('org.occupationsHint')}</Typography.Text>}
        extra={canEdit && <ExcelImport code="occupations" label={t('org.importCorm')} onDone={refresh('/org/occupations/')} />} />
    ),
    specialties: (
      <CrudTable key={`spec${reload}`} endpoint="/org/specialties/" fields={specialties} canEdit={canEdit} defaults={{ kind: 'other' }}
        extra={canEdit && <ExcelImport code="specialties" onDone={refresh('/org/specialties/')} />} />
    ),
    legal: (
      <CrudTable endpoint="/org/legal-bases/" fields={legal} canEdit={canEdit} defaults={{ act: 'Codul muncii nr. 154/2003' }}
        title={<Typography.Text type="secondary">{t('org.legalHint')}</Typography.Text>} />
    ),
    'order-types': (
      <CrudTable endpoint="/org/order-types/" fields={orderTypes} canEdit={canEdit}
        defaults={{ group: 'A', register: 'order_personnel', effect: 'none' }}
        title={<Typography.Text type="secondary">{t('org.orderTypesHint')}</Typography.Text>} />
    ),
  }

  return (
    <Card title={title}>
      {tables[dict] ?? (
        <CrudTable key={dict} endpoint="/org/dict-items/" params={{ kind: dict }} fields={dictFields} canEdit={canEdit} defaults={{ kind: dict }} />
      )}
      {payFor && <OccupationPayItems occupation={payFor.id} name={payFor.name} onClose={() => setPayFor(null)}
        canEdit={hasPerm('dictionaries.edit') || hasPerm('payroll_settings.edit')} />}
    </Card>
  )
}

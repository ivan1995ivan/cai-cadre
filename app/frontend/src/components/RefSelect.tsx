import { useMemo, useState, type CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Modal, Select, Space, Tooltip } from 'antd'
import { EllipsisOutlined } from '@ant-design/icons'

import { useFetch } from '../api/hooks'
import { useApp, useLocalName } from '../auth/AppContext'
import CrudTable, { type CrudField } from './CrudTable'

/** Ce clasificator: un tip din „Alte clasificatoare” (`{ dict: 'sanction' }`), funcțiile (CORM) sau specialitățile. */
export type RefSpec = { dict: string } | 'occupation' | 'specialty'

type Item = Record<string, unknown> & { id: number; code?: string; name_ro: string; name_ru?: string; name_en?: string; is_active?: boolean; deletion_mark?: boolean }

const SPEC_KINDS = ['higher', 'postsecondary', 'secondary', 'other']

function endpointOf(spec: RefSpec) {
  if (spec === 'occupation') return { endpoint: '/org/occupations/', params: {}, defaults: { category: null, weekly_hours: 40, base_leave_days: 28, extra_leave_days: 0 } }
  if (spec === 'specialty') return { endpoint: '/org/specialties/', params: {}, defaults: { kind: 'other' } }
  return { endpoint: '/org/dict-items/', params: { kind: spec.dict }, defaults: { kind: spec.dict } }
}

/**
 * Alegerea dintr-un clasificator, ca în 1C: lista derulantă cu căutare + butonul „…”, care deschide clasificatorul
 * (căutare, adăugare, corectare — pentru cine are dreptul); dublu clic sau „Alege” pune elementul în câmp.
 */
export default function RefSelect({ spec, value, onChange, allowClear = true, disabled, placeholder, style, mode }: {
  spec: RefSpec
  value?: number | number[] | null
  onChange?: (value: number | number[] | null) => void
  allowClear?: boolean
  disabled?: boolean
  placeholder?: string
  style?: CSSProperties
  mode?: 'multiple'
}) {
  const { t } = useTranslation()
  const { hasPerm, languages } = useApp()
  const localName = useLocalName()
  const [open, setOpen] = useState(false)
  const { endpoint, params, defaults } = endpointOf(spec)
  const { data, reload } = useFetch<Item[]>(endpoint, params)
  const label = (it: Item) => (spec === 'occupation' && it.code ? `${it.code} · ${localName(it)}` : localName(it))
  const options = useMemo(() => (data ?? []).filter((it) => (it.is_active !== false && !it.deletion_mark)
    || (Array.isArray(value) ? value.includes(it.id) : it.id === value)).map((it) => ({ value: it.id, label: label(it) })),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [data, value, localName])
  const names: CrudField[] = [
    { key: 'name_ro', label: t('org.nameRo'), required: true },
    ...(languages.includes('ru') ? [{ key: 'name_ru', label: t('org.nameRu'), inTable: false }] : []),
    ...(languages.includes('en') ? [{ key: 'name_en', label: t('org.nameEn'), inTable: false }] : []),
  ]
  const fields: CrudField[] = spec === 'occupation' ? [
    { key: 'code', label: t('org.corm'), width: 110 }, ...names,
    { key: 'category', label: t('org.category'), ref: { dict: 'staff_category' }, width: 220, render: (_v, r) => String(r.category_name ?? '') },
    { key: 'weekly_hours', label: t('org.weeklyHours'), type: 'number', inTable: false },
    { key: 'base_leave_days', label: t('org.baseLeave'), type: 'number', inTable: false },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
  ] : spec === 'specialty' ? [
    { key: 'code', label: t('common.code'), width: 110 }, ...names,
    { key: 'kind', label: t('org.kind'), type: 'select', options: SPEC_KINDS.map((k) => ({ value: k, label: t(`org.specKind.${k}`) })), width: 180 },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
  ] : [
    { key: 'kind', label: '', hidden: true },
    { key: 'code', label: t('common.code'), width: 140 }, ...names,
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
  ]
  const pick = (row: Record<string, unknown>) => {
    const id = Number(row.id)
    if (mode === 'multiple') {
      const cur = Array.isArray(value) ? value : []
      onChange?.(cur.includes(id) ? cur : [...cur, id])
    } else onChange?.(id)
    setOpen(false)
  }
  return (
    <>
      <Space.Compact style={{ width: '100%', ...style }}>
        <Select<number | number[]> showSearch optionFilterProp="label" allowClear={allowClear} disabled={disabled} mode={mode}
          placeholder={placeholder} value={value ?? undefined} options={options} style={{ width: '100%' }}
          onChange={(v) => onChange?.(v ?? null)} />
        <Tooltip title={t('picker.open')}>
          <Button icon={<EllipsisOutlined />} disabled={disabled} onClick={() => setOpen(true)} aria-label={t('picker.open')} />
        </Tooltip>
      </Space.Compact>
      <Modal open={open} onCancel={() => setOpen(false)} footer={null} width="min(1000px, 96vw)" destroyOnHidden
        title={t('picker.title')}>
        <CrudTable endpoint={endpoint} params={params} defaults={defaults} fields={fields} canEdit={hasPerm('dictionaries.edit')}
          onPick={pick} search onChanged={reload} />
      </Modal>
    </>
  )
}

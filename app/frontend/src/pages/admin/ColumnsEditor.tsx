import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Input, InputNumber, Select, Space, Tooltip, Typography } from 'antd'
import Table from '../../components/AppTable'
import { ArrowDownOutlined, ArrowUpOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'

import { api } from '../../api/client'
import type { PrintColumn } from '../../api/crm'

interface FieldGroup { group: string; name_ro: string; name_ru: string; fields: { key: string; ro: string; ru: string }[] }
export interface FieldsInfo { groups: FieldGroup[]; defaults: string[]; supports_columns: boolean }

export const newColumn = (field: string): PrintColumn => ({ field, title_ro: '', title_ru: '', width: null, align: '', factor: null, decimals: null })

/** Câmpurile disponibile pentru coloane, pe tipul de document. */
export function useColumnFields(docType: string) {
  const [info, setInfo] = useState<FieldsInfo | null>(null)
  useEffect(() => {
    setInfo(null)
    api.get<FieldsInfo>('/print-templates/fields/', { params: { doc_type: docType } }).then((r) => setInfo(r.data))
  }, [docType])
  return info
}

/**
 * Coloanele tabelului pe forma de tipar (ca macheta din 1C): ce valoare trage fiecare coloană din fișa produsului
 * (cod de bare, GOST, producător, date logistice, caracteristici) sau din rândul documentului (preț, TVA...),
 * titlul ei în română și rusă, lățimea, alinierea, factorul (kg → g: 1000) și zecimalele.
 */
export default function ColumnsEditor({ value, onChange, info, disabled }: {
  value: PrintColumn[]
  onChange: (columns: PrintColumn[]) => void
  info: FieldsInfo
  disabled?: boolean
}) {
  const { t, i18n } = useTranslation()
  const ru = i18n.language === 'ru'
  const options = useMemo(() => info.groups.map((g) => ({
    label: ru ? g.name_ru : g.name_ro,
    options: g.fields.map((f) => ({ value: f.key, label: ru ? f.ru : f.ro })),
  })), [info, ru])
  const labelOf = useMemo(() => Object.fromEntries(info.groups.flatMap((g) => g.fields.map((f) => [f.key, ru ? f.ru : f.ro]))), [info, ru])
  const [adding, setAdding] = useState<string>()

  const update = (i: number, patch: Partial<PrintColumn>) => onChange(value.map((c, j) => (j === i ? { ...c, ...patch } : c)))
  const move = (i: number, step: number) => {
    const next = [...value]
    const [item] = next.splice(i, 1)
    next.splice(i + step, 0, item)
    onChange(next)
  }

  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('printColumns.hint')}</Typography.Text>
      {value.length === 0 && (
        <Space wrap>
          <Typography.Text type="secondary">{t('printColumns.usingDefaults')}</Typography.Text>
          <Button size="small" disabled={disabled} onClick={() => onChange(info.defaults.map(newColumn))}>{t('printColumns.startFromDefaults')}</Button>
        </Space>
      )}
      <Table<PrintColumn> size="small" rowKey={(_, i) => String(i)} dataSource={value} pagination={false} scroll={{ x: 820 }}
        columns={[
          { title: '#', key: 'n', width: 36, render: (_, _c, i) => i + 1 },
          { title: t('printColumns.field'), key: 'field', width: 230, render: (_, c, i) => (
            <Select size="small" showSearch optionFilterProp="label" style={{ width: '100%' }} disabled={disabled} value={c.field}
              options={options} onChange={(field) => update(i, { field })} popupMatchSelectWidth={false} />
          ) },
          { title: t('printColumns.titleRo'), key: 'tro', width: 170, render: (_, c, i) => (
            <Input size="small" disabled={disabled} value={c.title_ro} placeholder={labelOf[c.field]} onChange={(e) => update(i, { title_ro: e.target.value })} />
          ) },
          { title: t('printColumns.titleRu'), key: 'tru', width: 170, render: (_, c, i) => (
            <Input size="small" disabled={disabled} value={c.title_ru} placeholder={labelOf[c.field]} onChange={(e) => update(i, { title_ru: e.target.value })} />
          ) },
          { title: <Tooltip title={t('printColumns.widthHint')}>{t('printColumns.width')}</Tooltip>, key: 'w', width: 70, render: (_, c, i) => (
            <InputNumber size="small" min={0} max={100} style={{ width: 60 }} disabled={disabled} value={c.width} onChange={(v) => update(i, { width: v })} />
          ) },
          { title: t('printColumns.align'), key: 'a', width: 92, render: (_, c, i) => (
            <Select size="small" style={{ width: 84 }} disabled={disabled} value={c.align} onChange={(align) => update(i, { align })}
              options={[{ value: '', label: t('printColumns.auto') }, { value: 'left', label: '⇤' }, { value: 'center', label: '↔' }, { value: 'right', label: '⇥' }]} />
          ) },
          { title: <Tooltip title={t('printColumns.factorHint')}>{t('printColumns.factor')}</Tooltip>, key: 'f', width: 80, render: (_, c, i) => (
            <InputNumber size="small" min={0} style={{ width: 72 }} disabled={disabled} value={c.factor} onChange={(v) => update(i, { factor: v })} />
          ) },
          { title: t('printColumns.decimals'), key: 'd', width: 64, render: (_, c, i) => (
            <InputNumber size="small" min={0} max={6} style={{ width: 56 }} disabled={disabled} value={c.decimals} onChange={(v) => update(i, { decimals: v })} />
          ) },
          { key: 'x', width: 92, render: (_, _c, i) => !disabled && (
            <Space size={0}>
              <Button type="text" size="small" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => move(i, -1)} />
              <Button type="text" size="small" icon={<ArrowDownOutlined />} disabled={i === value.length - 1} onClick={() => move(i, 1)} />
              <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => onChange(value.filter((_, j) => j !== i))} />
            </Space>
          ) },
        ]} />
      {!disabled && (
        <Space.Compact style={{ width: '100%', maxWidth: 520 }}>
          <Select showSearch optionFilterProp="label" style={{ width: '100%' }} placeholder={t('printColumns.pickField')} value={adding}
            options={options} onChange={setAdding} />
          <Button icon={<PlusOutlined />} disabled={!adding} onClick={() => { onChange([...value, newColumn(adding!)]); setAdding(undefined) }}>
            {t('printColumns.add')}
          </Button>
        </Space.Compact>
      )}
    </Space>
  )
}

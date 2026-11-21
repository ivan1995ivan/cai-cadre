import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, ColorPicker, DatePicker, Form, Input, InputNumber, Modal, Select, Space, Switch, Tag, message, type FormInstance } from 'antd'
import Table from './AppTable'
import FormLayout from './FormLayout'
import dayjs from 'dayjs'
import { PlusOutlined } from '@ant-design/icons'

import { api, errorText, fieldErrors } from '../api/client'
import { invalidateCache, useFetch } from '../api/hooks'
import MarkButton from './MarkButton'
import RefSelect, { type RefSpec } from './RefSelect'

export interface CrudField {
  key: string
  label: string
  type?: 'text' | 'number' | 'bool' | 'color' | 'select' | 'multiselect' | 'textarea' | 'date'
  options?: { value: string | number; label: string }[]
  required?: boolean
  inTable?: boolean
  hidden?: boolean // câmp tehnic: se trimite, dar nu se arată în formular
  display?: boolean // doar coloană în tabel (calculată pe server), fără câmp în formular
  width?: number
  render?: (value: unknown, row: Record<string, unknown>) => ReactNode
  input?: (form: FormInstance) => ReactNode // câmp propriu în formular (de ex. alegerea din clasificator)
  ref?: RefSpec // alegerea din clasificator cu butonul „…” (lista derulantă + forma clasificatorului)
  extra?: ReactNode
}

/** Tabel simplu cu adăugare / editare / marcare pentru ștergere, pentru nomenclatoarele mici. */
export default function CrudTable({ endpoint, fields, canEdit, defaults = {}, extra, title, params, rowActions, onChanged, onPick, search, modalWidth }: {
  endpoint: string
  params?: Record<string, unknown>
  fields: CrudField[]
  canEdit: boolean
  defaults?: Record<string, unknown>
  extra?: ReactNode
  title?: ReactNode
  rowActions?: (row: Record<string, unknown>) => ReactNode // butoane pe rând (de ex. tipărirea), înainte de ștergere
  onChanged?: () => void // după adăugare / modificare / ștergere (de ex. soldul calculat din rânduri)
  onPick?: (row: Record<string, unknown>) => void // forma de alegere (butonul „…”): dublu clic sau „Alege” întoarce rândul
  search?: boolean // căutare în rânduri (după toate câmpurile text)
  modalWidth?: number // forma mai lată (de ex. cu un tabel de rânduri în ea)
}) {
  const { t } = useTranslation()
  const { data, loading, reload } = useFetch<Record<string, unknown>[] | { results: Record<string, unknown>[] }>(
    endpoint, { page_size: 1000, ...params })
  const all = Array.isArray(data) ? data : data?.results ?? []
  const [query, setQuery] = useState('')
  const needle = query.trim().toLowerCase()
  const rows = needle ? all.filter((r) => Object.values(r).some((v) => typeof v === 'string' && v.toLowerCase().includes(needle))) : all
  const [editing, setEditing] = useState<Record<string, unknown> | null>(null)
  const [form] = Form.useForm()

  const open = (row?: Record<string, unknown>) => {
    const value = row ?? { is_active: true, ...defaults }
    setEditing(value)
    form.resetFields()
    const dates = Object.fromEntries(fields.filter((f) => f.type === 'date' && value[f.key]).map((f) => [f.key, dayjs(String(value[f.key]))]))
    form.setFieldsValue({ ...value, ...dates })
  }

  const save = async () => {
    const values = await form.validateFields()
    for (const f of fields) {
      if (f.type === 'color' && values[f.key] && typeof values[f.key] !== 'string') {
        values[f.key] = values[f.key].toHexString().toUpperCase()
      }
      if (f.type === 'date') values[f.key] = values[f.key] ? values[f.key].format('YYYY-MM-DD') : null
    }
    try {
      if (editing?.id) await api.patch(`${endpoint}${editing.id}/`, values)
      else await api.post(endpoint, values)
      message.success(t('common.saved'))
      setEditing(null)
      invalidateCache(endpoint)
      reload()
      onChanged?.()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  const cell = (f: CrudField, value: unknown, row: Record<string, unknown>) => {
    if (f.render) return f.render(value, row)
    if (f.type === 'bool') return value ? t('common.yes') : t('common.no')
    if (f.type === 'color') return value ? <Tag color={String(value)}>{String(value)}</Tag> : null
    if (f.type === 'select') return f.options?.find((o) => o.value === value)?.label ?? ''
    if (f.type === 'date') return value ? dayjs(String(value)).format('DD.MM.YYYY') : ''
    // zecimalele de pe server („10.000”, „1200.00”) — ca număr, fără zerourile de la coadă (10, 1 200), ca în restul tabelelor
    if (f.type === 'number' && value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))) {
      return Number(value).toLocaleString('ro-MD', { maximumFractionDigits: 4 })
    }
    return value as ReactNode
  }

  return (
    <>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }} wrap>
        <Space wrap>
          {search && <Input.Search autoFocus allowClear placeholder={t('picker.search')} style={{ width: 280 }}
            onChange={(e) => setQuery(e.target.value)} />}
          {title}
        </Space>
        <Space>
          {extra}
          {canEdit && <Button icon={<PlusOutlined />} onClick={() => open()} data-cmd="new">{t('common.add')}</Button>}
        </Space>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={loading}
        dataSource={rows}
        pagination={rows.length > 50 ? { pageSize: 50 } : false}
        scroll={{ x: 600 }}
        onRow={(row) => ({ onDoubleClick: () => (onPick ? !row.deletion_mark && onPick(row) : canEdit && !row.deletion_mark && open(row)) })}
        columns={[
          ...fields.filter((f) => f.inTable !== false && !f.hidden).map((f, i) => ({  // câmpul tehnic (hidden) nu e coloană
            title: f.label,
            dataIndex: f.key,
            width: f.width,
            render: (v: unknown, row: Record<string, unknown>) =>
              i === 0 && canEdit && !row.deletion_mark ? <a onClick={() => open(row)}>{cell(f, v, row)}</a> : cell(f, v, row),
          })),
          ...(rowActions ? [{ title: '', key: '_actions', render: (_: unknown, row: Record<string, unknown>) => rowActions(row) }] : []),
          ...(onPick ? [{ title: '', key: '_pick', width: 90, render: (_: unknown, row: Record<string, unknown>) => (
            !row.deletion_mark && <Button size="small" type="primary" onClick={() => onPick(row)}>{t('picker.choose')}</Button>) }] : []),
          ...(canEdit ? [{
            title: '', key: '_del', width: 50,
            render: (_: unknown, row: Record<string, unknown>) => (
              <MarkButton endpoint={endpoint} row={row as { id: number }} onDone={() => { reload(); onChanged?.() }} />
            ),
          }] : []),
        ]}
      />
      <Modal open={!!editing} onOk={save} onCancel={() => setEditing(null)} title={editing?.id ? t('common.edit') : t('common.add')} width={modalWidth}>
        <Form form={form} layout="vertical">
          {/* aranjarea câmpurilor e a fiecărui utilizator (butonul din dreapta sus); câmpurile tehnice rămân ascunse */}
          {fields.filter((f) => f.hidden).map((f) => (
            <Form.Item key={f.key} name={f.key} hidden><Input /></Form.Item>
          ))}
          <FormLayout formKey={`crud:${endpoint}`}>
            {fields.filter((f) => !f.hidden && !f.display).map((f) => (
              <Form.Item key={f.key} name={f.key} label={f.label} valuePropName={f.type === 'bool' ? 'checked' : 'value'}
                rules={f.required ? [{ required: true, message: t('common.required') }] : []} extra={f.extra}>
                {f.input ? f.input(form) : f.ref ? <RefSelect spec={f.ref} allowClear={!f.required} /> : f.type === 'bool' ? <Switch />
                  : f.type === 'number' ? <InputNumber style={{ width: '100%' }} />
                    : f.type === 'color' ? <ColorPicker format="hex" disabledAlpha showText />
                      : f.type === 'select' ? <Select allowClear options={f.options} />
                        : f.type === 'multiselect' ? <Select mode="multiple" allowClear optionFilterProp="label" options={f.options} />
                        : f.type === 'textarea' ? <Input.TextArea rows={3} />
                        : f.type === 'date' ? <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
                          : <Input />}
              </Form.Item>
            ))}
          </FormLayout>
        </Form>
      </Modal>
    </>
  )
}

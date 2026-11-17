import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Checkbox, Form, Input, Modal, Select, Space, Tag, Typography, message } from 'antd'
import Table from '../../components/AppTable'
import { PlusOutlined } from '@ant-design/icons'

import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'
import FormLayout from '../../components/FormLayout'
import MarkButton from '../../components/MarkButton'

interface Locality {
  id: number; country: string; code: string; name: string; name_ru: string; kind: string; region: string; commune: string
  postal_code: string; custom: boolean; label: string; deletion_mark?: boolean
}
interface Country { code: string; name: string; available: number; loaded: number }

/** Administrare → Setări → Localități: încărcarea listelor oficiale (bife pe țări) și clasificatorul, cu căutare și adăugare. */
export default function Localities() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('settings.edit')
  const [countries, setCountries] = useState<Country[]>([])
  const [checked, setChecked] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState<string>()
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Partial<Locality> | null>(null)
  const [form] = Form.useForm()
  const { data, loading, reload } = useFetch<Paged<Locality>>('/localities/', { search: search || undefined, country, page })
  const applyStatus = (list: Country[]) => {
    setCountries(list)
    setChecked(list.filter((c) => c.loaded > 0).map((c) => c.code))
  }
  useEffect(() => {
    api.get<{ countries: Country[] }>('/settings/localities/').then((r) => applyStatus(r.data.countries))
  }, [])

  const load = async () => {
    setBusy(true)
    try {
      const { data: res } = await api.post<{ countries: Country[] }>('/settings/localities/', { countries: checked })
      applyStatus(res.countries)
      reload()
      message.success(t('localities.loaded'))
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  const save = async () => {
    const values = await form.validateFields()
    try {
      if (editing?.id) await api.patch(`/localities/${editing.id}/`, values)
      else await api.post('/localities/', values)
      setEditing(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const startNew = () => {
    setEditing({ country: 'MD' })
    form.setFieldsValue({ country: 'MD', name: '', name_ru: '', kind: '', region: '', commune: '', postal_code: '' })
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.localities')}</Typography.Title>
      <Card size="small" title={t('localities.loadTitle')}>
        <Space orientation="vertical">
          <Typography.Text type="secondary">{t('localities.loadHint')}</Typography.Text>
          {countries.map((c) => (
            <Checkbox key={c.code} disabled={!canEdit} checked={checked.includes(c.code)}
              onChange={(e) => setChecked(e.target.checked ? [...checked, c.code] : checked.filter((x) => x !== c.code))}>
              <b>{c.name}</b> — {t('localities.available', { count: c.available })}
              {c.loaded > 0 ? <Tag color="green" style={{ marginInlineStart: 8 }}>{t('localities.inBase', { count: c.loaded })}</Tag> : null}
            </Checkbox>
          ))}
          {canEdit && <Button type="primary" loading={busy} onClick={load}>{t('localities.load')}</Button>}
          <Alert type="info" showIcon title={t('localities.sources')} />
        </Space>
      </Card>
      <Card size="small">
        <Space wrap style={{ marginBottom: 12 }}>
          <Input.Search allowClear placeholder={t('localities.search')} style={{ width: 280 }} onSearch={(v) => { setSearch(v); setPage(1) }} />
          <Select allowClear placeholder={t('localities.country')} style={{ width: 160 }} value={country} onChange={(v) => { setCountry(v); setPage(1) }}
            options={[{ value: 'MD', label: 'Moldova' }, { value: 'RO', label: 'România' }]} />
          {canEdit && <Button icon={<PlusOutlined />} onClick={startNew}>{t('localities.add')}</Button>}
        </Space>
        <Table<Locality> size="small" rowKey="id" loading={loading} dataSource={data?.results}
          pagination={{ current: page, total: data?.count, pageSize: 50, onChange: setPage, showSizeChanger: false }}
          onRow={(x) => ({ onClick: () => { if (canEdit && !x.deletion_mark) { setEditing(x); form.setFieldsValue(x) } }, style: { cursor: canEdit ? 'pointer' : undefined } })}
          columns={[
            { title: t('localities.name'), dataIndex: 'name', render: (v, x) => <>{v}{x.name_ru && <Typography.Text type="secondary"> / {x.name_ru}</Typography.Text>}</> },
            { title: t('localities.kind'), dataIndex: 'kind', width: 110 },
            { title: t('localities.commune'), dataIndex: 'commune', width: 180 },
            { title: t('localities.region'), dataIndex: 'region', width: 200 },
            { title: t('localities.postal'), dataIndex: 'postal_code', width: 100 },
            { title: '', dataIndex: 'country', width: 90, render: (v, x) => <Space size={4}>{v}{x.custom && <Tag>{t('localities.custom')}</Tag>}</Space> },
            ...(canEdit ? [{ title: '', key: 'x', width: 40, render: (_: unknown, x: Locality) => (
              <span onClick={(e) => e.stopPropagation()}>
                <MarkButton endpoint="/localities/" row={x} onDone={reload} />
              </span>
            ) }] : []),
          ]} />
      </Card>
      <Modal open={!!editing} title={editing?.id ? editing.label : t('localities.add')} onCancel={() => setEditing(null)} onOk={save} destroyOnHidden>
        <Form form={form} layout="vertical" preserve={false}>
          <FormLayout formKey="locality"><Form.Item name="country" label={t('localities.country')} rules={[{ required: true, message: t('common.required') }]}>
            <Input maxLength={2} placeholder="MD / RO / UA" />
          </Form.Item>
          <Form.Item name="name" label={t('localities.name')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
          <Form.Item name="name_ru" label={t('localities.nameRu')}><Input /></Form.Item>
          <Form.Item name="kind" label={t('localities.kind')}><Input placeholder="oraș / comună / sat" /></Form.Item>
          <Form.Item name="commune" label={t('localities.commune')}><Input /></Form.Item>
          <Form.Item name="region" label={t('localities.region')}><Input placeholder="r. Călărași / jud. Iași" /></Form.Item>
          <Form.Item name="postal_code" label={t('localities.postal')}><Input /></Form.Item></FormLayout>
        </Form>
      </Modal>
    </Space>
  )
}

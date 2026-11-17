import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Checkbox, Col, Form, Input, Modal, Row, Select, Space, Tag, Typography, message } from 'antd'
import Table from '../../components/AppTable'
import { PlusOutlined } from '@ant-design/icons'

import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'
import type { Bank } from '../../components/BankInput'
import FormLayout from '../../components/FormLayout'
import MarkButton from '../../components/MarkButton'

interface Country { code: string; name: string; available: number; loaded: number }

/** Administrare → Setări → Bănci: listele oficiale (bife pe țări) și clasificatorul, cu căutare și adăugare. */
export default function Banks() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('settings.edit')
  const [countries, setCountries] = useState<Country[]>([])
  const [checked, setChecked] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState<string>()
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Partial<Bank> | null>(null)
  const [form] = Form.useForm()
  const { data, loading, reload } = useFetch<Paged<Bank>>('/banks/', { search: search || undefined, country, page })
  const applyStatus = (list: Country[]) => {
    setCountries(list)
    setChecked(list.filter((c) => c.loaded > 0).map((c) => c.code))
  }
  useEffect(() => {
    api.get<{ countries: Country[] }>('/settings/banks/').then((r) => applyStatus(r.data.countries))
  }, [])

  const load = async () => {
    setBusy(true)
    try {
      const { data: res } = await api.post<{ countries: Country[] }>('/settings/banks/', { countries: checked })
      applyStatus(res.countries)
      reload()
      message.success(t('banks.loaded'))
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  const save = async () => {
    const values = await form.validateFields()
    try {
      if (editing?.id) await api.patch(`/banks/${editing.id}/`, values)
      else await api.post('/banks/', values)
      setEditing(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const startNew = () => {
    const empty = { country: 'MD', code: '', name: '', short_name: '', bic: '', fiscal_code: '', address: '', phone: '', email: '', website: '', note: '' }
    setEditing(empty)
    form.setFieldsValue(empty)
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.banks')}</Typography.Title>
      <Card size="small" title={t('banks.loadTitle')}>
        <Space orientation="vertical">
          <Typography.Text type="secondary">{t('banks.loadHint')}</Typography.Text>
          {countries.map((c) => (
            <Checkbox key={c.code} disabled={!canEdit} checked={checked.includes(c.code)}
              onChange={(e) => setChecked(e.target.checked ? [...checked, c.code] : checked.filter((x) => x !== c.code))}>
              <b>{c.name}</b> — {t('banks.available', { count: c.available })}
              {c.loaded > 0 ? <Tag color="green" style={{ marginInlineStart: 8 }}>{t('banks.inBase', { count: c.loaded })}</Tag> : null}
            </Checkbox>
          ))}
          {canEdit && <Button type="primary" loading={busy} onClick={load}>{t('banks.load')}</Button>}
          <Alert type="info" showIcon title={t('banks.sources')} />
        </Space>
      </Card>
      <Card size="small">
        <Space wrap style={{ marginBottom: 12 }}>
          <Input.Search allowClear placeholder={t('banks.search')} style={{ width: 280 }} onSearch={(v) => { setSearch(v); setPage(1) }} />
          <Select allowClear placeholder={t('localities.country')} style={{ width: 160 }} value={country} onChange={(v) => { setCountry(v); setPage(1) }}
            options={[{ value: 'MD', label: 'Moldova' }, { value: 'RO', label: 'România' }]} />
          {canEdit && <Button icon={<PlusOutlined />} onClick={startNew}>{t('banks.add')}</Button>}
        </Space>
        <Table<Bank> size="small" rowKey="id" loading={loading} dataSource={data?.results} scroll={{ x: 900 }}
          pagination={{ current: page, total: data?.count, pageSize: 50, onChange: setPage, showSizeChanger: false }}
          onRow={(x) => ({ onClick: () => { if (canEdit && !x.deletion_mark) { setEditing(x); form.setFieldsValue(x) } }, style: { cursor: canEdit ? 'pointer' : undefined } })}
          columns={[
            { title: t('banks.name'), dataIndex: 'name', render: (v, x) => (
              <>{v}{x.short_name && <Typography.Text type="secondary"> ({x.short_name})</Typography.Text>}
                {x.note && <div><Typography.Text type="secondary" style={{ fontSize: 12 }}>{x.note}</Typography.Text></div>}</>
            ) },
            { title: 'BIC / SWIFT', dataIndex: 'bic', width: 110 },
            { title: t('banks.code'), dataIndex: 'code', width: 80 },
            { title: t('banks.fiscalCode'), dataIndex: 'fiscal_code', width: 130 },
            { title: t('banks.address'), dataIndex: 'address', width: 280 },
            { title: t('banks.phone'), dataIndex: 'phone', width: 160 },
            { title: '', dataIndex: 'country', width: 90, render: (v, x) => <Space size={4}>{v}{x.custom && <Tag>{t('localities.custom')}</Tag>}</Space> },
            ...(canEdit ? [{ title: '', key: 'x', width: 40, render: (_: unknown, x: Bank) => (
              <span onClick={(e) => e.stopPropagation()}>
                <MarkButton endpoint="/banks/" row={x} onDone={reload} />
              </span>
            ) }] : []),
          ]} />
      </Card>
      <Modal open={!!editing} title={editing?.id ? editing.name : t('banks.add')} onCancel={() => setEditing(null)} onOk={save} destroyOnHidden width={640}>
        <Form form={form} layout="vertical" preserve={false}>
          <FormLayout formKey="bank"><Row gutter={12}>
            <Col span={8}>
              <Form.Item name="country" label={t('localities.country')} rules={[{ required: true, message: t('common.required') }]}>
                <Input maxLength={2} placeholder="MD / RO / UA" />
              </Form.Item>
            </Col>
            <Col span={8}><Form.Item name="bic" label="BIC / SWIFT"><Input maxLength={11} /></Form.Item></Col>
            <Col span={8}>
              <Form.Item name="code" label={t('banks.code')} tooltip={t('banks.codeHint')}><Input maxLength={4} placeholder="AG / BTRL" /></Form.Item>
            </Col>
          </Row>
          <Form.Item name="name" label={t('banks.name')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="short_name" label={t('banks.shortName')}><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="fiscal_code" label={t('banks.fiscalCode')}><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="address" label={t('banks.address')}><Input /></Form.Item>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="phone" label={t('banks.phone')}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="email" label="E-mail"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="website" label={t('banks.website')}><Input /></Form.Item></Col>
          </Row>
          <Form.Item name="note" label={t('banks.note')}><Input /></Form.Item></FormLayout>
        </Form>
      </Modal>
    </Space>
  )
}

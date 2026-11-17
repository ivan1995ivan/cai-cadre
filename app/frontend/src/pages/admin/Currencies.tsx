import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Button, Card, Col, DatePicker, Form, Input, InputNumber, Modal, Row, Select, Space, Switch, Tag, Typography,
  message,
} from 'antd'
import Table from '../../components/AppTable'
import { CloudDownloadOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import type { Currency, ExchangeRate, VatRate } from '../../api/types'
import { useApp, useLocalName } from '../../auth/AppContext'

export default function Currencies() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const localName = useLocalName()
  const canEdit = hasPerm('settings.edit')
  const [currencies, setCurrencies] = useState<Currency[]>([])
  const [rates, setRates] = useState<Paged<ExchangeRate> | null>(null)
  const [vat, setVat] = useState<VatRate[]>([])
  const [filter, setFilter] = useState<string | undefined>()
  const [page, setPage] = useState(1)
  const [bnmDate, setBnmDate] = useState<Dayjs>(dayjs())
  const [fetching, setFetching] = useState(false)
  const [modal, setModal] = useState<null | 'currency' | 'rate' | 'vat'>(null)
  const [editId, setEditId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadCurrencies = useCallback(() => api.get<Currency[]>('/currencies/').then((r) => setCurrencies(r.data)), [])
  const loadVat = useCallback(() => api.get<VatRate[]>('/vat-rates/').then((r) => setVat(r.data)), [])
  const loadRates = useCallback(
    () => api.get<Paged<ExchangeRate>>('/exchange-rates/', { params: { currency: filter, page } }).then((r) => setRates(r.data)),
    [filter, page],
  )

  useEffect(() => {
    loadCurrencies()
    loadVat()
  }, [loadCurrencies, loadVat])
  useEffect(() => {
    loadRates()
  }, [loadRates])

  const fetchBnm = async () => {
    setFetching(true)
    try {
      const { data } = await api.post('/exchange-rates/fetch-bnm/', { date: bnmDate.format('YYYY-MM-DD') })
      message.success(t('currencies.fetched', { count: data.saved, date: dayjs(data.date).format('DD.MM.YYYY') }))
      loadRates()
      loadCurrencies()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setFetching(false)
    }
  }

  const openModal = (kind: 'currency' | 'rate' | 'vat', record?: Record<string, unknown>) => {
    setModal(kind)
    setEditId((record?.id as number) ?? null)
    form.resetFields()
    if (record) form.setFieldsValue({ ...record, date: record.date ? dayjs(record.date as string) : undefined })
    else if (kind === 'rate') form.setFieldsValue({ date: dayjs(), nominal: 1 })
    else if (kind === 'currency') form.setFieldsValue({ is_active: true, auto_rate: true })
    else form.setFieldsValue({ is_active: true })
  }

  const saveModal = async () => {
    const values = await form.validateFields()
    if (values.date) values.date = values.date.format('YYYY-MM-DD')
    const url = { currency: '/currencies/', rate: '/exchange-rates/', vat: '/vat-rates/' }[modal!]
    try {
      if (editId) await api.patch(`${url}${editId}/`, values)
      else await api.post(url, values)
      setModal(null)
      loadCurrencies()
      loadRates()
      loadVat()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.currencies')}</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title={t('currencies.title')} extra={canEdit && <Button icon={<PlusOutlined />} onClick={() => openModal('currency')}>{t('common.add')}</Button>}>
            <Table<Currency> rowKey="id" size="small" pagination={false} dataSource={currencies}
              columns={[
                { title: t('common.code'), dataIndex: 'code', render: (v, c) => (canEdit ? <a onClick={() => openModal('currency', c as never)}>{v}</a> : v) },
                { title: t('common.name'), key: 'name', render: (_, c) => localName(c) },
                {
                  title: t('currencies.lastRate'), key: 'rate',
                  render: (_, c) => c.is_base ? <Tag color="blue">{t('currencies.base')}</Tag>
                    : c.last_rate ? `${c.last_rate.rate}${c.last_rate.nominal > 1 ? ` / ${c.last_rate.nominal}` : ''} (${dayjs(c.last_rate.date).format('DD.MM')})` : '—',
                },
                { title: t('currencies.auto'), dataIndex: 'auto_rate', render: (v, c) => !c.is_base && (v ? <Tag color="green">BNM</Tag> : <Tag>{t('currencies.manual')}</Tag>) },
                { title: t('users.active'), dataIndex: 'is_active', render: (v) => (v ? t('common.yes') : t('common.no')) },
              ]} />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title={t('currencies.vat')} extra={canEdit && <Button icon={<PlusOutlined />} onClick={() => openModal('vat')}>{t('common.add')}</Button>}>
            <Table<VatRate> rowKey="id" size="small" pagination={false} dataSource={vat}
              columns={[
                { title: t('common.name'), dataIndex: 'name', render: (v, r) => (canEdit ? <a onClick={() => openModal('vat', r as never)}>{v}</a> : v) },
                { title: '%', dataIndex: 'rate' },
                { title: '', dataIndex: 'is_default', render: (v) => v && <Tag color="green">{t('currencies.default')}</Tag> },
                { title: t('users.active'), dataIndex: 'is_active', render: (v) => (v ? t('common.yes') : t('common.no')) },
              ]} />
          </Card>
        </Col>
        <Col xs={24}>
          <Card title={t('currencies.rates')}
            extra={canEdit && (
              <Space wrap>
                <DatePicker value={bnmDate} onChange={(d) => d && setBnmDate(d)} format="DD.MM.YYYY" allowClear={false} />
                <Button type="primary" icon={<CloudDownloadOutlined />} loading={fetching} onClick={fetchBnm}>{t('currencies.fetchBnm')}</Button>
                <Button icon={<PlusOutlined />} onClick={() => openModal('rate')}>{t('currencies.manualRate')}</Button>
              </Space>
            )}>
            <Select allowClear placeholder={t('currencies.title')} style={{ width: 160, marginBottom: 12 }} value={filter}
              onChange={(v) => { setFilter(v); setPage(1) }}
              options={currencies.filter((c) => !c.is_base).map((c) => ({ value: c.code, label: c.code }))} />
            <Table<ExchangeRate> rowKey="id" size="small" dataSource={rates?.results}
              pagination={{ current: page, total: rates?.count, pageSize: 50, onChange: setPage, showSizeChanger: false }}
              columns={[
                { title: t('common.date'), dataIndex: 'date', render: (v) => dayjs(v).format('DD.MM.YYYY') },
                { title: t('currencies.title'), dataIndex: 'currency_code' },
                { title: t('currencies.rate'), dataIndex: 'rate' },
                { title: t('currencies.nominal'), dataIndex: 'nominal' },
                { title: t('currencies.source'), dataIndex: 'source', render: (v) => <Tag color={v === 'bnm' ? 'green' : 'default'}>{v.toUpperCase()}</Tag> },
              ]} />
          </Card>
        </Col>
      </Row>

      <Modal open={!!modal} onOk={saveModal} onCancel={() => setModal(null)}
        title={modal === 'currency' ? t('currencies.title') : modal === 'vat' ? t('currencies.vat') : t('currencies.manualRate')}>
        <Form form={form} layout="vertical">
          {modal === 'currency' && (
            <>
              <Form.Item name="code" label={t('common.code')} rules={[{ required: true, len: 3 }]}><Input maxLength={3} style={{ textTransform: 'uppercase' }} /></Form.Item>
              <Form.Item name="name_ro" label={t('roles.name_ro')} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="name_ru" label={t('roles.name_ru')} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="symbol" label={t('currencies.symbol')}><Input /></Form.Item>
              <Space size="large">
                <Form.Item name="auto_rate" label={t('currencies.auto')} valuePropName="checked"><Switch /></Form.Item>
                <Form.Item name="is_active" label={t('users.active')} valuePropName="checked"><Switch /></Form.Item>
              </Space>
            </>
          )}
          {modal === 'vat' && (
            <>
              <Form.Item name="name" label={t('common.name')} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="rate" label="%" rules={[{ required: true }]}><InputNumber min={0} max={100} style={{ width: '100%' }} /></Form.Item>
              <Space size="large">
                <Form.Item name="is_default" label={t('currencies.default')} valuePropName="checked"><Switch /></Form.Item>
                <Form.Item name="is_active" label={t('users.active')} valuePropName="checked"><Switch /></Form.Item>
              </Space>
            </>
          )}
          {modal === 'rate' && (
            <>
              <Form.Item name="currency" label={t('currencies.title')} rules={[{ required: true }]}>
                <Select options={currencies.filter((c) => !c.is_base).map((c) => ({ value: c.id, label: c.code }))} />
              </Form.Item>
              <Form.Item name="date" label={t('common.date')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item>
              <Form.Item name="rate" label={t('currencies.rate')} rules={[{ required: true }]}><InputNumber min={0} step={0.0001} style={{ width: '100%' }} /></Form.Item>
              <Form.Item name="nominal" label={t('currencies.nominal')}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </Space>
  )
}

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, Form, Input, InputNumber, Modal, Space, Switch, Typography, message } from 'antd'
import Table from '../../components/AppTable'
import { api, errorText, fieldErrors } from '../../api/client'
import type { NumberSeries } from '../../api/types'
import { useApp, useLocalName } from '../../auth/AppContext'

export default function Numbering() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const localName = useLocalName()
  const [items, setItems] = useState<NumberSeries[]>([])
  const [editing, setEditing] = useState<NumberSeries | null>(null)
  const [form] = Form.useForm()

  const load = () => api.get<NumberSeries[]>('/number-series/').then((r) => setItems(r.data))
  useEffect(() => {
    load()
  }, [])

  const open = (s: NumberSeries) => {
    if (!hasPerm('settings.edit')) return
    setEditing(s)
    form.setFieldsValue(s)
  }

  const save = async () => {
    const values = await form.validateFields()
    try {
      await api.patch(`/number-series/${editing!.id}/`, values)
      message.success(t('common.saved'))
      setEditing(null)
      load()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.numbering')}</Typography.Title>
      <Typography.Paragraph type="secondary">{t('numbering.hint')}</Typography.Paragraph>
      <Card>
        <Table<NumberSeries> rowKey="id" size="small" pagination={false} dataSource={items} scroll={{ x: 700 }}
          onRow={(s) => ({ onClick: () => open(s), style: { cursor: 'pointer' } })}
          columns={[
            { title: t('numbering.document'), key: 'name', render: (_, s) => localName(s) },
            { title: t('numbering.prefix'), dataIndex: 'prefix' },
            { title: t('numbering.withYear'), dataIndex: 'include_year', render: (v) => (v ? t('common.yes') : t('common.no')) },
            { title: t('numbering.resetYearly'), dataIndex: 'reset_yearly', render: (v) => (v ? t('common.yes') : t('common.no')) },
            { title: t('numbering.next'), dataIndex: 'preview', render: (v) => <Typography.Text code>{v}</Typography.Text> },
          ]} />
      </Card>
      <Modal open={!!editing} title={editing && localName(editing)} onOk={save} onCancel={() => setEditing(null)}>
        <Form form={form} layout="vertical">
          <Form.Item name="prefix" label={t('numbering.prefix')}><Input maxLength={10} /></Form.Item>
          <Form.Item name="padding" label={t('numbering.padding')}><InputNumber min={1} max={10} /></Form.Item>
          <Form.Item name="next_value" label={t('numbering.nextValue')} extra={t('numbering.nextValueHint')}><InputNumber min={1} /></Form.Item>
          <Space size="large">
            <Form.Item name="include_year" label={t('numbering.withYear')} valuePropName="checked"><Switch /></Form.Item>
            <Form.Item name="reset_yearly" label={t('numbering.resetYearly')} valuePropName="checked"><Switch /></Form.Item>
          </Space>
        </Form>
      </Modal>
    </Space>
  )
}

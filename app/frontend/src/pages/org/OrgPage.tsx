import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, Col, Form, Input, InputNumber, Modal, Row, Select, Space, Switch, Tag, TreeSelect, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'

import Table from '../../components/AppTable'
import ExcelImport from '../../components/ExcelImport'
import { api, errorText, fieldErrors } from '../../api/client'
import { invalidateCache, useFetch } from '../../api/hooks'
import type { OrgMeta, Subdivision } from '../../api/org'
import { useApp, useLocalName } from '../../auth/AppContext'
import { useEnumOptions } from './DictionariesPage'
import FormLayout from '../../components/FormLayout'
import MarkButton from '../../components/MarkButton'

interface TreeNode { value: number; title: string; children?: TreeNode[] }

function toTreeSelect(nodes: Subdivision[], exclude?: number): TreeNode[] {
  return nodes.filter((n) => n.id !== exclude).map((n) => ({
    value: n.id, title: n.name_ro, children: n.children ? toTreeSelect(n.children, exclude) : undefined,
  }))
}

/** Subdiviziunile întreprinderii (departamente, secții, ateliere, filiale), ierarhic. */
export default function OrgPage() {
  const { t } = useTranslation()
  const { hasPerm, companyName, languages } = useApp()
  const localName = useLocalName()
  const canEdit = hasPerm('org.edit')
  const [q, setQ] = useState('')
  const { data, loading, reload } = useFetch<Subdivision[]>('/org/subdivisions/', { tree: 1, q: q || undefined })
  const { data: meta } = useFetch<OrgMeta>('/org/meta/')
  const opts = useEnumOptions()
  const [editing, setEditing] = useState<Partial<Subdivision> | null>(null)
  const [form] = Form.useForm()

  const open = (row?: Partial<Subdivision>) => {
    const value = row ?? { kind: 'section', is_active: true, extra_leave_days: 0, sort: 0 }
    setEditing(value)
    form.resetFields()
    form.setFieldsValue(value)
  }

  const save = async () => {
    const values = await form.validateFields()
    try {
      if (editing?.id) await api.patch(`/org/subdivisions/${editing.id}/`, values)
      else await api.post('/org/subdivisions/', values)
      message.success(t('common.saved'))
      setEditing(null)
      invalidateCache('/org/subdivisions/')
      reload()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  return (
    <Card title={<Space direction="vertical" size={0}><span>{t('menu.org')}</span>
      <Typography.Text type="secondary" style={{ fontWeight: 400 }}>{companyName}</Typography.Text></Space>}
      extra={<Space>
        <Input.Search allowClear placeholder={t('common.search')} onSearch={setQ} style={{ width: 220 }} />
        {canEdit && <ExcelImport code="subdivisions" onDone={() => { invalidateCache('/org/subdivisions/'); reload() }} />}
        {canEdit && <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('common.add')}</Button>}
      </Space>}>
      <Table<Subdivision> rowKey="id" size="small" loading={loading} dataSource={data ?? []} pagination={false}
        expandable={{ defaultExpandAllRows: true }}
        onRow={(row) => ({ onDoubleClick: () => canEdit && !row.deletion_mark && open(row) })}
        columns={[
          { title: t('org.subdivision'), dataIndex: 'name_ro', render: (_: unknown, r) => (
            <Space>
              {canEdit && !r.deletion_mark ? <a onClick={() => open(r)}>{localName(r)}</a> : localName(r)}
              {!r.is_active && <Tag>{t('common.inactive')}</Tag>}
            </Space>) },
          { title: t('common.code'), dataIndex: 'code', width: 90 },
          { title: t('org.kind'), dataIndex: 'kind', width: 190, render: (v: string) => t(`org.subKind.${v}`) },
          { title: t('org.harmful'), dataIndex: 'harmful', width: 150,
            render: (v: boolean, r) => v ? <Tag color="volcano">{t('org.harmfulShort', { days: r.extra_leave_days })}
              {Number(r.harmful_pct) ? ` · +${Number(r.harmful_pct)}%` : ''}</Tag> : null },
          { title: t('org.head'), dataIndex: 'head_name', width: 200 },
          ...(canEdit ? [{ title: '', key: 'del', width: 50, render: (_: unknown, r: Subdivision) => (
            <MarkButton endpoint="/org/subdivisions/" row={r} onDone={reload} />) }] : []),
        ]} />

      <Modal open={!!editing} width={720} onOk={save} onCancel={() => setEditing(null)}
        title={editing?.id ? t('common.edit') : t('org.newSubdivision')}>
        <Form form={form} layout="vertical">
          <FormLayout formKey="subdivision"><Row gutter={12}>
            <Col span={16}><Form.Item name="name_ro" label={t('org.nameRo')} rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="code" label={t('common.code')}><Input /></Form.Item></Col>
            {languages.includes('ru') && <Col span={12}><Form.Item name="name_ru" label={t('org.nameRu')}><Input /></Form.Item></Col>}
            {languages.includes('en') && <Col span={12}><Form.Item name="name_en" label={t('org.nameEn')}><Input /></Form.Item></Col>}
            <Col span={12}>
              <Form.Item name="parent" label={t('org.parent')}>
                <TreeSelect allowClear treeDefaultExpandAll treeData={toTreeSelect(data ?? [], editing?.id)} />
              </Form.Item>
            </Col>
            <Col span={12}><Form.Item name="kind" label={t('org.kind')}><Select options={opts('org.subKind', meta?.subdivision_kinds)} /></Form.Item></Col>
            <Col span={6}><Form.Item name="harmful" label={t('org.harmful')} valuePropName="checked"><Switch /></Form.Item></Col>
            <Col span={6}><Form.Item name="harmful_pct" label={t('org.harmfulPct')} tooltip={t('org.harmfulPctHint')}>
              <InputNumber min={0} max={300} style={{ width: '100%' }} suffix="%" /></Form.Item></Col>
            <Col span={6}><Form.Item name="extra_leave_days" label={t('org.extraLeave')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name="reduced_hours" label={t('org.reducedHours')}><InputNumber min={0} max={40} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={12}><Form.Item name="head_name" label={t('org.head')}><Input /></Form.Item></Col>
            <Col span={6}><Form.Item name="sort" label={t('org.sort')}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name="is_active" label={t('common.active')} valuePropName="checked"><Switch /></Form.Item></Col>
          </Row></FormLayout>
        </Form>
      </Modal>
    </Card>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Button, Card, Col, Drawer, Form, Input, Popconfirm, Row, Select, Space, Switch, Tag, Typography, message,
} from 'antd'
import Table from '../../components/AppTable'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import { LANG_LABELS, type Role, type User } from '../../api/types'
import { useApp, useLocalName } from '../../auth/AppContext'
import { useFetch } from '../../api/hooks'
import type { Subdivision } from '../../api/org'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'

export default function Users() {
  const { t } = useTranslation()
  const { hasPerm, me, languages } = useApp()
  const localName = useLocalName()
  const [data, setData] = useState<Paged<User> | null>(null)
  const [roles, setRoles] = useState<Role[]>([])
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<Partial<User> | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  const { data: tree } = useFetch<Subdivision[]>('/org/subdivisions/', { tree: 1 })
  const subName = (id: number) => {
    const find = (nodes: Subdivision[]): Subdivision | undefined => {
      for (const n of nodes) {
        if (n.id === id) return n
        const hit = find(n.children ?? [])
        if (hit) return hit
      }
      return undefined
    }
    return localName(find(tree ?? []))
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get<Paged<User>>('/users/', { params: { page, search: search || undefined, role: roleFilter } })
      setData(data)
    } finally {
      setLoading(false)
    }
  }, [page, search, roleFilter])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (hasPerm('roles.view')) api.get<Paged<Role> | Role[]>('/roles/', { params: { page_size: 500 } }).then((r) => {
      setRoles(Array.isArray(r.data) ? r.data : r.data.results)
    })
  }, [hasPerm])

  const open = (user?: User) => {
    const initial = user ?? { is_active: true, language: languages[0], roles: [], subdivisions: [] }
    setEditing(initial)
    form.resetFields()
    form.setFieldsValue({ ...initial, password: '' })
  }

  const save = async () => {
    const values = await form.validateFields()
    if (!values.password) delete values.password
    setSaving(true)
    try {
      if (editing?.id) await api.patch(`/users/${editing.id}/`, values)
      else await api.post('/users/', values)
      message.success(t('common.saved'))
      setEditing(null)
      load()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (user: User) => {
    try {
      await api.delete(`/users/${user.id}/`)
      message.success(t('common.deleted'))
      load()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const roleName = (id: number) => localName(roles.find((r) => r.id === id))

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.users')}</Typography.Title>
        {hasPerm('users.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('common.add')}</Button>}
      </Space>
      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search placeholder={t('common.search')} allowClear onSearch={(v) => { setSearch(v); setPage(1) }} style={{ width: 260 }} />
          <Select allowClear placeholder={t('users.roles')} style={{ width: 220 }} value={roleFilter}
            onChange={(v) => { setRoleFilter(v); setPage(1) }}
            options={roles.map((r) => ({ value: r.id, label: localName(r) }))} />
        </Space>
        <Table<User>
          rowKey="id"
          loading={loading}
          dataSource={data?.results}
          scroll={{ x: 900 }}
          pagination={{ current: page, total: data?.count, pageSize: 50, onChange: setPage, showSizeChanger: false }}
          onRow={(u) => ({ onDoubleClick: () => hasPerm('users.edit') && open(u) })}
          columns={[
            { title: t('users.name'), dataIndex: 'full_name', render: (v, u) => <a onClick={() => open(u)}>{v}</a> },
            { title: t('login.username'), dataIndex: 'username' },
            { title: t('users.roles'), dataIndex: 'roles', render: (ids: number[]) => ids.map((id) => <Tag key={id}>{roleName(id)}</Tag>) },
            { title: t('users.subdivisions'), dataIndex: 'subdivisions', render: (ids: number[] = []) => ids.map((id) => <Tag key={id}>{subName(id)}</Tag>) },
            {
              title: t('users.active'), dataIndex: 'is_active', width: 90,
              render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? t('common.yes') : t('common.no')}</Tag>,
            },
            { title: t('users.lastLogin'), dataIndex: 'last_login', render: (v) => (v ? dayjs(v).format('DD.MM.YYYY HH:mm') : '—') },
            {
              title: '', key: 'actions', width: 60,
              render: (_, u) => hasPerm('users.delete') && u.id !== me?.id && (
                <Popconfirm title={t('common.confirmDelete')} onConfirm={() => remove(u)}>
                  <Button type="link" danger size="small">{t('common.delete')}</Button>
                </Popconfirm>
              ),
            },
          ]}
        />
      </Card>

      <Drawer open={!!editing} onClose={() => setEditing(null)} size="large"
        title={editing?.id ? t('users.edit') : t('users.new')}
        extra={<Button type="primary" onClick={save} loading={saving}>{t('common.save')}</Button>}>
        <Form form={form} layout="vertical">
          <FormLayout formKey="user"><Row gutter={16}>
            <Col xs={24} md={8}><Form.Item name="last_name" label={t('users.last_name')}><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="first_name" label={t('users.first_name')}><Input /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="middle_name" label={t('users.middle_name')}><Input /></Form.Item></Col>
            <Col xs={24} md={12}>
              <Form.Item name="username" label={t('login.username')} rules={[{ required: true, message: t('common.required') }]}>
                <Input autoComplete="off" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="password" label={editing?.id ? t('users.newPassword') : t('login.password')}
                extra={t('users.passwordRules')} rules={editing?.id ? [] : [{ required: true, message: t('common.required') }]}>
                <Input.Password autoComplete="new-password" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}><Form.Item name="email" label="E-mail" rules={[{ type: 'email' }]}><Input /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="phone" label={t('users.phone')}><Input /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="position" label={t('users.position')}><Input /></Form.Item></Col>
            <Col xs={24} md={12}>
              <Form.Item name="language" label={t('profile.language')}>
                <Select options={languages.map((l) => ({ value: l, label: LANG_LABELS[l] }))} />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item name="roles" label={t('users.roles')} extra={t('users.rolesHint')}>
                <Select mode="multiple" options={roles.map((r) => ({ value: r.id, label: localName(r) }))} />
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Form.Item name="subdivisions" label={t('users.subdivisions')} extra={t('users.subdivisionsHint')}>
                <SubdivisionSelect mode="multiple" />
              </Form.Item>
            </Col>
            <Col xs={12}>
              <Form.Item name="is_active" label={t('users.active')} valuePropName="checked"><Switch /></Form.Item>
            </Col>
            <Col xs={12}>
              <Form.Item name="must_change_password" label={t('users.mustChange')} valuePropName="checked"><Switch /></Form.Item>
            </Col>
          </Row></FormLayout>
        </Form>
      </Drawer>
    </Space>
  )
}

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert, Button, Card, Checkbox, Col, Form, Input, List, Popconfirm, Row, Select, Space, Switch,
  Tag, Tree, Typography, message,
} from 'antd'
import Table from '../../components/AppTable'
import { LockOutlined, PlusOutlined } from '@ant-design/icons'

import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import type { PermissionCatalog, Role } from '../../api/types'
import { useApp, useLocalName } from '../../auth/AppContext'
import { useFetch } from '../../api/hooks'
import { completeSections, type MenuSection, sectionKeys, useSectionName } from '../../layout/menu'
import { navLabel, SETTINGS_NAV } from '../../layout/nav'
import { useEditGuard } from '../../components/UnsavedGuard'

type Editable = Partial<Role> & { permissions: string[]; data_scopes: Record<string, string>; hidden_fields: string[]; menu_hidden: string[] }

export default function Roles() {
  const { t } = useTranslation()
  const { hasPerm, lang, reloadMe, languages } = useApp()
  const localName = useLocalName()
  const [roles, setRoles] = useState<Role[]>([])
  const [catalog, setCatalog] = useState<PermissionCatalog | null>(null)
  const [selected, setSelected] = useState<Editable | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  const canEdit = hasPerm('roles.edit')
  const { touch, clean } = useEditGuard(() => save(), canEdit)
  /** O schimbare a bifelor rolului ales (drepturi, date, câmpuri, meniu) — rămâne de salvat. */
  const edit = (value: Editable) => {
    setSelected(value)
    touch()
  }

  const load = useCallback(async () => {
    const { data } = await api.get<Paged<Role>>('/roles/', { params: { page_size: 500 } })
    setRoles(data.results)
    return data.results
  }, [])

  useEffect(() => {
    load().then((list) => list[0] && select(list[0]))
    api.get<PermissionCatalog>('/roles/catalog/').then((r) => setCatalog(r.data))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load])

  const select = (role: Role | null) => {
    const value: Editable = role
      ? { ...role, permissions: [...role.permissions], data_scopes: { ...role.data_scopes }, hidden_fields: [...role.hidden_fields], menu_hidden: [...(role.menu_hidden ?? [])] }
      : { name_ro: '', name_ru: '', code: '', is_admin: false, permissions: [], data_scopes: {}, hidden_fields: [], menu_hidden: [] }
    setSelected(value)
    form.resetFields()
    form.setFieldsValue(value)
    clean()
  }

  const togglePerm = (code: string, checked: boolean) => {
    if (!selected) return
    const permissions = checked ? [...selected.permissions, code] : selected.permissions.filter((p) => p !== code)
    edit({ ...selected, permissions })
  }

  const toggleModule = (module: string, actions: string[], checked: boolean) => {
    if (!selected) return
    const codes = actions.map((a) => `${module}.${a}`)
    const rest = selected.permissions.filter((p) => !codes.includes(p))
    edit({ ...selected, permissions: checked ? [...rest, ...codes] : rest })
  }

  const save = async () => {
    if (!selected) return
    const values = await form.validateFields()
    const payload = { ...values, permissions: selected.permissions, data_scopes: selected.data_scopes, hidden_fields: selected.hidden_fields, menu_hidden: selected.menu_hidden }
    setSaving(true)
    try {
      const { data } = selected.id ? await api.patch<Role>(`/roles/${selected.id}/`, payload) : await api.post<Role>('/roles/', payload)
      message.success(t('common.saved'))
      await load()
      select(data)
      reloadMe()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
      return false
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!selected?.id) return
    try {
      await api.delete(`/roles/${selected.id}/`)
      message.success(t('common.deleted'))
      const list = await load()
      select(list[0] ?? null)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const label = (obj: { ro: string; ru: string }) => (lang === 'ru' ? obj.ru : obj.ro)
  const allActions = useMemo(() => (catalog ? Object.keys(catalog.actions) : []), [catalog])

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.roles')}</Typography.Title>
        {hasPerm('roles.create') && <Button icon={<PlusOutlined />} onClick={() => select(null)}>{t('roles.new')}</Button>}
      </Space>
      <Row gutter={16}>
        <Col xs={24} lg={6}>
          <Card size="small">
            <List
              dataSource={roles}
              renderItem={(r) => (
                <List.Item onClick={() => select(r)} style={{
                  cursor: 'pointer', paddingInline: 8, borderRadius: 6,
                  background: selected?.id === r.id ? 'var(--ant-color-primary-bg)' : undefined,
                }}>
                  <Space orientation="vertical" size={0}>
                    <Space>
                      {r.is_system && <LockOutlined style={{ opacity: 0.5 }} />}
                      <Typography.Text strong>{localName(r)}</Typography.Text>
                    </Space>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('roles.userCount', { count: r.user_count ?? 0 })}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={18}>
          {selected && catalog && (
            <Card title={selected.id ? localName(selected as Role) : t('roles.new')}
              extra={canEdit && (
                <Space>
                  {selected.id && !selected.is_system && (
                    <Popconfirm title={t('common.confirmDelete')} onConfirm={remove}>
                      <Button danger>{t('common.delete')}</Button>
                    </Popconfirm>
                  )}
                  <Button type="primary" onClick={save} loading={saving}>{t('common.save')}</Button>
                </Space>
              )}>
              <Form form={form} layout="vertical" disabled={!canEdit} onValuesChange={touch}>
                <Row gutter={16}>
                  <Col xs={24} md={8}>
                    <Form.Item name="name_ro" label={t('roles.name_ro')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
                  </Col>
                  {languages.includes('ru') && <Col xs={24} md={8}>
                    <Form.Item name="name_ru" label={t('roles.name_ru')}><Input /></Form.Item>
                  </Col>}
                  <Col xs={24} md={8}>
                    <Form.Item name="code" label={t('common.code')} rules={[{ required: true, pattern: /^[a-z0-9_-]+$/, message: t('roles.codeHint') }]}>
                      <Input disabled={selected.is_system} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item name="is_admin" label={t('roles.isAdmin')} valuePropName="checked" extra={t('roles.isAdminHint')}>
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>
              </Form>

              {selected.is_admin ? (
                <Alert type="info" showIcon title={t('roles.adminAll')} />
              ) : (
                <>
                  <Typography.Title level={5}>{t('roles.matrix')}</Typography.Title>
                  <Table
                    size="small"
                    rowKey="code"
                    pagination={false}
                    scroll={{ x: 900 }}
                    dataSource={catalog.modules}
                    columns={[
                      {
                        title: t('roles.module'), key: 'module', fixed: 'left', width: 220,
                        render: (_, m) => {
                          const codes = m.actions.map((a) => `${m.code}.${a}`)
                          const on = codes.filter((c) => selected.permissions.includes(c)).length
                          return (
                            <Checkbox disabled={!canEdit} checked={on === codes.length} indeterminate={on > 0 && on < codes.length}
                              onChange={(e) => toggleModule(m.code, m.actions, e.target.checked)}>
                              {lang === 'ru' ? m.name_ru : m.name_ro}
                            </Checkbox>
                          )
                        },
                      },
                      ...allActions.map((action) => ({
                        title: label(catalog.actions[action]),
                        key: action,
                        align: 'center' as const,
                        width: 100,
                        render: (_: unknown, m: PermissionCatalog['modules'][number]) =>
                          m.actions.includes(action) ? (
                            <Checkbox disabled={!canEdit} checked={selected.permissions.includes(`${m.code}.${action}`)}
                              onChange={(e) => togglePerm(`${m.code}.${action}`, e.target.checked)} />
                          ) : null,
                      })),
                      {
                        title: t('roles.scope'), key: 'scope', width: 170,
                        render: (_, m) => m.scoped ? (
                          <Select size="small" style={{ width: 150 }} disabled={!canEdit}
                            value={selected.data_scopes[m.code] || 'all'}
                            onChange={(v) => edit({ ...selected, data_scopes: { ...selected.data_scopes, [m.code]: v } })}
                            options={Object.entries(catalog.scopes).map(([k, v]) => ({ value: k, label: label(v) }))} />
                        ) : null,
                      },
                    ]}
                  />
                  <Typography.Title level={5} style={{ marginTop: 24 }}>{t('mainMenu.roleTitle')}</Typography.Title>
                  <Typography.Paragraph type="secondary">{t('mainMenu.roleHint')}</Typography.Paragraph>
                  <RoleMenuTree hidden={selected.menu_hidden} disabled={!canEdit} onChange={(menu_hidden) => edit({ ...selected, menu_hidden })} />
                  <Typography.Title level={5} style={{ marginTop: 24 }}>{t('roles.hiddenFields')}</Typography.Title>
                  <Typography.Paragraph type="secondary">{t('roles.hiddenFieldsHint')}</Typography.Paragraph>
                  <Space wrap>
                    {Object.entries(catalog.sensitive_fields).map(([key, names]) => (
                      <Checkbox key={key} disabled={!canEdit} checked={selected.hidden_fields.includes(key)}
                        onChange={(e) => edit({
                          ...selected,
                          hidden_fields: e.target.checked ? [...selected.hidden_fields, key] : selected.hidden_fields.filter((f) => f !== key),
                        })}>
                        {label(names)}
                      </Checkbox>
                    ))}
                  </Space>
                </>
              )}
              {selected.is_system && <Tag style={{ marginTop: 16 }} icon={<LockOutlined />}>{t('roles.system')}</Tag>}
            </Card>
          )}
        </Col>
      </Row>
    </Space>
  )
}


/** Bifele meniului pe rol: secțiunea debifată ascunde tot ce e în ea; funcția debifată — doar pe ea. La urmă — setările din
 *  Administrare → Setări (`set:<cheie>`): cea debifată nu apare în lista rolului; toate debifate — nici rândul Setări. */
function RoleMenuTree({ hidden, disabled, onChange }: { hidden: string[]; disabled: boolean; onChange: (hidden: string[]) => void }) {
  const { t, i18n } = useTranslation()
  const name = useSectionName()
  const { data } = useFetch<{ sections?: MenuSection[] }>('/settings/menu/')
  const sections = completeSections(data?.sections)
  const settings = useMemo(() => [...SETTINGS_NAV].sort((a, b) => navLabel(t, a).localeCompare(navLabel(t, b), i18n.language)), [t, i18n.language])
  const off = new Set(hidden)
  const keysOf = (s: MenuSection) => [...new Set(sectionKeys(s))]
  const checked = [
    ...sections.flatMap((s) => (off.has(`s:${s.key}`) ? [] : keysOf(s).filter((k) => !off.has(k)).map((k) => `${s.key}/${k}`))),
    ...settings.filter((i) => !off.has(i.key)).map((i) => `set:${i.key}`),
  ]
  return (
    <Tree checkable disabled={disabled} defaultExpandAll={false} selectable={false} checkedKeys={checked}
      treeData={[
        ...sections.map((s) => ({ key: `s:${s.key}`, title: name(s), children: keysOf(s).map((k) => ({ key: `${s.key}/${k}`, title: t(`menu.${k}`) })) })),
        { key: 'set:', title: t('menu.settings'), children: settings.map((i) => ({ key: `set:${i.key}`, title: navLabel(t, i) })) },
      ]}
      onCheck={(keys) => {
        const on = new Set((Array.isArray(keys) ? keys : keys.checked).map(String))
        const next: string[] = []
        const visibleAnywhere = new Set<string>()
        for (const s of sections) {
          const visible = keysOf(s).filter((k) => on.has(`${s.key}/${k}`))
          visible.forEach((k) => visibleAnywhere.add(k))
          if (!visible.length) next.push(`s:${s.key}`)
        }
        // funcția se ascunde doar dacă e debifată în toate secțiunile unde apare
        for (const k of new Set(sections.flatMap(keysOf))) if (!visibleAnywhere.has(k)) next.push(k)
        for (const i of settings) if (!on.has(`set:${i.key}`)) next.push(i.key)
        onChange(next)
      }} />
  )
}

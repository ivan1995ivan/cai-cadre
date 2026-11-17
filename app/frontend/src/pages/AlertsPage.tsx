import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Checkbox, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { MailOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import AppTable from '../components/AppTable'
import { api, errorText } from '../api/client'
import { useFetch } from '../api/hooks'
import FormLayout from '../components/FormLayout'
import { useEditGuard, useUnsavedGuard } from '../components/UnsavedGuard'

export interface AlertRow {
  kind: string
  key: string
  title: string
  text: string
  due: string
  days: number
  level: 'info' | 'task' | 'warning' | 'success'
  employee: number | null
  employee_name: string
  link: string
}

export const LEVEL_COLOR: Record<string, string> = { warning: 'red', task: 'orange', success: 'green', info: 'blue' }

/** Cât a rămas până la termen: „azi”, „peste 5 zile”, „acum 3 zile”. */
export function DaysTag({ days }: { days: number }) {
  const { t } = useTranslation()
  if (days === 0) return <Tag color="red">{t('al.today')}</Tag>
  if (days < 0) return <Tag color="red">{t('al.ago', { count: -days })}</Tag>
  return <Tag color={days <= 7 ? 'orange' : 'default'}>{t('al.in', { count: days })}</Tag>
}

/** Termene și alerte: lista „de făcut” a cadrelor, contabilității și șefilor de secție (setările notificărilor și poșta sunt
 *  la Administrare → Setări). */
export default function AlertsPage() {
  const { t } = useTranslation()
  return <Card title={t('menu.alerts')}><AlertList /></Card>
}

/** Setarea termenelor și alertelor (Administrare → Setări): ce se urmărește, cu câte zile înainte, vârsta de pensionare. */
export function AlertSettingsPage({ title }: { title: string }) {
  return <Card title={title}><AlertSettings /></Card>
}

/** Poșta pentru notificări și fluturași (Administrare → Setări). */
export function SmtpSettingsPage({ title }: { title: string }) {
  return <Card title={title}><SmtpSettings /></Card>
}

function AlertList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [kind, setKind] = useState<string | undefined>()
  const { data, loading } = useFetch<{ rows: AlertRow[]; counts: Record<string, number> }>('/alerts/')
  const rows = (data?.rows ?? []).filter((r) => !kind || r.kind === kind)
  const counts = data?.counts ?? {}
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select allowClear style={{ width: 340 }} placeholder={t('al.allKinds')} value={kind} onChange={setKind}
          options={Object.entries(counts).map(([k, n]) => ({ value: k, label: `${t(`al.kinds.${k}`)} (${n})` }))} />
        <Typography.Text type="secondary">{t('al.listHint')}</Typography.Text>
      </Space>
      <AppTable<AlertRow> rowKey="key" size="small" loading={loading} dataSource={rows} exportName={t('menu.alerts')}
        pagination={{ pageSize: 50, showTotal: (n) => t('common.total', { count: n }) }}
        onRow={(r) => ({ onDoubleClick: () => r.link && navigate(r.link) })}
        columns={[
          { title: t('al.due'), dataIndex: 'due', width: 110, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: '', dataIndex: 'days', width: 120, render: (v: number) => <DaysTag days={v} /> },
          { title: t('al.kind'), dataIndex: 'kind', width: 260, render: (v: string, r) => <Tag color={LEVEL_COLOR[r.level]}>{t(`al.kinds.${v}`)}</Tag> },
          { title: t('al.what'), dataIndex: 'text', render: (v: string, r) => r.link
            ? <span className="report-drill" style={{ cursor: 'pointer' }} onClick={() => navigate(r.link)}>{v}</span> : v },
        ]} />
    </>
  )
}

interface AlertSettingsData {
  retirement_men: number
  retirement_women: number
  email_digest: boolean
  kinds: Record<string, { audience: string[] }>
  [k: string]: unknown
}

function AlertSettings() {
  const { t } = useTranslation()
  const { data, reload } = useFetch<AlertSettingsData>('/alerts/settings/')
  const [draft, setDraft] = useState<AlertSettingsData | null>(null)
  useEffect(() => { if (data) setDraft(data) }, [data])
  useUnsavedGuard(!!draft && !!data && JSON.stringify(draft) !== JSON.stringify(data), () => save())
  if (!draft) return null
  const kinds = Object.keys(draft.kinds)
  const setKind = (k: string, patch: Record<string, unknown>) => setDraft({ ...draft, [k]: { ...(draft[k] as object), ...patch } })
  const save = async () => {
    try {
      await api.put('/alerts/settings/', draft)
      message.success(t('common.saved'))
      await reload()
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  const runNow = async () => {
    try {
      const r = await api.post('/alerts/run/')
      message.success(t('al.sent', { count: r.data.notified, emails: r.data.emails }))
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={16}>
      <Typography.Text type="secondary">{t('al.settingsHint')}</Typography.Text>
      <Table size="small" rowKey="k" pagination={false} style={{ maxWidth: 900 }}
        dataSource={kinds.map((k) => ({ k, ...(draft[k] as { enabled: boolean; days: number }) }))}
        columns={[
          { title: t('al.kind'), dataIndex: 'k', render: (k: string) => t(`al.kinds.${k}`) },
          { title: t('al.enabled'), dataIndex: 'enabled', width: 90, render: (v: boolean, r) => <Switch size="small" checked={v} onChange={(x) => setKind(r.k, { enabled: x })} /> },
          { title: t('al.days'), dataIndex: 'days', width: 130, render: (v: number, r) => <InputNumber size="small" min={0} max={730} value={v} onChange={(x) => setKind(r.k, { days: x ?? 0 })} /> },
          { title: t('al.audience'), key: 'aud', width: 260, render: (_: unknown, r) => draft.kinds[r.k].audience.map((a) => <Tag key={a}>{t(`al.aud.${a}`)}</Tag>) },
        ]} />
      <Row gutter={16} style={{ maxWidth: 900 }}>
        <Col><Form.Item label={t('al.retMen')}><InputNumber min={50} max={75} value={draft.retirement_men} onChange={(v) => setDraft({ ...draft, retirement_men: v ?? 63 })} /></Form.Item></Col>
        <Col><Form.Item label={t('al.retWomen')}><InputNumber min={50} max={75} value={draft.retirement_women} onChange={(v) => setDraft({ ...draft, retirement_women: v ?? 63 })} /></Form.Item></Col>
        <Col><Form.Item label={t('al.emailDigest')}><Checkbox checked={draft.email_digest} onChange={(e) => setDraft({ ...draft, email_digest: e.target.checked })}>{t('al.emailDigestHint')}</Checkbox></Form.Item></Col>
      </Row>
      <Space>
        <Button type="primary" onClick={save}>{t('common.save')}</Button>
        <Button icon={<SendOutlined />} onClick={runNow}>{t('al.runNow')}</Button>
      </Space>
    </Space>
  )
}

function SmtpSettings() {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const { data } = useFetch<Record<string, unknown>>('/alerts/smtp/')
  const [to, setTo] = useState('')
  useEffect(() => { if (data) form.setFieldsValue(data) }, [data, form])
  const { touch, clean } = useEditGuard(() => save())
  const save = async () => {
    try {
      await api.put('/alerts/smtp/', await form.validateFields())
      message.success(t('common.saved'))
      clean()
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  const test = async () => {
    try {
      const r = await api.post('/alerts/smtp/test/', { to })
      message.success(t('al.smtp.testOk', { to: r.data.sent }))
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <Form form={form} layout="vertical" style={{ maxWidth: 640 }} onValuesChange={touch}>
      <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('al.smtp.hint')} />
      <Form.Item name="enabled" valuePropName="checked"><Checkbox>{t('al.smtp.enabled')}</Checkbox></Form.Item>
      <FormLayout formKey="smtp"><Row gutter={12}>
        <Col xs={24} md={16}><Form.Item name="host" label={t('al.smtp.host')}><Input placeholder="smtp.gmail.com" /></Form.Item></Col>
        <Col xs={24} md={8}><Form.Item name="port" label={t('al.smtp.port')}><InputNumber min={1} max={65535} style={{ width: '100%' }} /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="username" label={t('al.smtp.username')}><Input /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="password" label={t('al.smtp.password')}><Input.Password /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="from_email" label={t('al.smtp.from')}><Input placeholder="cadre@spital.md" /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="use_tls" valuePropName="checked" label=" "><Checkbox>TLS</Checkbox></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="use_ssl" valuePropName="checked" label=" "><Checkbox>SSL</Checkbox></Form.Item></Col>
      </Row></FormLayout>
      <Space wrap>
        <Button type="primary" onClick={save}>{t('common.save')}</Button>
        <Input style={{ width: 240 }} placeholder={t('al.smtp.testTo')} value={to} onChange={(e) => setTo(e.target.value)} />
        <Button icon={<MailOutlined />} onClick={test}>{t('al.smtp.test')}</Button>
      </Space>
    </Form>
  )
}

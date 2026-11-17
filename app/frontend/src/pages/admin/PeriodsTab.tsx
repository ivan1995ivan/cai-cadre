import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Col, DatePicker, Row, Select, Space, TimePicker, Typography, message } from 'antd'
import Table from '../../components/AppTable'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api, errorText } from '../../api/client'
import { useCachedList } from '../../api/hooks'
import type { UserLookup } from '../../api/crm'

interface PeriodSettings {
  doc_times: Record<'receipt' | 'internal' | 'issue', string>
  closing: { date: string | null; modules: Record<string, string>; users: Record<string, string> }
  modules: string[]
}

const KINDS = ['receipt', 'internal', 'issue'] as const

/** Constante → Perioade: ora documentelor după tip și data interzicerii modificării (general, pe module, pe utilizatori). */
export default function PeriodsTab({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation()
  const users = useCachedList<UserLookup>('/user-lookup/')
  const [data, setData] = useState<PeriodSettings | null>(null)
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    api.get<PeriodSettings>('/settings/periods/').then((r) => setData(r.data))
  }, [])
  if (!data) return null

  const setClosing = (patch: Partial<PeriodSettings['closing']>) => setData({ ...data, closing: { ...data.closing, ...patch } })
  const datePicker = (value: string | null | undefined, onChange: (v: string) => void, placeholder?: string) => (
    <DatePicker format="DD.MM.YYYY" disabled={!canEdit} placeholder={placeholder} value={value ? dayjs(value) : null}
      onChange={(d) => onChange(d ? d.format('YYYY-MM-DD') : '')} />
  )
  const save = async () => {
    setSaving(true)
    try {
      const { data: saved } = await api.put<PeriodSettings>('/settings/periods/', { doc_times: data.doc_times, closing: data.closing })
      setData(saved)
      message.success(t('common.saved'))
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setSaving(false)
    }
  }
  const userRows = Object.entries(data.closing.users).map(([id, date]) => ({ id, date }))

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Card title={t('periods.timesTitle')}>
        <Typography.Paragraph type="secondary">{t('periods.timesHint')}</Typography.Paragraph>
        <Row gutter={16}>
          {KINDS.map((k) => (
            <Col xs={24} md={8} key={k}>
              <Typography.Text strong>{t(`periods.kinds.${k}`)}</Typography.Text>
              <div>
                <TimePicker format="HH:mm" minuteStep={5} disabled={!canEdit} allowClear={false} value={dayjs(data.doc_times[k], 'HH:mm')}
                  onChange={(v) => v && setData({ ...data, doc_times: { ...data.doc_times, [k]: v.format('HH:mm') } })} />
              </div>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t(`periods.kindDocs.${k}`)}</Typography.Text>
            </Col>
          ))}
        </Row>
      </Card>
      <Card title={t('periods.closingTitle')}>
        <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('periods.closingHint')} />
        <Space wrap align="center" style={{ marginBottom: 16 }}>
          <Typography.Text strong>{t('periods.general')}</Typography.Text>
          {datePicker(data.closing.date, (v) => setClosing({ date: v || null }), t('periods.notClosed'))}
        </Space>
        <Typography.Title level={5}>{t('periods.byModule')}</Typography.Title>
        <Row gutter={[16, 8]} style={{ marginBottom: 16 }}>
          {data.modules.map((m) => (
            <Col xs={24} md={6} key={m}>
              <div><Typography.Text>{t(`periods.modules.${m}`)}</Typography.Text></div>
              <Space>
                {datePicker(data.closing.modules[m], (v) => setClosing({ modules: { ...data.closing.modules, [m]: v } }), t('periods.asGeneral'))}
                {m in data.closing.modules && canEdit && (
                  <Button type="text" size="small" icon={<DeleteOutlined />} onClick={() => {
                    const rest = { ...data.closing.modules }
                    delete rest[m]
                    setClosing({ modules: rest })
                  }} />
                )}
              </Space>
            </Col>
          ))}
        </Row>
        <Typography.Title level={5}>{t('periods.byUser')}</Typography.Title>
        <Table size="small" rowKey="id" pagination={false} dataSource={userRows} style={{ maxWidth: 620 }}
          locale={{ emptyText: t('periods.noUsers') }}
          columns={[
            { title: t('periods.user'), key: 'u', render: (_, r) => users.find((u) => String(u.id) === r.id)?.name ?? r.id },
            { title: t('periods.until'), key: 'd', render: (_, r) => datePicker(r.date, (v) => setClosing({ users: { ...data.closing.users, [r.id]: v } }), t('periods.noLimit')) },
            ...(canEdit ? [{ title: '', key: 'x', width: 44, render: (_: unknown, r: { id: string }) => (
              <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => {
                const rest = { ...data.closing.users }
                delete rest[r.id]
                setClosing({ users: rest })
              }} />
            ) }] : []),
          ]} />
        {canEdit && (
          <Select style={{ width: 260, marginTop: 8 }} placeholder={<><PlusOutlined /> {t('periods.addUser')}</>} value={null} showSearch optionFilterProp="label"
            options={users.filter((u) => !(String(u.id) in data.closing.users)).map((u) => ({ value: String(u.id), label: u.name }))}
            onChange={(id) => id && setClosing({ users: { ...data.closing.users, [id]: '' } })} />
        )}
      </Card>
      {canEdit && <Button type="primary" onClick={save} loading={saving}>{t('common.save')}</Button>}
    </Space>
  )
}

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Descriptions, Input, Progress, Space, Tag, Typography, message } from 'antd'
import Table from '../../components/AppTable'
import dayjs from 'dayjs'

import { api, errorText } from '../../api/client'
import type { LicenseStatus } from '../../api/types'
import { useApp } from '../../auth/AppContext'

interface SystemInfo {
  version: string
  database: { engine: string; host: string; name: string; vendor_version: string }
  license: LicenseStatus
}

const PAID = ['payroll']

export default function License() {
  const { t } = useTranslation()
  const { hasPerm, reloadMe } = useApp()
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => api.get<SystemInfo>('/system-info/').then((r) => setInfo(r.data))
  useEffect(() => {
    load()
  }, [])

  const install = async () => {
    setSaving(true)
    try {
      await api.post('/license/', { license: text })
      message.success(t('license.installed'))
      setText('')
      load()
      reloadMe()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setSaving(false)
    }
  }

  if (!info) return null
  const lic = info.license

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.license')}</Typography.Title>
      <Card title={t('license.status')}>
        {lic.mode === 'trial' && (
          <Alert type={lic.valid ? 'info' : 'error'} showIcon style={{ marginBottom: 16 }}
            title={lic.valid ? t('license.trial', { days: lic.days_left }) : t('license.trialExpired')} />
        )}
        {lic.error && <Alert type="error" showIcon title={lic.error} style={{ marginBottom: 16 }} />}
        {lic.over_limit && <Alert type="warning" showIcon style={{ marginBottom: 16 }} title={t('license.overLimit', { active: lic.active_users, max: lic.max_users })} />}
        <Descriptions column={{ xs: 1, md: 2 }} bordered size="small">
          <Descriptions.Item label={t('license.mode')}>
            <Tag color={lic.valid ? 'green' : 'red'}>{t(`license.modes.${lic.mode}`)}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('license.validUntil')}>
            {lic.valid_until ? dayjs(lic.valid_until).format('DD.MM.YYYY') : t('license.unlimited')}
          </Descriptions.Item>
          {lic.company && <Descriptions.Item label={t('license.company')}>{lic.company} {lic.idno && `(${lic.idno})`}</Descriptions.Item>}
          <Descriptions.Item label={t('license.plan')}>
            <Tag color="blue" style={{ fontSize: 14, padding: '2px 10px' }}>{lic.plan_name}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('license.users')}>
            <Space orientation="vertical" size={2} style={{ width: '100%', maxWidth: 320 }}>
              <span><b>{lic.active_users ?? 0}</b> {t('license.of')} <b>{lic.max_users}</b></span>
              <Progress size="small" showInfo={false} percent={Math.min(100, Math.round(((lic.active_users ?? 0) / Math.max(lic.max_users, 1)) * 100))}
                status={lic.over_limit ? 'exception' : undefined} />
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label={t('license.modules')} span={2}>
            {PAID.map((m) => (
              <Tag key={m} color={lic.modules.includes(m) ? 'green' : undefined} style={lic.modules.includes(m) ? undefined : { textDecoration: 'line-through' }}>
                {t(`license.moduleNames.${m}`, m)}
              </Tag>
            ))}
            <div><Typography.Text type="secondary">{t('license.baseModules')}</Typography.Text></div>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      {lic.plans && (
        <Card title={t('license.plans')}>
          <Table size="small" rowKey="key" pagination={false} dataSource={lic.plans}
            rowClassName={(p) => (p.key === lic.plan ? 'ant-table-row-selected' : '')}
            columns={[
              { title: t('license.plan'), dataIndex: 'name', render: (v: string, p) => <b>{v}{p.key === lic.plan ? ' ✓' : ''}</b> },
              { title: t('license.usersRange'), key: 'r', render: (_, p) => (p.min === p.max ? p.max : `${p.min}–${p.max}`) },
              { title: '', key: 'd', render: (_, p) => <Typography.Text type="secondary">{t(`license.planHint.${p.key}`)}</Typography.Text> },
            ]} />
          <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>{t('license.plansHint')}</Typography.Paragraph>
        </Card>
      )}
      {hasPerm('settings.edit') && (
        <Card title={t('license.enter')}>
          <Input.TextArea rows={4} value={text} onChange={(e) => setText(e.target.value)} placeholder={t('license.placeholder')} />
          <Button type="primary" style={{ marginTop: 12 }} onClick={install} loading={saving} disabled={!text.trim()}>
            {t('license.activate')}
          </Button>
        </Card>
      )}
      <Card title={t('license.system')}>
        <Descriptions column={{ xs: 1, md: 2 }} size="small">
          <Descriptions.Item label={t('license.version')}>{info.version}</Descriptions.Item>
          <Descriptions.Item label={t('license.database')}>{info.database.engine}</Descriptions.Item>
          {info.database.host && <Descriptions.Item label={t('setup.host')}>{info.database.host}</Descriptions.Item>}
          <Descriptions.Item label={t('setup.dbName')}>{info.database.name}</Descriptions.Item>
          <Descriptions.Item label={t('license.dbVersion')}>{info.database.vendor_version}</Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  )
}

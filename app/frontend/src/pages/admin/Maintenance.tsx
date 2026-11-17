import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert, Button, Card, Col, Descriptions, Input, InputNumber, Popconfirm, Row, Space, Switch, Tag, Typography, Upload, message,
} from 'antd'
import Table from '../../components/AppTable'
import { CloudDownloadOutlined, DeleteOutlined, DownloadOutlined, SaveOutlined, UploadOutlined } from '@ant-design/icons'
import axios from 'axios'
import dayjs from 'dayjs'

import { api, errorText } from '../../api/client'
import { useApp } from '../../auth/AppContext'

interface BackupItem { name: string; size: number; reason: string; method: string; created: string }
interface BackupConfig { daily: boolean; keep: number; hour: number; last_daily?: string }
interface Release { version: string; notes_ro: string; notes_ru: string; from_version?: string }
interface UpdatesState {
  version: string; pending: Release | null; last: { version: string; from_version: string } | null
  rollback_versions: string[]; feed_url: string; docker: boolean
}

const size = (bytes: number) => (bytes > 1 << 20 ? `${(bytes / (1 << 20)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`)

/** Administrare → Întreținere: copiile de rezervă și actualizările programului. */
export default function Maintenance() {
  const { t } = useTranslation()
  const { lang, hasPerm } = useApp()
  const canEdit = hasPerm('settings.edit')
  const [items, setItems] = useState<BackupItem[]>([])
  const [cfg, setCfg] = useState<BackupConfig | null>(null)
  const [dir, setDir] = useState('')
  const [busy, setBusy] = useState(false)
  const [updates, setUpdates] = useState<UpdatesState | null>(null)
  const [feed, setFeed] = useState('')
  const [check, setCheck] = useState<{ latest: string; newer: boolean; notes_ro: string; notes_ru: string } | null>(null)
  const [restarting, setRestarting] = useState(false)

  const load = useCallback(() => {
    api.get<{ items: BackupItem[]; config: BackupConfig; dir: string }>('/system/backups/').then((r) => {
      setItems(r.data.items)
      setCfg(r.data.config)
      setDir(r.data.dir)
    })
    api.get<UpdatesState>('/system/updates/').then((r) => { setUpdates(r.data); setFeed(r.data.feed_url) })
  }, [])
  useEffect(load, [load])

  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true)
    try {
      await fn()
      if (ok) message.success(ok)
      load()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const download = async (name: string) => {
    const { data } = await api.get(`/system/backups/${name}/`, { responseType: 'blob' })
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  }

  const install = async () => {
    setBusy(true)
    try {
      await api.post('/system/updates/install/')
      setRestarting(true)
      // serverul se oprește, aplică pachetul și pornește din nou: așteptăm să răspundă
      const started = Date.now()
      await new Promise((r) => setTimeout(r, 4000))
      while (Date.now() - started < 10 * 60 * 1000) {
        try {
          const { data } = await axios.get('/api/setup/status/', { timeout: 3000 })
          if (data.installed) {
            window.location.reload()
            return
          }
        } catch {
          // încă repornește
        }
        await new Promise((r) => setTimeout(r, 2000))
      }
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const notes = (r: { notes_ro: string; notes_ru: string }) => (lang === 'ru' ? r.notes_ru || r.notes_ro : r.notes_ro)

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.maintenance')}</Typography.Title>
      {restarting && <Alert type="info" showIcon title={t('maintenance.restarting')} />}
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Card title={t('maintenance.backups')} extra={canEdit && (
            <Button type="primary" icon={<SaveOutlined />} loading={busy} onClick={() => run(() => api.post('/system/backups/'), t('maintenance.backupDone'))}>
              {t('maintenance.backupNow')}
            </Button>
          )}>
            <Typography.Paragraph type="secondary">{t('maintenance.backupsHint')}</Typography.Paragraph>
            {cfg && canEdit && (
              <Space wrap style={{ marginBottom: 12 }}>
                <Space><Switch checked={cfg.daily} onChange={(v) => setCfg({ ...cfg, daily: v })} />{t('maintenance.daily')}</Space>
                <span>{t('maintenance.after')}</span>
                <InputNumber min={0} max={23} value={cfg.hour} onChange={(v) => setCfg({ ...cfg, hour: Number(v ?? 2) })} addonAfter=":00" style={{ width: 110 }} />
                <span>{t('maintenance.keep')}</span>
                <InputNumber min={1} max={365} value={cfg.keep} onChange={(v) => setCfg({ ...cfg, keep: Number(v ?? 14) })} style={{ width: 80 }} />
                <Button onClick={() => run(() => api.put('/system/backups/', cfg), t('common.saved'))}>{t('common.save')}</Button>
              </Space>
            )}
            <Table<BackupItem> size="small" rowKey="name" dataSource={items} pagination={{ pageSize: 10, hideOnSinglePage: true }} columns={[
              { title: t('common.date'), dataIndex: 'created', width: 150, render: (v) => dayjs(v).format('DD.MM.YYYY HH:mm') },
              { title: t('maintenance.kind'), dataIndex: 'reason', width: 140, render: (v: string) => <Tag>{t(`maintenance.reasons.${v}`, v)}</Tag> },
              { title: t('maintenance.method'), dataIndex: 'method', width: 120, render: (v: string) => t(`maintenance.methods.${v}`, v) },
              { title: t('maintenance.size'), dataIndex: 'size', width: 90, align: 'right', render: size },
              { title: '', key: 'x', width: 90, render: (_, b) => canEdit && (
                <Space size={0}>
                  <Button type="text" icon={<DownloadOutlined />} onClick={() => download(b.name)} />
                  <Popconfirm title={t('maintenance.deleteConfirm')} onConfirm={() => run(() => api.delete(`/system/backups/${b.name}/`))}>
                    <Button type="text" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              ) },
            ]} />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('maintenance.folder')}: {dir}</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card title={t('maintenance.updates')}>
            {updates && (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label={t('license.version')}><b>{updates.version}</b></Descriptions.Item>
                  {updates.last && (
                    <Descriptions.Item label={t('maintenance.lastUpdate')}>{updates.last.from_version} → {updates.last.version}</Descriptions.Item>
                  )}
                </Descriptions>
                {updates.docker ? <Alert type="info" showIcon title={t('maintenance.docker')} /> : updates.pending ? (
                  <Alert type="success" showIcon title={t('maintenance.pending', { version: updates.pending.version })}
                    description={<>
                      {notes(updates.pending) && <div style={{ whiteSpace: 'pre-wrap', marginBottom: 8 }}>{notes(updates.pending)}</div>}
                      {canEdit && (
                        <Space wrap>
                          <Popconfirm title={t('maintenance.installConfirm')} onConfirm={install}>
                            <Button type="primary" loading={busy || restarting}>{t('maintenance.install')}</Button>
                          </Popconfirm>
                          <Button onClick={() => run(() => api.delete('/system/updates/'))}>{t('common.cancel')}</Button>
                        </Space>
                      )}
                    </>} />
                ) : canEdit && (
                  <Upload accept=".zip" showUploadList={false} beforeUpload={(file) => {
                    const form = new FormData()
                    form.append('package', file)
                    run(() => api.post('/system/updates/upload/', form, { timeout: 10 * 60 * 1000 }), t('maintenance.uploaded'))
                    return false
                  }}>
                    <Button icon={<UploadOutlined />} loading={busy}>{t('maintenance.upload')}</Button>
                  </Upload>
                )}
                <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>{t('maintenance.updatesHint')}</Typography.Paragraph>
                {canEdit && (
                  <>
                    <Typography.Text strong>{t('maintenance.feed')}</Typography.Text>
                    <Space.Compact style={{ width: '100%' }}>
                      <Input value={feed} onChange={(e) => setFeed(e.target.value)} placeholder="https://..." />
                      <Button onClick={() => run(() => api.put('/system/updates/', { feed_url: feed }), t('common.saved'))}>{t('common.save')}</Button>
                    </Space.Compact>
                    {updates.feed_url && (
                      <Space wrap>
                        <Button onClick={() => run(async () => setCheck((await api.post('/system/updates/check/', {})).data))}>{t('maintenance.check')}</Button>
                        {check?.newer && !updates.pending && (
                          <Button type="primary" icon={<CloudDownloadOutlined />} loading={busy}
                            onClick={() => run(() => api.post('/system/updates/check/', { download: true }, { timeout: 10 * 60 * 1000 }), t('maintenance.uploaded'))}>
                            {t('maintenance.download', { version: check.latest })}
                          </Button>
                        )}
                        {check && !check.newer && <Typography.Text type="secondary">{t('maintenance.upToDate')}</Typography.Text>}
                      </Space>
                    )}
                  </>
                )}
                {updates.rollback_versions.length > 0 && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {t('maintenance.rollbackKept', { versions: updates.rollback_versions.join(', ') })}
                  </Typography.Text>
                )}
              </Space>
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

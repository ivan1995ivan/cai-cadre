import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Col, Popconfirm, Row, Space, Statistic, Switch, Tag, Typography, message } from 'antd'
import { DesktopOutlined, MobileOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons'
import Table from '../../components/AppTable'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

import { api, errorText } from '../../api/client'
import { useApp } from '../../auth/AppContext'

dayjs.extend(relativeTime)

interface SessionUser { id: number; name: string; username: string; email: string; role_ro: string; role_ru: string; is_admin: boolean }
interface SessionRow {
  sid: string; current: boolean; ip: string; device: string; user_agent: string
  created_at: string; last_seen: string; last_path: string; user: SessionUser
}
interface OnlineData {
  now: string; online_minutes: number
  stats: { online: number; worked_today: number; sessions: number; accounts: number }
  online: SessionRow[]; idle: SessionRow[]
}

/** Cine e online: oamenii cu programul deschis în ultimele minute și sesiunile intrate fără semn de viață. „În timp real”
 *  (pornit de la deschidere) reîmprospătează pagina la 10 s, cât fila browserului e în față. */
const LIVE_EVERY = 10_000
export default function Online() {
  const { t, i18n } = useTranslation()
  const { hasPerm } = useApp()
  const [data, setData] = useState<OnlineData | null>(null)
  const [loading, setLoading] = useState(false)
  const canClose = hasPerm('users.edit')
  const [live, setLive] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData((await api.get<OnlineData>('/online/')).data)
    } catch (e) {
      message.error(errorText(e), 8)
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (!live) return
    const tick = () => { if (document.visibilityState === 'visible') load() }
    const timer = setInterval(tick, LIVE_EVERY)
    document.addEventListener('visibilitychange', tick)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', tick)
    }
  }, [live, load])

  const close = async (sid: string) => {
    try {
      await api.post('/online/', { sid })
      message.success(t('online.closed'))
      load()
    } catch (e) {
      message.error(errorText(e), 8)
    }
  }

  const lastSeen = (iso: string) => {
    const d = dayjs(iso)
    const minutes = dayjs().diff(d, 'minute')
    if (minutes < 1) return <Typography.Text style={{ color: '#2E9E5B', fontWeight: 600 }}>{t('online.justNow')}</Typography.Text>
    if (minutes < 24 * 60) return <Typography.Text strong>{d.fromNow()}</Typography.Text>
    return d.format('DD.MM.YYYY HH:mm')
  }
  const role = (u: SessionUser) => (i18n.language === 'ru' ? u.role_ru : u.role_ro) || (u.is_admin ? t('online.admin') : '')

  const columns = (withClose: boolean) => [
    {
      title: t('online.person'), dataIndex: ['user', 'name'], key: 'user', width: 220,
      render: (_: unknown, r: SessionRow) => (
        <div>
          <Typography.Text strong>{r.user.name}</Typography.Text>
          <div style={{ fontSize: 12 }}>
            <Typography.Text type="secondary">{role(r.user)}</Typography.Text>
            {r.user.email && <Typography.Text type="secondary"> · {r.user.email}</Typography.Text>}
          </div>
        </div>
      ),
    },
    {
      title: t('online.device'), dataIndex: 'device', key: 'device', width: 260,
      render: (_: unknown, r: SessionRow) => (
        <Space align="start">
          {r.device.startsWith('Telefon') ? <MobileOutlined style={{ fontSize: 18 }} /> : <DesktopOutlined style={{ fontSize: 18 }} />}
          <div>
            <div>{r.device || '—'}</div>
            {r.user_agent && (
              <details style={{ fontSize: 12 }}>
                <summary style={{ cursor: 'pointer', color: 'var(--ant-color-text-secondary)' }}>{t('online.fullAgent')}</summary>
                <Typography.Text type="secondary" style={{ wordBreak: 'break-all' }}>{r.user_agent}</Typography.Text>
              </details>
            )}
          </div>
        </Space>
      ),
    },
    { title: t('online.ip'), dataIndex: 'ip', key: 'ip', width: 150, render: (v: string) => <Typography.Text code>{v || '—'}</Typography.Text> },
    { title: t('online.lastSeen'), dataIndex: 'last_seen', key: 'last_seen', width: 170, render: (v: string) => lastSeen(v) },
    {
      title: t('online.page'), dataIndex: 'last_path', key: 'last_path',
      render: (v: string) => <Typography.Text type="secondary" style={{ fontFamily: 'monospace', fontSize: 12 }}>{v || '—'}</Typography.Text>,
    },
    { title: t('online.signedIn'), dataIndex: 'created_at', key: 'created_at', width: 170, render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm') },
    {
      title: '', key: 'actions', width: 130, align: 'right' as const,
      render: (_: unknown, r: SessionRow) => r.current
        ? <Tag color="gold">{t('online.yourSession')}</Tag>
        : withClose && canClose
          ? (
            <Popconfirm title={t('online.closeConfirm', { name: r.user.name })} okText={t('online.close')} onConfirm={() => close(r.sid)}>
              <Button size="small" danger icon={<StopOutlined />}>{t('online.close')}</Button>
            </Popconfirm>
          )
          : null,
    },
  ]

  const stats = data?.stats
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.online')}</Typography.Title>
        <Space>
          <Switch checked={live} onChange={setLive} /> <Typography.Text>{t('online.live')}</Typography.Text>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading && !live}>{t('online.refresh')}</Button>
        </Space>
      </Space>
      <Typography.Text type="secondary">
        {t(live ? 'online.introLive' : 'online.intro', { minutes: data?.online_minutes ?? 3,
          at: data ? dayjs(data.now).format(live ? 'HH:mm:ss' : 'DD.MM.YYYY HH:mm') : '…' })}
      </Typography.Text>
      <Row gutter={[12, 12]}>
        {([
          ['online', stats?.online, t('online.statOnline'), t('online.statOnlineHint')],
          ['worked', stats?.worked_today, t('online.statToday'), t('online.statTodayHint')],
          ['sessions', stats?.sessions, t('online.statSessions'), t('online.statSessionsHint')],
          ['accounts', stats?.accounts, t('online.statAccounts'), t('online.statAccountsHint')],
        ] as const).map(([key, value, title, hint]) => (
          <Col key={key} xs={12} lg={6}>
            <Card size="small">
              <Statistic title={title} value={value ?? '—'} />
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>{hint}</Typography.Text>
            </Card>
          </Col>
        ))}
      </Row>

      <Card size="small" title={<Space><span style={{ width: 8, height: 8, borderRadius: 4, background: '#2E9E5B', display: 'inline-block' }} />{t('online.nowTitle', { count: data?.online.length ?? 0 })}</Space>}>
        <Table<SessionRow> rowKey="sid" size="small" loading={loading} dataSource={data?.online} pagination={false} scroll={{ x: 1000 }}
          columns={columns(false)} locale={{ emptyText: t('online.nobody') }} />
      </Card>

      <Card size="small" title={t('online.idleTitle', { count: data?.idle.length ?? 0 })}>
        <Alert type="info" showIcon style={{ marginBottom: 12 }} message={t('online.idleText')} description={t('online.idleText2')} />
        <Table<SessionRow> rowKey="sid" size="small" loading={loading} dataSource={data?.idle} pagination={false} scroll={{ x: 1000 }}
          columns={columns(true)} locale={{ emptyText: t('online.noIdle') }} />
      </Card>
    </Space>
  )
}

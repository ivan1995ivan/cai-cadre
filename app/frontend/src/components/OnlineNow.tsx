import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Badge, Button, Empty, Popover, Space, Tooltip, Typography } from 'antd'
import { DesktopOutlined, MobileOutlined, TeamOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api } from '../api/client'
import { useApp } from '../auth/AppContext'

interface Person { id: number; name: string; device: string; last_seen: string; current: boolean }
interface OnlineReply { online: { user: { id: number; name: string }; device: string; last_seen: string; current: boolean }[] }

const EVERY = 30_000 // reîmprospătarea în antet; pagina „Cine e online” — la 10 s

/**
 * „● N online” în antet (pentru cine vede utilizatorii): câți oameni au programul deschis acum și, la clic, cine — cu
 * ultimul semn și dispozitivul; legătura duce la „Cine e online”. Se reîmprospătează la 30 s, cât fila browserului e
 * în față, și la deschiderea listei.
 */
export default function OnlineNow() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const navigate = useNavigate()
  const allowed = hasPerm('users.view')
  const [people, setPeople] = useState<Person[] | null>(null)
  const [open, setOpen] = useState(false)

  const load = useCallback(() => {
    if (!allowed || document.visibilityState !== 'visible') return
    api.get<OnlineReply>('/online/').then((r) => {
      const byUser = new Map<number, Person>()
      for (const s of r.data.online) {
        const old = byUser.get(s.user.id)
        if (!old || s.last_seen > old.last_seen) {
          byUser.set(s.user.id, { id: s.user.id, name: s.user.name, device: s.device, last_seen: s.last_seen, current: s.current || !!old?.current })
        }
      }
      setPeople([...byUser.values()].sort((a, b) => a.name.localeCompare(b.name)))
    }).catch(() => {})
  }, [allowed])

  useEffect(() => {
    load()
    const timer = setInterval(load, EVERY)
    document.addEventListener('visibilitychange', load)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', load)
    }
  }, [load])

  if (!allowed || people === null) return null
  const ago = (iso: string) => {
    const m = dayjs().diff(dayjs(iso), 'minute')
    return m < 1 ? t('online.justNow') : t('online.minutesAgo', { count: m })
  }
  const list = (
    <div style={{ width: 320, maxHeight: 360, overflowY: 'auto' }}>
      {people.length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('online.nobody')} /> : people.map((p) => (
        <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderBottom: '1px solid var(--ant-color-split)' }}>
          <Badge status="success" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <Typography.Text strong ellipsis style={{ display: 'block' }}>{p.name}{p.current ? ` (${t('online.you')})` : ''}</Typography.Text>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {p.device.startsWith('Telefon') ? <MobileOutlined /> : <DesktopOutlined />} {p.device || '—'} · {ago(p.last_seen)}
            </Typography.Text>
          </div>
        </div>
      ))}
      <Button type="link" size="small" style={{ paddingInline: 0, marginTop: 6 }} onClick={() => { setOpen(false); navigate('/admin/online') }}>
        {t('online.allSessions')}
      </Button>
    </div>
  )
  return (
    <Popover open={open} onOpenChange={(v) => { setOpen(v); if (v) load() }} trigger="click" placement="bottomRight"
      title={t('online.nowTitle', { count: people.length })} content={list}>
      <Tooltip title={open ? '' : t('online.headerHint')}>
        <Button type="text" aria-label={t('online.headerHint')}>
          <Space size={4}>
            <Badge status="success" />
            <TeamOutlined />
            <span>{people.length}</span>
          </Space>
        </Button>
      </Tooltip>
    </Popover>
  )
}

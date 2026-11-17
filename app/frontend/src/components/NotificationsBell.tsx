import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Badge, Button, Empty, List, Popover, Space, Tag, Typography } from 'antd'
import { BellOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

import { api, type Paged } from '../api/client'
import type { Notification } from '../api/types'
import { MessageColleagues } from './Conversation'

dayjs.extend(relativeTime)

const LEVEL_COLOR: Record<Notification['level'], string> = {
  info: 'blue',
  task: 'orange',
  warning: 'red',
  success: 'green',
}

export default function NotificationsBell() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [count, setCount] = useState(0)
  const [items, setItems] = useState<Notification[]>([])
  const [open, setOpen] = useState(false)
  const [writing, setWriting] = useState(false)

  const loadCount = useCallback(() => {
    api.get('/notifications/count/').then((r) => setCount(r.data.unread)).catch(() => {})
  }, [])

  useEffect(() => {
    loadCount()
    const timer = setInterval(loadCount, 60000)
    return () => clearInterval(timer)
  }, [loadCount])

  useEffect(() => {
    if (open) api.get<Paged<Notification>>('/notifications/', { params: { page_size: 20 } }).then((r) => setItems(r.data.results))
  }, [open])

  const openItem = async (n: Notification) => {
    if (!n.is_read) {
      await api.post(`/notifications/${n.id}/read/`)
      setItems((list) => list.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)))
      loadCount()
    }
    if (n.link) {
      setOpen(false)
      navigate(n.link)
    }
  }

  const readAll = async () => {
    await api.post('/notifications/read-all/')
    setItems((list) => list.map((x) => ({ ...x, is_read: true })))
    setCount(0)
  }

  const content = (
    <div style={{ width: 360, maxWidth: '85vw' }}>
      {items.length === 0 ? (
        <Empty description={t('header.noNotifications')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          size="small"
          dataSource={items}
          style={{ maxHeight: 420, overflow: 'auto' }}
          renderItem={(n) => (
            <List.Item onClick={() => openItem(n)} style={{ cursor: 'pointer', opacity: n.is_read ? 0.6 : 1 }}>
              <Space orientation="vertical" size={0} style={{ width: '100%' }}>
                <Space>
                  <Tag color={LEVEL_COLOR[n.level]}>{t(`notifications.level.${n.level}`)}</Tag>
                  <Typography.Text strong={!n.is_read}>{n.title}</Typography.Text>
                </Space>
                {n.message && <Typography.Text type="secondary">{n.message}</Typography.Text>}
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>{dayjs(n.created_at).fromNow()}</Typography.Text>
              </Space>
            </List.Item>
          )}
        />
      )}
    </div>
  )

  return (
    <>
    <MessageColleagues open={writing} onClose={() => setWriting(false)} />
    <Popover
      open={open}
      onOpenChange={setOpen}
      trigger="click"
      placement="bottomRight"
      title={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <span>{t('header.notifications')}</span>
          <Space size={0}>
            <Button type="link" size="small" icon={<SendOutlined />} onClick={() => { setOpen(false); setWriting(true) }}>{t('talk.toColleagues')}</Button>
            {count > 0 && <Button type="link" size="small" onClick={readAll}>{t('header.markAllRead')}</Button>}
          </Space>
        </Space>
      }
      content={content}
    >
      <Badge count={count} size="small">
        <Button type="text" icon={<BellOutlined />} aria-label={t('header.notifications')} />
      </Badge>
    </Popover>
    </>
  )
}

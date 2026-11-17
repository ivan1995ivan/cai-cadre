import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { Badge, Button, Checkbox, Drawer, Empty, Input, List, Modal, Popconfirm, Select, Space, Typography, message } from 'antd'
import { CommentOutlined, DeleteOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api, errorText } from '../api/client'
import { useCachedList, useFetch } from '../api/hooks'
import type { UserLookup } from '../api/crm'

interface CommentRow { id: number; author: string; author_id: number | null; text: string; created_at: string; mentions: string[]; can_delete: boolean }

/**
 * Conversația despre un obiect: mesajele colegilor și un câmp pentru mesaj nou, cu menționarea colegilor (din listă sau
 * scriind @utilizator). Cei care au mai scris, responsabilul obiectului și cei menționați primesc notificare.
 */
export default function Conversation({ model, id }: { model: string; id: number }) {
  const { t } = useTranslation()
  const location = useLocation()
  const users = useCachedList<UserLookup>('/user-lookup/')
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<CommentRow[]>([])
  const [text, setText] = useState('')
  const [mentions, setMentions] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const counter = useFetch<{ count: number }>('/comments/', { model, id, count: 1 })

  useEffect(() => {
    if (open) api.get<CommentRow[]>('/comments/', { params: { model, id } }).then((r) => setRows(r.data)).catch(() => setRows([]))
  }, [open, model, id])

  const send = async () => {
    setBusy(true)
    try {
      const { data } = await api.post<CommentRow[]>('/comments/', { model, id, text, mentions, link: location.pathname })
      setRows(data)
      setText('')
      setMentions([])
      counter.reload()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  const remove = async (row: CommentRow) => {
    try {
      await api.delete('/comments/', { params: { comment: row.id } })
      setRows((cur) => cur.filter((r) => r.id !== row.id))
      counter.reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <>
      <Badge count={counter.data?.count ?? 0} size="small" offset={[-4, 4]}>
        <Button icon={<CommentOutlined />} onClick={() => setOpen(true)}>{t('talk.button')}</Button>
      </Badge>
      <Drawer open={open} onClose={() => setOpen(false)} title={t('talk.title')} size="large">
        <Space orientation="vertical" style={{ width: '100%' }} size="middle">
          {rows.length === 0 ? <Empty description={t('talk.empty')} /> : (
            <List dataSource={rows} renderItem={(r) => (
              <List.Item actions={r.can_delete ? [
                <Popconfirm key="d" title={t('common.confirmDelete')} onConfirm={() => remove(r)}><Button type="text" size="small" danger icon={<DeleteOutlined />} /></Popconfirm>,
              ] : []}>
                <List.Item.Meta
                  title={<Space wrap><b>{r.author}</b><Typography.Text type="secondary" style={{ fontSize: 12 }}>{dayjs(r.created_at).format('DD.MM.YYYY HH:mm')}</Typography.Text>
                    {r.mentions.length > 0 && <Typography.Text type="secondary" style={{ fontSize: 12 }}>→ {r.mentions.join(', ')}</Typography.Text>}</Space>}
                  description={<Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>{r.text}</Typography.Paragraph>} />
              </List.Item>
            )} />
          )}
          <Input.TextArea rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder={t('talk.placeholder')}
            onPressEnter={(e) => { if (e.ctrlKey && text.trim()) send() }} />
          <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
            <Select mode="multiple" allowClear showSearch optionFilterProp="label" placeholder={t('talk.mention')} style={{ minWidth: 280 }}
              value={mentions} onChange={setMentions} options={users.map((u) => ({ value: u.id, label: u.name }))} />
            <Button type="primary" icon={<SendOutlined />} disabled={!text.trim()} loading={busy} onClick={send}>{t('talk.send')}</Button>
          </Space>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('talk.hint')}</Typography.Text>
        </Space>
      </Drawer>
    </>
  )
}

/** Mesaj către colegi (din clopoțel): utilizatorii, textul și, la alegere, legătura spre pagina curentă. */
export function MessageColleagues({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const location = useLocation()
  const users = useCachedList<UserLookup>('/user-lookup/', open)
  const [to, setTo] = useState<number[]>([])
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [withLink, setWithLink] = useState(true)
  const [busy, setBusy] = useState(false)
  const send = async () => {
    setBusy(true)
    try {
      await api.post('/notifications/send/', { users: to, title, message: body, link: withLink ? location.pathname : '' })
      message.success(t('talk.messageSent'))
      setTo([])
      setTitle('')
      setBody('')
      onClose()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Modal open={open} onCancel={onClose} onOk={send} okText={t('talk.send')} okButtonProps={{ disabled: !to.length || !title.trim(), loading: busy }}
      title={t('talk.toColleagues')} destroyOnHidden>
      <Space orientation="vertical" style={{ width: '100%' }}>
        <Select mode="multiple" showSearch optionFilterProp="label" placeholder={t('talk.recipients')} style={{ width: '100%' }}
          value={to} onChange={setTo} options={users.map((u) => ({ value: u.id, label: u.name }))} />
        <Input placeholder={t('talk.subject')} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={150} />
        <Input.TextArea rows={3} placeholder={t('talk.text')} value={body} onChange={(e) => setBody(e.target.value)} />
        <Checkbox checked={withLink} onChange={(e) => setWithLink(e.target.checked)}>{t('talk.withLink')}</Checkbox>
      </Space>
    </Modal>
  )
}

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Drawer, Empty, Popconfirm, Space, Tag, Timeline, Typography, message } from 'antd'
import { HistoryOutlined, RollbackOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api, errorText } from '../api/client'
import { useFetch } from '../api/hooks'

interface HistoryEntry {
  id: number; timestamp: string; user: string; action: 'create' | 'update' | 'delete' | string; object_repr: string
  is_line: boolean; line_model: string; restored_from: number | null; can_restore: boolean
  changes: { field: string; label: string; old: unknown; new: unknown }[]
}

const ACTION_COLOR: Record<string, string> = { create: 'green', update: 'blue', delete: 'red' }

function show(value: unknown) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? '✓' : '✗'
  if (typeof value === 'object') return JSON.stringify(value)
  const text = String(value)
  return /^\d{4}-\d{2}-\d{2}T/.test(text) ? dayjs(text).format('DD.MM.YYYY HH:mm') : text
}

/**
 * Istoricul modificărilor unui document / clasificator: cine, când, ce câmp (valoarea veche → cea nouă), și schimbările
 * pozițiilor documentului. Administratorul poate reveni la o versiune (la ciorne și clasificatoare).
 */
export default function HistoryButton({ model, id, onRestored }: { model: string; id: number; onRestored?: () => void }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data, loading, reload } = useFetch<{ entries: HistoryEntry[]; verbose_name: string }>(open ? '/history/' : null, { model, id })
  const restore = async (entry: HistoryEntry) => {
    try {
      await api.post(`/history/${entry.id}/restore/`)
      message.success(t('history.restored'))
      reload()
      onRestored?.()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <>
      <Button icon={<HistoryOutlined />} onClick={() => setOpen(true)}>{t('history.button')}</Button>
      <Drawer open={open} onClose={() => setOpen(false)} size="large" title={`${t('history.title')}${data ? ` — ${data.verbose_name}` : ''}`}>
        {!loading && !data?.entries.length ? <Empty description={t('history.empty')} /> : (
          <Timeline items={(data?.entries ?? []).map((e) => ({
            color: ACTION_COLOR[e.action] ?? 'gray',
            children: (
              <Space orientation="vertical" size={2} style={{ width: '100%' }}>
                <Space wrap>
                  <b>{dayjs(e.timestamp).format('DD.MM.YYYY HH:mm')}</b>
                  <span>{e.user}</span>
                  <Tag color={ACTION_COLOR[e.action]}>{t(`history.actions.${e.action}`, { defaultValue: e.action })}</Tag>
                  {e.is_line && <Tag>{t('history.line')}: {e.object_repr}</Tag>}
                  {e.restored_from && <Tag color="purple">{t('history.restoredFrom', { id: e.restored_from })}</Tag>}
                  {e.can_restore && (
                    <Popconfirm title={t('history.restoreConfirm')} onConfirm={() => restore(e)}>
                      <Button size="small" type="link" icon={<RollbackOutlined />}>{t('history.restore')}</Button>
                    </Popconfirm>
                  )}
                </Space>
                {e.action === 'update' && e.changes.map((c) => (
                  <Typography.Text key={c.field} style={{ fontSize: 13 }}>
                    {c.label}: <Typography.Text delete type="secondary">{show(c.old)}</Typography.Text> → <b>{show(c.new)}</b>
                  </Typography.Text>
                ))}
                {e.action !== 'update' && !e.is_line && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>{e.object_repr}</Typography.Text>
                )}
              </Space>
            ),
          }))} />
        )}
      </Drawer>
    </>
  )
}

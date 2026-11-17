import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Empty, Popconfirm, Select, Space, Tag, Typography, message } from 'antd'
import { DeleteOutlined, LinkOutlined, ReloadOutlined, UndoOutlined } from '@ant-design/icons'

import Table from '../../components/AppTable'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'

/** Un obiect din bază, cum îl descrie serverul (apps/core/deletion.py → describe). */
interface Obj { key: string; model: string; type: string; title: string; part: string }
interface Blocked extends Obj { refs: Obj[] }

/** Unde se deschide obiectul (documentele cu formă proprie). */
const ROUTES: Record<string, string> = {
  'orders.Order': '/orders/', 'staff.Employee': '/employees/', 'org.StaffList': '/staff-list/', 'leave.LeaveSchedule': '/leave/schedule/',
  'worktime.Roster': '/worktime/rosters/', 'worktime.Timesheet': '/timesheets/', 'payroll.Payroll': '/payroll/',
  'payroll.Payment': '/payroll/payments/',
}

/**
 * Administrare → Ștergerea obiectelor marcate (ca „Удаление помеченных объектов” din 1C): lista tuturor obiectelor marcate
 * pentru ștergere, verificarea legăturilor și ștergerea de tot doar a celor pe care nu le mai folosește nimic.
 */
export default function MarkedObjects() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const canDelete = hasPerm('settings.edit')
  const { data, loading, reload } = useFetch<Obj[]>('/system/marked/')
  const [type, setType] = useState<string>()
  const [selected, setSelected] = useState<string[]>([])
  const [refs, setRefs] = useState<Record<string, Obj[]>>({})
  const [busy, setBusy] = useState(false)
  const [deleted, setDeleted] = useState<Obj[] | null>(null)

  const all = useMemo(() => data ?? [], [data])
  const types = useMemo(() => [...new Set(all.map((o) => o.model))], [all])
  const rows = type ? all.filter((o) => o.model === type) : all
  const chosen = selected.length ? selected : rows.map((o) => o.key)  // fără bife — toate cele din listă

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    try {
      await fn()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  const check = () => run(async () => {
    const r = await api.post<Record<string, Obj[]>>('/system/marked/check/', { keys: chosen })
    setRefs((cur) => ({ ...cur, ...r.data }))
    const used = Object.values(r.data).filter((x) => x.length).length
    message.info(t('marks.checked', { free: chosen.length - used, used }))
  })
  const remove = () => run(async () => {
    const r = await api.post<{ deleted: Obj[]; blocked: Blocked[] }>('/system/marked/delete/', { keys: chosen })
    setDeleted(r.data.deleted)
    setRefs((cur) => ({ ...cur, ...Object.fromEntries(r.data.blocked.map((b) => [b.key, b.refs])) }))
    setSelected([])
    reload()
  })
  const unmark = () => run(async () => {
    const r = await api.post<{ unmarked: number }>('/system/marked/unmark/', { keys: chosen })
    message.success(t('marks.unmarked', { count: r.data.unmarked }))
    setSelected([])
    reload()
  })

  const typeOf = (o: Obj) => t(`marks.models.${o.model.replace('.', '_')}`, { defaultValue: o.type })
  const open = (o: Obj) => ROUTES[o.model] && navigate(`${ROUTES[o.model]}${o.key.split(':')[1]}`)
  const objLink = (o: Obj) => (ROUTES[o.model] ? <a onClick={() => open(o)}>{o.title}</a> : o.title)

  return (
    <Card title={t('menu.markedObjects')}>
      <Typography.Paragraph type="secondary">{t('marks.hint')}</Typography.Paragraph>
      {deleted && <Alert type={deleted.length ? 'success' : 'info'} showIcon closable onClose={() => setDeleted(null)} style={{ marginBottom: 12 }}
        title={t('marks.deleted', { count: deleted.length })}
        description={deleted.length ? deleted.slice(0, 20).map((o) => `${typeOf(o)}: ${o.title}`).join('; ') : undefined} />}
      <Space wrap style={{ marginBottom: 12 }}>
        <Select allowClear placeholder={t('marks.allTypes')} style={{ width: 260 }} value={type} onChange={(v) => { setType(v); setSelected([]) }}
          options={types.map((model) => {
            const rowsOf = all.filter((o) => o.model === model)
            return { value: model, label: `${typeOf(rowsOf[0])} (${rowsOf.length})` }
          })} />
        <Button icon={<ReloadOutlined />} onClick={reload}>{t('marks.refresh')}</Button>
        <Button icon={<LinkOutlined />} disabled={!rows.length} loading={busy} onClick={check}>{t('marks.check')}</Button>
        {canDelete && <Popconfirm title={t('marks.deleteConfirm', { count: chosen.length })} onConfirm={remove} disabled={!rows.length}>
          <Button danger type="primary" icon={<DeleteOutlined />} disabled={!rows.length} loading={busy}>
            {t(selected.length ? 'marks.deleteSelected' : 'marks.deleteAll')}</Button>
        </Popconfirm>}
        {canDelete && selected.length > 0 && <Popconfirm title={t('marks.unmarkSelectedConfirm', { count: selected.length })} onConfirm={unmark}>
          <Button icon={<UndoOutlined />} loading={busy}>{t('marks.unmarkSelected')}</Button>
        </Popconfirm>}
      </Space>
      {!loading && !all.length ? <Empty description={t('marks.empty')} /> : (
        <Table<Obj> rowKey="key" size="small" loading={loading} dataSource={rows} exportName={t('menu.markedObjects')}
          pagination={rows.length > 100 ? { pageSize: 100 } : false}
          rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys as string[]) }}
          columns={[
            { title: t('marks.type'), dataIndex: 'type', width: 220, render: (_: unknown, o) => typeOf(o) },
            { title: t('marks.object'), dataIndex: 'title', render: (_: unknown, o) => objLink(o) },
            { title: t('marks.refs'), key: 'refs', render: (_: unknown, o) => {
              const list = refs[o.key]
              if (!list) return <Typography.Text type="secondary">—</Typography.Text>
              if (!list.length) return <Tag color="green">{t('marks.free')}</Tag>
              return <Space orientation="vertical" size={0}>
                <Tag color="red">{t('marks.used', { count: list.length })}</Tag>
                {list.map((r) => <span key={`${r.key}:${r.part}`}>{typeOf(r)}: {objLink(r)}{r.part && <Typography.Text type="secondary"> ({r.part})</Typography.Text>}</span>)}
              </Space>
            } },
          ]} />
      )}
    </Card>
  )
}

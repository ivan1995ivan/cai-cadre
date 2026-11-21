import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, DatePicker, Input, InputNumber, Modal, Popconfirm, Select, Space, Spin, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  ArrowLeftOutlined, CheckOutlined, DeleteOutlined, FileAddOutlined, PrinterOutlined, RollbackOutlined, SendOutlined,
  UsergroupAddOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import PrintDialog from '../../components/PrintDialog'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import {
  PLAN_STATE_COLOR, SCHEDULE_STATUS_COLOR, fmtDays, type LeaveSchedule, type ScheduleGuest, type ScheduleReport, type ScheduleRow,
  type ScheduleWarning,
} from '../../api/leave'
import type { Order } from '../../api/orders'
import { useApp } from '../../auth/AppContext'
import { fmtRate } from '../../components/RateInput'
import { d } from './LeavePage'
import EmployeeSelect from '../../components/EmployeeSelect'
import { useTabTitle } from '../../layout/tabs'

const MONTHS = Array.from({ length: 12 }, (_, i) => i)

/** Bara anului: perioada planificată (sus) și concediile efective (jos), pe lunile anului. */
function YearBar({ year, row }: { year: number; row: ScheduleRow }) {
  const start = dayjs(`${year}-01-01`)
  const total = start.add(1, 'year').diff(start, 'day')
  const pos = (from: string, to: string) => {
    const a = Math.max(0, dayjs(from).diff(start, 'day'))
    const b = Math.min(total - 1, dayjs(to).diff(start, 'day'))
    return { left: `${(a / total) * 100}%`, width: `${(Math.max(b - a + 1, 1) / total) * 100}%` }
  }
  const planFrom = row.moved_to || row.date_from
  const planTo = row.moved_to && row.date_from && row.date_to
    ? dayjs(row.moved_to).add(dayjs(row.date_to).diff(dayjs(row.date_from), 'day'), 'day').format('YYYY-MM-DD') : row.date_to
  return (
    <div style={{ position: 'relative', height: 22, minWidth: 260, background: 'var(--ant-color-fill-quaternary)', borderRadius: 3 }}>
      {MONTHS.slice(1).map((m) => (
        <div key={m} style={{ position: 'absolute', left: `${(start.month(m).diff(start, 'day') / total) * 100}%`, top: 0, bottom: 0,
          borderLeft: '1px solid var(--ant-color-border-secondary)' }} />
      ))}
      {planFrom && planTo && <div title={`${d(planFrom)} – ${d(planTo)}`} style={{ position: 'absolute', top: 2, height: 9, borderRadius: 2,
        background: row.moved_to ? 'var(--ant-color-warning)' : 'var(--ant-color-primary)', ...pos(planFrom, planTo) }} />}
      {row.actual.map((a) => <div key={a.id} title={`${d(a.from)} – ${d(a.to)}`} style={{ position: 'absolute', bottom: 2, height: 7,
        borderRadius: 2, background: 'var(--ant-color-success)', ...pos(a.from, a.to) }} />)}
    </div>
  )
}

/** Graficul concediilor unei subdiviziuni: planificarea, verificarea suprapunerilor, aprobarea, ordinele lunare. */
export default function ScheduleEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const { data, loading, reload } = useFetch<ScheduleReport>(`/leave/schedules/${id}/report/`)
  useTabTitle(data ? { key: 'lv.sch.heading', params: { year: data.year, subdivision: data.subdivision_name } } : null)
  const [adding, setAdding] = useState<number | undefined>()
  const [printOpen, setPrintOpen] = useState(false)
  const [month, setMonth] = useState<number>(dayjs().month() + 2 > 12 ? 1 : dayjs().month() + 2)

  if (!data) return <Card loading={loading}><Spin /></Card>
  const editable = !data.deletion_mark && (data.status === 'draft' || (data.status === 'submitted' && hasPerm('leave.approve')))
  const canEdit = editable && hasPerm('leave.edit')

  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    try {
      await fn()
      if (ok) message.success(ok)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const patch = (row: ScheduleRow, values: Record<string, unknown>) =>
    run(() => api.patch(`/leave/schedule-lines/${row.id}/`, values))
  const post = (action: string, body?: unknown) => api.post<LeaveSchedule>(`/leave/schedules/${id}/${action}/`, body)

  const approve = () => {
    let by = data.approved_by
    Modal.confirm({
      title: t('lv.sch.approveTitle'),
      content: <Space orientation="vertical" style={{ width: '100%' }}>
        <Typography.Text type="secondary">{t('lv.sch.approveHint')}</Typography.Text>
        <Input defaultValue={by} placeholder={t('lv.sch.approvedByPlaceholder')} onChange={(e) => { by = e.target.value }} />
      </Space>,
      onOk: () => run(() => post('approve', { approved_by: by })),
    })
  }
  const makeOrders = () => run(async () => {
    const r = await api.post<Order>(`/leave/schedules/${id}/make-orders/`, { month })
    navigate(`/orders/${r.data.id}`)
  })
  const addLine = () => {
    if (!adding) return
    run(() => api.post('/leave/schedule-lines/', { schedule: Number(id), employee: adding, days: 28, second_part: true }))
      .then(() => setAdding(undefined))
  }

  const warningText = (w: ScheduleWarning) => {
    if (w.kind === 'balance') return t('lv.sch.warnBalance', { name: w.name, days: w.days, available: fmtDays(w.available) })
    const period = `${d(w.from)} – ${d(w.to)}`
    return t('lv.sch.warnOccupation', { period, label: w.label, count: w.count })
  }

  return (
    <Card title={<Space>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/leave/schedule')} />
      {t('lv.sch.heading', { year: data.year, subdivision: data.subdivision_name })}
      <Tag color={SCHEDULE_STATUS_COLOR[data.status]}>{data.status_label}</Tag>
    </Space>}>
      <MarkedBanner endpoint="/leave/schedules/" row={data} onDone={reload} canUnmark={hasPerm('leave.delete')} />
      {!data.deletion_mark && <Space wrap style={{ marginBottom: 12 }}>
        {canEdit && <Button icon={<UsergroupAddOutlined />} onClick={() => run(async () => {
          const r = await post('fill')
          message.info(t('lv.sch.filled', { count: (r.data as unknown as { added: number }).added }))
        })}>{t('lv.sch.fill')}</Button>}
        {data.status === 'draft' && hasPerm('leave.edit') && <Popconfirm title={t('lv.sch.submitConfirm')} onConfirm={() => run(() => post('submit'))}>
          <Button icon={<SendOutlined />}>{t('lv.sch.submit')}</Button></Popconfirm>}
        {data.status !== 'approved' && hasPerm('leave.approve') && <Button icon={<CheckOutlined />} onClick={approve}>{t('lv.sch.approve')}</Button>}
        {data.status !== 'draft' && hasPerm('leave.approve') && <Popconfirm title={t('lv.sch.reopenConfirm')} onConfirm={() => run(() => post('reopen'))}>
          <Button icon={<RollbackOutlined />}>{t('lv.sch.reopen')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('lv.print')}</Button>
        {data.status !== 'approved' && hasPerm('leave.delete') && <MarkButton endpoint="/leave/schedules/" row={data} onDone={reload} text />}
      </Space>}
      {data.approved_by && <Typography.Paragraph type="secondary">{t('lv.sch.approvedBy')}: {data.approved_by}</Typography.Paragraph>}
      {data.warnings.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('lv.sch.warnings')}
        description={<ul style={{ margin: 0, paddingLeft: 18 }}>{data.warnings.map((w, i) => <li key={i}>{warningText(w)}</li>)}</ul>} />}
      {hasPerm('orders.create') && <Space wrap style={{ marginBottom: 12 }}>
        <Typography.Text>{t('lv.sch.ordersFor')}</Typography.Text>
        <Select style={{ width: 150 }} value={month} onChange={setMonth}
          options={MONTHS.map((m) => ({ value: m + 1, label: dayjs().month(m).format('MMMM') }))} />
        <Button icon={<FileAddOutlined />} onClick={makeOrders}>{t('lv.sch.makeOrders')}</Button>
      </Space>}
      <Table<ScheduleRow> rowKey="id" size="small" loading={loading} dataSource={data.rows} pagination={false}
        exportName={t('lv.sch.heading', { year: data.year, subdivision: data.subdivision_name })}
        columns={[
          { title: t('staff.fullName'), dataIndex: 'name', width: 210, render: (v: string, r) => (
            <Space orientation="vertical" size={0}>
              <a onClick={() => navigate(`/employees/${r.employee}?tab=leave`)}>{v}</a>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>{r.occupation}</Typography.Text>
              {r.other_jobs.map((j) => <Typography.Text key={j} type="secondary" style={{ fontSize: 11 }}>+ {j}</Typography.Text>)}
            </Space>) },
          { title: <Tooltip title={t('lv.availableHint')}>{t('lv.available')}</Tooltip>, dataIndex: 'available', width: 80, align: 'right',
            render: (v: number) => <Typography.Text type={v < 0 ? 'danger' : undefined}>{fmtDays(v)}</Typography.Text> },
          { title: t('ord.p.days'), dataIndex: 'days', width: 90, render: (v: number, r) => canEdit
            ? <InputNumber key={`${r.id}-${v}`} size="small" min={0} max={120} defaultValue={v} style={{ width: 70 }}
                onBlur={(e) => { const n = Number(e.target.value); if (n !== v) patch(r, { days: n }) }} /> : v },
          { title: t('lv.sch.planned'), dataIndex: 'date_from', width: 150, render: (v: string | null, r) => canEdit
            ? <DatePicker size="small" format="DD.MM.YYYY" value={v ? dayjs(v) : null} style={{ width: 130 }}
                disabledDate={(x) => x.year() !== data.year}
                onChange={(x) => patch(r, { date_from: x ? x.format('YYYY-MM-DD') : null })} /> : d(v) },
          { title: t('staff.sen.to'), dataIndex: 'date_to', width: 100, render: d },
          { title: t('lv.sch.timeline'), key: 'bar', render: (_: unknown, r) => <YearBar year={data.year} row={r} /> },
          { title: t('lv.sch.state'), dataIndex: 'state', width: 190, render: (v: string, r) => (
            <Space orientation="vertical" size={0}>
              <Tag color={PLAN_STATE_COLOR[v]}>{t(`lv.sch.states.${v}`)}</Tag>
              {r.moved_to && <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('lv.sch.movedTo', { date: d(r.moved_to) })}</Typography.Text>}
              {r.actual.map((a) => <Typography.Text key={a.id} type="secondary" style={{ fontSize: 12 }}>{d(a.from)} – {d(a.to)} ({a.days})</Typography.Text>)}
            </Space>) },
          { title: t('lv.sch.note'), dataIndex: 'note', width: 180, render: (v: string, r) => canEdit
            ? <Input key={`${r.id}-${v}`} size="small" defaultValue={v} onBlur={(e) => { if (e.target.value !== v) patch(r, { note: e.target.value }) }} /> : v },
          ...(canEdit ? [{ title: '', key: 'del', width: 40, render: (_: unknown, r: ScheduleRow) => (
            <Popconfirm title={t('common.confirmDelete')} onConfirm={() => run(() => api.delete(`/leave/schedule-lines/${r.id}/`))}>
              <Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>) }] : []),
        ]} />
      {canEdit && <Space style={{ marginTop: 12 }} wrap>
        <EmployeeSelect style={{ width: 400 }} value={adding} onChange={(v) => setAdding(typeof v === 'number' ? v : undefined)}
          placeholder={t('lv.sch.addPerson')} />
        <Button disabled={!adding} onClick={addLine}>{t('common.add')}</Button>
      </Space>}
      {data.guests.length > 0 && <div style={{ marginTop: 16 }}>
        <Typography.Text strong>{t('lv.sch.guests')}</Typography.Text>
        <Table<ScheduleGuest> rowKey="id" size="small" pagination={false} dataSource={data.guests} style={{ marginTop: 6 }} noSettings
          columns={[
            { title: t('staff.fullName'), dataIndex: 'name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}?tab=leave`)}>{v}</a> },
            { title: t('org.sl.position'), key: 'occ', render: (_: unknown, r) => `${r.occupation} · ${r.kind} (${fmtRate(r.rate)})` },
            { title: t('lv.sch.home'), dataIndex: 'home', width: 220 },
            { title: t('lv.period'), key: 'p', width: 200, render: (_: unknown, r) => r.date_from ? `${d(r.moved_to || r.date_from)} – ${d(r.date_to)}` : '—' },
            { title: t('ord.p.days'), dataIndex: 'days', width: 60, align: 'right' },
          ]} />
      </div>}
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>{t('lv.sch.legend')}</Typography.Paragraph>
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="leave_schedule" url={`/leave/schedules/${id}/print/`}
        params={{}} optionKeys={['show_signature']} title={t('menu.leaveSchedule')} />
    </Card>
  )
}

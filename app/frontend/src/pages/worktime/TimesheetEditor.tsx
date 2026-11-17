import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Form, InputNumber, Modal, Popconfirm, Select, Space, Spin, Tag, Tooltip, Typography, message } from 'antd'
import { ArrowLeftOutlined, LockOutlined, PrinterOutlined, ReloadOutlined, RollbackOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import PrintDialog from '../../components/PrintDialog'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { MONTH_STATUS_COLOR, fmtH, type DayHeader, type TimesheetCell, type TimesheetReport, type TimesheetRow } from '../../api/worktime'
import { useApp } from '../../auth/AppContext'
import { cellStyle, dayTitle, useDocActions } from './MonthDocs'
import { useShifts } from './WorktimePage'

/** Celula pontajului: orele lucrate (cu noaptea dedesubt) sau codul absenței; cele scrise de mână — subliniate. */
function Cell({ cell, onClick }: { cell?: TimesheetCell; onClick?: () => void }) {
  const style: React.CSSProperties = { cursor: onClick ? 'pointer' : undefined, lineHeight: 1.1, minHeight: 28,
    textDecoration: cell?.m ? 'underline dotted' : undefined }
  if (!cell || !cell.c) return <div style={{ ...style, color: 'var(--ant-color-text-quaternary)' }} onClick={onClick}>·</div>
  if (cell.h) {
    return <div style={style} onClick={onClick}><div>{fmtH(cell.h)}</div>
      {cell.n ? <div style={{ fontSize: 10, color: 'var(--ant-color-text-tertiary)' }}>{fmtH(cell.n)}</div> : null}</div>
  }
  return <div style={{ ...style, fontWeight: 600, color: cell.c === 'A' ? 'var(--ant-color-error)' : 'var(--ant-color-primary)' }} onClick={onClick}>{cell.c}</div>
}

/** Tabela de pontaj a secției: completată din grafic și absențe, corectată de mână, închisă pentru salarizare. */
export default function TimesheetEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const { data, loading, reload } = useFetch<TimesheetReport>(`/worktime/timesheets/${id}/report/`)
  const shifts = useShifts()
  const { post } = useDocActions('/worktime/timesheets/', id, reload)
  const [printOpen, setPrintOpen] = useState(false)
  const [editing, setEditing] = useState<{ row: TimesheetRow; day: DayHeader } | null>(null)
  const [form] = Form.useForm()

  if (!data) return <Card loading={loading}><Spin /></Card>
  const editable = hasPerm('worktime.edit') && !data.deletion_mark
    && (data.status === 'draft' || (data.status === 'submitted' && hasPerm('worktime.approve')))
  const codeOptions = [
    { value: '', label: t('wt.ts.cellEmpty') },
    ...shifts.map((s) => ({ value: s.code, label: `${s.code} — ${s.name}` })),
    ...data.manual_codes.filter((c, i, arr) => arr.indexOf(c) === i).map((c) => ({ value: c, label: `${c} — ${data.codes[c] ?? t(`wt.codes.${c}`)}` })),
  ]

  const openCell = (row: TimesheetRow, day: DayHeader) => {
    if (!editable) return
    const cell = row.days[String(day.day)]
    form.setFieldsValue({ code: cell?.c && !cell.h ? cell.c : cell?.h && shifts.some((s) => s.code === cell.c) ? cell.c : '',
      hours: cell?.h ?? undefined, night: cell?.n ?? undefined })
    setEditing({ row, day })
  }
  const saveCell = async () => {
    if (!editing) return
    const v = await form.validateFields()
    try {
      await api.post(`/worktime/timesheets/${id}/set-cell/`, { line: editing.row.id, day: editing.day.day, code: v.code, hours: v.hours, night: v.night })
      setEditing(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const title = t('wt.ts.heading', { month: dayjs().month(data.month - 1).format('MMMM'), year: data.year, subdivision: data.subdivision_name })
  const codeOf = (c: string) => data.codes[c] ?? c

  return (
    <Card title={<Space>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/timesheets')} />
      {title}<Tag color={MONTH_STATUS_COLOR[data.status]}>{data.status_label}</Tag>
    </Space>}>
      <MarkedBanner endpoint="/worktime/timesheets/" row={data} onDone={reload} canUnmark={hasPerm('worktime.delete')} />
      {!data.deletion_mark && <Space wrap style={{ marginBottom: 12 }}>
        {editable && <Button icon={<ReloadOutlined />} onClick={() => post('fill')}>{t('wt.ts.refill')}</Button>}
        {editable && <Popconfirm title={t('wt.ts.resetConfirm')} onConfirm={() => post('fill', { reset: true })}><Button>{t('wt.ts.reset')}</Button></Popconfirm>}
        {data.status === 'draft' && hasPerm('worktime.edit') && <Popconfirm title={t('wt.doc.submitConfirm')} onConfirm={() => post('submit')}>
          <Button icon={<SendOutlined />}>{t('wt.doc.submit')}</Button></Popconfirm>}
        {data.status !== 'closed' && hasPerm('worktime.approve') && <Popconfirm title={t('wt.ts.closeConfirm')} onConfirm={() => post('close')}>
          <Button icon={<LockOutlined />} type="primary">{t('wt.ts.close')}</Button></Popconfirm>}
        {data.status !== 'draft' && hasPerm('worktime.approve') && <Popconfirm title={t('wt.doc.reopenConfirm')} onConfirm={() => post('reopen')}>
          <Button icon={<RollbackOutlined />}>{t('wt.doc.reopen')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('lv.print')}</Button>
        {data.status !== 'closed' && hasPerm('worktime.delete') && <MarkButton endpoint="/worktime/timesheets/" row={data} onDone={reload} text />}
      </Space>}
      <Table<TimesheetRow> rowKey="id" size="small" loading={loading} dataSource={data.rows} pagination={false} noSettings
        scroll={{ x: 1600 }} exportName={title}
        columns={[
          { title: t('staff.fullName'), dataIndex: 'name', width: 200, fixed: 'left', render: (v: string, r) => (
            <Space orientation="vertical" size={0}>
              <a onClick={() => navigate(`/employees/${r.employee}?tab=jobs`)}>{v}</a>
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>{r.occupation}{r.kind !== 'main' ? ` · ${r.kind_label}` : ''} · {r.rate * 100}%</Typography.Text>
            </Space>) },
          ...data.days.map((d) => ({
            title: dayTitle(d, t), key: `d${d.day}`, width: 40, onCell: () => ({ style: cellStyle(d) }),
            render: (_: unknown, r: TimesheetRow) => {
              const cell = r.days[String(d.day)]
              const node = <Cell cell={cell} onClick={editable ? () => openCell(r, d) : undefined} />
              return cell?.c && !cell.h ? <Tooltip title={codeOf(cell.c)}>{node}</Tooltip> : node
            },
          })),
          { title: t('wt.ts.days'), key: 'td', width: 50, align: 'right', fixed: 'right', render: (_: unknown, r) => r.totals.days || '' },
          { title: t('wt.ro.hours'), key: 'th', width: 60, align: 'right', fixed: 'right', render: (_: unknown, r) => <b>{fmtH(r.totals.hours)}</b> },
          { title: t('wt.ro.night'), key: 'tn', width: 64, align: 'right', fixed: 'right', render: (_: unknown, r) => fmtH(r.totals.night) },
          { title: t('wt.ts.holiday'), key: 'thol', width: 55, align: 'right', fixed: 'right', render: (_: unknown, r) => fmtH(r.totals.holiday) },
          { title: t('wt.ro.norm'), key: 'tnorm', width: 60, align: 'right', fixed: 'right', render: (_: unknown, r) => fmtH(r.totals.norm) },
          { title: '±', key: 'diff', width: 60, align: 'right', fixed: 'right', render: (_: unknown, r) => r.totals.overtime
            ? <Typography.Text type="warning">+{fmtH(r.totals.overtime)}</Typography.Text>
            : r.totals.missing ? <Typography.Text type="secondary">−{fmtH(r.totals.missing)}</Typography.Text> : '' },
          { title: t('wt.ts.absences'), key: 'codes', width: 120, fixed: 'right', render: (_: unknown, r) =>
            Object.entries(r.totals.codes ?? {}).map(([c, n]) => <Tooltip key={c} title={codeOf(c)}><Tag style={{ marginRight: 2 }}>{c} {n}</Tag></Tooltip>) },
        ]} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>{t('wt.ts.legend')}</Typography.Paragraph>
      <Typography.Paragraph type="secondary">
        {Object.entries(data.codes).map(([c, l]) => <span key={c} style={{ marginRight: 12 }}><b>{c}</b> — {l}</span>)}
      </Typography.Paragraph>
      <Modal open={!!editing} onOk={saveCell} onCancel={() => setEditing(null)} width={460}
        title={editing ? t('wt.ts.cellTitle', { name: editing.row.name, day: `${editing.day.day}.${String(data.month).padStart(2, '0')}` }) : ''}>
        <Form form={form} layout="vertical">
          <Form.Item name="code" label={t('wt.ts.cellCode')}><Select options={codeOptions} showSearch optionFilterProp="label" /></Form.Item>
          <Space>
            <Form.Item name="hours" label={t('wt.ts.cellHours')}><InputNumber min={0} max={24} step={0.5} /></Form.Item>
            <Form.Item name="night" label={t('wt.ts.cellNight')}><InputNumber min={0} max={24} step={0.5} /></Form.Item>
          </Space>
          <Typography.Text type="secondary">{t('wt.ts.cellHint')}</Typography.Text>
        </Form>
      </Modal>
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="timesheet" url={`/worktime/timesheets/${id}/print/`}
        params={{}} optionKeys={[]} title={t('menu.timesheets')} />
    </Card>
  )
}

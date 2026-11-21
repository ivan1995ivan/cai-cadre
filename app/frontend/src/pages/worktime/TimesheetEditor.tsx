import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Descriptions, Form, InputNumber, Modal, Popconfirm, Radio, Select, Space, Spin, Tag, Tooltip, Typography, message } from 'antd'
import { ArrowLeftOutlined, LockOutlined, PrinterOutlined, ReloadOutlined, RollbackOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import PrintDialog from '../../components/PrintDialog'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { MONTH_STATUS_COLOR, fmtH, type DayHeader, type HourColumn, type TimesheetCell, type TimesheetReport, type TimesheetRow } from '../../api/worktime'
import { useApp, useLocalName } from '../../auth/AppContext'
import ExcelImport from '../../components/ExcelImport'
import { combinationShort, payShort } from './HourRates'
import { cellStyle, dayTitle, useDocActions } from './MonthDocs'
import { useShifts } from './WorktimePage'
import { useTabTitle } from '../../layout/tabs'

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
  useTabTitle(data ? { key: 'wt.ts.heading', params: { month: { month: data.month }, year: data.year, subdivision: data.subdivision_name } } : null)
  const shifts = useShifts()
  const { post } = useDocActions('/worktime/timesheets/', id, reload)
  const [printOpen, setPrintOpen] = useState(false)
  const [editing, setEditing] = useState<{ row: TimesheetRow; day: DayHeader } | null>(null)
  const [form] = Form.useForm()
  const [typedEdit, setTypedEdit] = useState<{ row: TimesheetRow; col: HourColumn } | null>(null)
  const [typedForm] = Form.useForm()
  const typedMode = Form.useWatch('mode', typedForm) as 'day' | 'month' | undefined
  const localName = useLocalName()

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
  const openTyped = (row: TimesheetRow, col: HourColumn) => {
    if (!editable) return
    const entry = row.typed[col.code]
    const byDay = col.entry === 'day' && !(entry && entry.month !== null && entry.month !== undefined)
    typedForm.resetFields()
    typedForm.setFieldsValue({ mode: byDay ? 'day' : 'month', month: entry?.month ?? (entry ? Object.values(entry.days).reduce((a, b) => a + b, 0) : undefined),
      ...Object.fromEntries(Object.entries(entry?.days ?? {}).map(([k, v]) => [`d${k}`, v])) })
    setTypedEdit({ row, col })
  }
  const saveTyped = async (clear = false) => {
    if (!typedEdit) return
    const v = await typedForm.validateFields()
    const days = Object.fromEntries(data.days.map((d) => [String(d.day), v[`d${d.day}`]]).filter(([, h]) => h !== null && h !== undefined && h !== 0))
    const body = clear ? { days: null, month: null } : v.mode === 'month' ? { month: v.month ?? null } : { days }
    try {
      await api.post(`/worktime/timesheets/${id}/set-hours/`, { line: typedEdit.row.id, code: typedEdit.col.code, ...body })
      setTypedEdit(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const typedCell = (r: TimesheetRow, col: HourColumn) => {
    const s = r.hour_types[col.code]
    const node = !s ? <span style={{ color: 'var(--ant-color-text-quaternary)' }}>·</span> : <div style={{ lineHeight: 1.1 }}>
      <div><b>{fmtH(s.hours) || '0'}</b></div>
      {s.guaranteed !== null && <div style={{ fontSize: 10, color: 'var(--ant-color-text-tertiary)' }}>
        {t('ht.ts.cellLine', { g: fmtH(s.guaranteed) || '0', p: fmtH(s.paid) || '0' })}</div>}
    </div>
    const tip = s ? <div>
      <div>{t('ht.ts.summary', { hours: fmtH(s.hours) || '0', guaranteed: s.guaranteed === null ? '—' : fmtH(s.guaranteed) || '0',
        available: s.available_days ?? '—', total: s.total_days, paid: fmtH(s.paid) || '0' })}</div>
      {s.note && <div style={{ marginTop: 4 }}>{s.note}</div>}
    </div> : localName(col)
    return <Tooltip title={tip}><div style={{ cursor: editable ? 'pointer' : undefined, minHeight: 28 }}
      onClick={editable ? () => openTyped(r, col) : undefined}>{node}</div></Tooltip>
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
        {editable && <ExcelImport code="hours" url={`/worktime/timesheets/${id}/import/`} label={t('ht.ts.import')} onDone={reload}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>{t('ht.ts.importHint')}</Typography.Paragraph>
        </ExcelImport>}
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
              {r.kind !== 'contractor' && <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                {payShort(t, r.pay_mode)}{r.rate_codes.length ? `: ${r.rate_codes.join(', ')}` : ''}
                {r.combinations.map((c) => `; ${combinationShort(t, c)}`).join('')}</Typography.Text>}
              {r.hour_warnings.map((w) => <Typography.Text key={w} type="warning" style={{ fontSize: 11 }}>{w}</Typography.Text>)}
            </Space>) },
          ...data.days.map((d) => ({
            title: dayTitle(d, t), key: `d${d.day}`, width: 40, onCell: () => ({ style: cellStyle(d) }),
            render: (_: unknown, r: TimesheetRow) => {
              const cell = r.days[String(d.day)]
              const node = <Cell cell={cell} onClick={editable ? () => openCell(r, d) : undefined} />
              return cell?.c && !cell.h ? <Tooltip title={codeOf(cell.c)}>{node}</Tooltip> : node
            },
          })),
          ...data.hour_types.map((col) => ({
            title: <Tooltip title={localName(col)}>{col.code}</Tooltip>, key: `ht-${col.code}`, width: 64, align: 'right' as const,
            onCell: () => ({ style: { background: 'var(--ant-color-fill-quaternary)' } }),
            render: (_: unknown, r: TimesheetRow) => typedCell(r, col),
          })),
          { title: t('wt.ts.days'), key: 'td', width: 50, align: 'right', fixed: 'right', render: (_: unknown, r) => r.totals.days || '' },
          { title: t('wt.ro.hours'), key: 'th', width: 60, align: 'right', fixed: 'right', render: (_: unknown, r) => <b>{fmtH(r.totals.hours)}</b> },
          { title: t('wt.ro.night'), key: 'tn', width: 64, align: 'right', fixed: 'right', render: (_: unknown, r) => fmtH(r.totals.night) },
          { title: t('wt.ts.holiday'), key: 'thol', width: 55, align: 'right', fixed: 'right', render: (_: unknown, r) => fmtH(r.totals.holiday) },
          { title: t('wt.ro.norm'), key: 'tnorm', width: 60, align: 'right', fixed: 'right', render: (_: unknown, r) => fmtH(r.totals.norm) },
          { title: '±', key: 'diff', width: 60, align: 'right', fixed: 'right', render: (_: unknown, r) => {
            const tt = r.totals
            const split = t('wt.ts.overtimeSplit', { first: fmtH(tt.overtime_2 ?? tt.overtime), next: fmtH(tt.overtime_over ?? 0),
              inNorm: fmtH(tt.holiday_in_norm ?? 0), over: fmtH(tt.holiday_over_norm ?? 0) })
            const text = tt.overtime ? <Typography.Text type="warning">+{fmtH(tt.overtime)}</Typography.Text>
              : tt.missing ? <Typography.Text type="secondary">−{fmtH(tt.missing)}</Typography.Text> : ''
            return tt.overtime || tt.holiday_in_norm || tt.holiday_over_norm ? <Tooltip title={split}>{text || '·'}</Tooltip> : text
          } },
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
      <Modal open={!!typedEdit} onCancel={() => setTypedEdit(null)} width={720}
        title={typedEdit ? t('ht.ts.editTitle', { code: typedEdit.col.code, name: localName(typedEdit.col), who: typedEdit.row.name }) : ''}
        footer={[
          <Button key="clear" danger onClick={() => saveTyped(true)}>{t('ht.ts.clear')}</Button>,
          <Button key="cancel" onClick={() => setTypedEdit(null)}>{t('common.cancel')}</Button>,
          <Button key="ok" type="primary" onClick={() => saveTyped()}>{t('common.save')}</Button>,
        ]}>
        {typedEdit && (() => {
          const s = typedEdit.row.hour_types[typedEdit.col.code]
          return <>
            {s && s.guaranteed !== null && <Descriptions size="small" column={4} style={{ marginBottom: 8 }} items={[
              { key: 'g', label: t('ht.ts.guaranteed'), children: fmtH(s.guaranteed) || '0' },
              { key: 'a', label: t('ht.ts.available'), children: `${s.available_days ?? '—'} / ${s.total_days}` },
              { key: 'e', label: t('ht.ts.effective'), children: fmtH(s.hours) || '0' },
              { key: 'p', label: t('ht.ts.paid'), children: <b>{fmtH(s.paid) || '0'}</b> },
            ]} />}
            {s?.note && <Alert type="info" showIcon style={{ marginBottom: 8 }} title={s.note} />}
            <Form form={typedForm} layout="vertical">
              <Form.Item name="mode" label={t('ht.ts.entry')}>
                <Radio.Group options={[{ value: 'day', label: t('ht.ts.byDay'), disabled: typedEdit.col.entry === 'month' },
                  { value: 'month', label: t('ht.ts.byMonth') }]} />
              </Form.Item>
              {typedMode === 'month' ? <Form.Item name="month" label={t('ht.ts.total')}><InputNumber min={0} max={744} step={0.5} /></Form.Item>
                : <Space wrap size={[4, 4]}>
                  {data.days.map((d) => (
                    <Form.Item key={d.day} name={`d${d.day}`} label={dayTitle(d, t)} style={{ marginBottom: 4, width: 64 }}>
                      <InputNumber min={0} max={24} step={0.5} size="small" style={{ width: 60 }} />
                    </Form.Item>
                  ))}
                </Space>}
            </Form>
            <Typography.Text type="secondary">{t('ht.ts.editHint')}</Typography.Text>
          </>
        })()}
      </Modal>
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="timesheet" url={`/worktime/timesheets/${id}/print/`}
        params={{}} optionKeys={[]} title={t('menu.timesheets')} />
    </Card>
  )
}

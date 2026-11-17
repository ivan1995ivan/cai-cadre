import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Popconfirm, Select, Space, Spin, Tag, Tooltip, Typography } from 'antd'
import { ArrowLeftOutlined, CheckOutlined, PrinterOutlined, ReloadOutlined, RollbackOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import PrintDialog from '../../components/PrintDialog'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import { api } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { MONTH_STATUS_COLOR, fmtH, type RosterReport, type RosterRow, type RosterWarning } from '../../api/worktime'
import { useApp } from '../../auth/AppContext'
import { cellStyle, dayTitle, useDocActions } from './MonthDocs'
import { shiftOptions, useShifts } from './WorktimePage'

/** Graficul lunar al secției: turele și gărzile fiecărui raport de muncă pe zilele lunii. */
export default function RosterEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const { data, loading, reload } = useFetch<RosterReport>(`/worktime/rosters/${id}/report/`)
  const shifts = useShifts()
  const { run, post } = useDocActions('/worktime/rosters/', id, reload)
  const [printOpen, setPrintOpen] = useState(false)
  const colors = Object.fromEntries(shifts.map((s) => [s.code, s.color]))

  if (!data) return <Card loading={loading}><Spin /></Card>
  const editable = hasPerm('worktime.edit') && !data.deletion_mark
    && (data.status === 'draft' || (data.status === 'submitted' && hasPerm('worktime.approve')))
  const options = shiftOptions(shifts, t)

  const setDay = (row: RosterRow, day: number, code: string) => {
    const days = { ...row.days }
    if (code === '-' || !code) delete days[String(day)]
    else days[String(day)] = code
    run(() => api.patch(`/worktime/roster-lines/${row.id}/`, { days }))
  }
  const warnText = (w: RosterWarning) => {
    if (w.kind === 'rest') return t('wt.ro.warnRest', { name: w.name, day: w.day, rest: w.rest })
    if (w.kind === 'absence') return t('wt.ro.warnAbsence', { name: w.name, day: w.day, code: w.code })
    if (w.kind === 'duties') return t('wt.ro.warnDuties', { name: w.name, duties: w.duties, max: w.max })
    return t('wt.ro.warnNorm', { name: w.name, hours: fmtH(w.hours), norm: fmtH(w.norm) })
  }
  const title = t('wt.ro.heading', { month: dayjs().month(data.month - 1).format('MMMM'), year: data.year, subdivision: data.subdivision_name })

  return (
    <Card title={<Space>
      <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/worktime/rosters')} />
      {title}<Tag color={MONTH_STATUS_COLOR[data.status]}>{data.status_label}</Tag>
    </Space>}>
      <MarkedBanner endpoint="/worktime/rosters/" row={data} onDone={reload} canUnmark={hasPerm('worktime.delete')} />
      {!data.deletion_mark && <Space wrap style={{ marginBottom: 12 }}>
        {editable && <Popconfirm title={t('wt.ro.fillConfirm')} onConfirm={() => post('fill', { overwrite: true })}>
          <Button icon={<ReloadOutlined />}>{t('wt.ro.fill')}</Button></Popconfirm>}
        {editable && <Button onClick={() => post('fill')}>{t('wt.doc.addMissing')}</Button>}
        {data.status === 'draft' && hasPerm('worktime.edit') && <Popconfirm title={t('wt.doc.submitConfirm')} onConfirm={() => post('submit')}>
          <Button icon={<SendOutlined />}>{t('wt.doc.submit')}</Button></Popconfirm>}
        {data.status !== 'approved' && hasPerm('worktime.approve') && <Button icon={<CheckOutlined />} onClick={() => post('approve')}>{t('wt.doc.approve')}</Button>}
        {data.status !== 'draft' && hasPerm('worktime.approve') && <Popconfirm title={t('wt.doc.reopenConfirm')} onConfirm={() => post('reopen')}>
          <Button icon={<RollbackOutlined />}>{t('wt.doc.reopen')}</Button></Popconfirm>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('lv.print')}</Button>
        {data.status !== 'approved' && hasPerm('worktime.delete') && <MarkButton endpoint="/worktime/rosters/" row={data} onDone={reload} text />}
      </Space>}
      {data.warnings.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('lv.sch.warnings')}
        description={<ul style={{ margin: 0, paddingLeft: 18 }}>{data.warnings.map((w, i) => <li key={i}>{warnText(w)}</li>)}</ul>} />}
      <Table<RosterRow> rowKey="id" size="small" loading={loading} dataSource={data.rows} pagination={false} noSettings
        scroll={{ x: 1400 }} exportName={title}
        columns={[
          { title: t('staff.fullName'), dataIndex: 'name', width: 200, fixed: 'left', render: (v: string, r) => (
            <Space orientation="vertical" size={0}>
              <a onClick={() => navigate(`/employees/${r.employee}?tab=jobs`)}>{v}</a>
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>{r.occupation}{r.kind !== 'main' ? ` · ${r.kind_label}` : ''} · {r.rate * 100}%</Typography.Text>
            </Space>) },
          ...data.days.map((d) => ({
            title: dayTitle(d, t), key: `d${d.day}`, width: 54, onCell: () => ({ style: cellStyle(d) }),
            render: (_: unknown, r: RosterRow) => {
              const code = r.days[String(d.day)] ?? ''
              const absence = r.absences[String(d.day)]
              if (absence && !code) return <Tooltip title={t(`wt.codes.${absence}`, { defaultValue: absence })}><Typography.Text type="secondary">{absence}</Typography.Text></Tooltip>
              if (!editable) return <span style={{ color: colors[code] || undefined, fontWeight: 600 }}>{code}</span>
              return <Select size="small" variant="borderless" value={code || '-'} options={options} popupMatchSelectWidth={false}
                suffixIcon={null} style={{ width: 52, color: colors[code] || undefined, fontWeight: 600 }} onChange={(v) => setDay(r, d.day, v)}
                labelRender={(o) => (o.value === '-' ? <span style={{ color: 'var(--ant-color-text-quaternary)' }}>·</span> : String(o.value))} />
            },
          })),
          { title: t('wt.ro.hours'), dataIndex: 'hours', width: 60, align: 'right', fixed: 'right', render: (v: number, r) =>
            <Typography.Text type={v > r.norm && r.norm ? 'danger' : undefined} strong>{fmtH(v)}</Typography.Text> },
          { title: t('wt.ro.norm'), dataIndex: 'norm', width: 60, align: 'right', fixed: 'right', render: fmtH },
          { title: t('wt.ro.night'), dataIndex: 'night', width: 60, align: 'right', fixed: 'right', render: fmtH },
          { title: t('wt.ro.duties'), dataIndex: 'duties', width: 55, align: 'right', fixed: 'right', render: (v: number) => v || '' },
        ]} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        {shifts.map((s) => <span key={s.code} style={{ marginRight: 12 }}><b style={{ color: s.color || undefined }}>{s.code}</b> — {s.name}</span>)}
      </Typography.Paragraph>
      <Typography.Paragraph type="secondary">{t('wt.ro.legend')}</Typography.Paragraph>
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="roster" url={`/worktime/rosters/${id}/print/`}
        params={{}} optionKeys={[]} title={t('wt.rosters')} />
    </Card>
  )
}

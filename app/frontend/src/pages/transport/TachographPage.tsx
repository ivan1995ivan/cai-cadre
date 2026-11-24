import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, DatePicker, Modal, Popconfirm, Select, Space, Tabs, Tag, Tooltip, Typography, message } from 'antd'
import { DeleteOutlined, DownloadOutlined, UploadOutlined, UserAddOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import EmployeeSelect from '../../components/EmployeeSelect'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { downloadFile } from '../../api/payroll'
import { useApp } from '../../auth/AppContext'
import { ACTIVITY_COLOR, hm, type TachoDayRow, type TachoFile, type TachoFinding, type TachoUpload } from '../../api/transport'

const DT = 'DD.MM.YYYY HH:mm'

/** Bara zilei: activitățile pe 24 de ore (ora Moldovei), cu culorile legendei. */
export function DayBar({ spans }: { spans: [number, number, string, number][] }) {
  const { t } = useTranslation()
  return (
    <div style={{ position: 'relative', height: 14, minWidth: 220, background: 'var(--ant-color-fill-quaternary)', borderRadius: 2 }}>
      {spans.map(([a, b, code], i) => (
        <Tooltip key={i} title={`${dayjs().startOf('day').add(a, 'minute').format('HH:mm')}–${b >= 1440 ? '24:00' : dayjs().startOf('day').add(b, 'minute').format('HH:mm')} ${t(`tr.tacho.act.${code}`)}`}>
          <div style={{ position: 'absolute', top: code === 'D' ? 0 : 3, bottom: code === 'D' ? 0 : 3, left: `${(a / 1440) * 100}%`,
            width: `${((b - a) / 1440) * 100}%`, background: ACTIVITY_COLOR[code] }} />
        </Tooltip>
      ))}
    </div>
  )
}

export function Legend() {
  const { t } = useTranslation()
  return (
    <Space wrap size={12}>
      {['D', 'W', 'A', 'R', 'U'].map((c) => (
        <Space key={c} size={4}><span style={{ display: 'inline-block', width: 14, height: 10, background: ACTIVITY_COLOR[c] }} />
          <Typography.Text type="secondary">{t(`tr.tacho.act.${c}`)}</Typography.Text></Space>))}
    </Space>
  )
}

function monthParam(v: string | null): Dayjs {
  const d = v ? dayjs(`${v}-01`) : dayjs()
  return (d.isValid() ? d : dayjs()).startOf('month')
}

/** Tahograful: descărcările cardului de conducător (.ddd), zilele șoferului cu activitățile, încălcările lunii. */
export default function TachographPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'files'
  const set = (patch: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params)
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    setParams(next)
  }
  return (
    <Card title={t('menu.tachograph')}>
      <Tabs activeKey={tab} onChange={(k) => set({ tab: k })} destroyOnHidden items={[
        { key: 'files', label: t('tr.tacho.files'), children: <Files onOpen={(emp) => set({ tab: 'days', employee: String(emp) })} /> },
        { key: 'days', label: t('tr.tacho.days'), children: <Days employee={params.get('employee')} month={monthParam(params.get('month'))}
          onChange={(emp, m) => set({ employee: emp ? String(emp) : undefined, month: m.format('YYYY-MM') })} /> },
        { key: 'findings', label: t('tr.tacho.findings'), children: <Findings month={monthParam(params.get('month'))}
          onMonth={(m) => set({ month: m.format('YYYY-MM') })} onOpen={(emp, m) => set({ tab: 'days', employee: String(emp), month: m })} /> },
      ]} />
    </Card>
  )
}

function Files({ onOpen }: { onOpen: (employee: number) => void }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState<TachoUpload[] | null>(null)
  const [assign, setAssign] = useState<TachoFile | null>(null)
  const [who, setWho] = useState<number | null>(null)
  const [unmatched, setUnmatched] = useState(false)
  const { data, loading, reload } = useFetch<Paged<TachoFile> | TachoFile[]>('/transport/tacho-files/',
    { page_size: 500, unmatched: unmatched ? 1 : undefined })
  const rows = Array.isArray(data) ? data : data?.results ?? []

  const send = async (files: FileList | null) => {
    if (!files || !files.length) return
    const form = new FormData()
    Array.from(files).forEach((f) => form.append('files', f))
    setBusy(true)
    try {
      const r = await api.post<{ results: TachoUpload[] }>('/transport/tacho-files/upload/', form)
      setResults(r.data.results)
      reload()
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }
  const doAssign = async () => {
    if (!assign) return
    try {
      await api.post(`/transport/tacho-files/${assign.id}/assign/`, { employee: who })
      setAssign(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const remove = async (f: TachoFile) => {
    try {
      await api.post(`/transport/tacho-files/${f.id}/remove/`)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const tone: Record<string, 'success' | 'info' | 'error'> = { created: 'success', duplicate: 'info', error: 'error' }
  return (
    <>
      <Space style={{ marginBottom: 12 }} wrap>
        {hasPerm('transport.create') && <>
          <input ref={input} type="file" multiple accept=".ddd,.DDD,.esm,.ESM,.c1b,.C1B,.tgd,.TGD" style={{ display: 'none' }}
            onChange={(e) => send(e.target.files)} />
          <Button type="primary" icon={<UploadOutlined />} loading={busy} onClick={() => input.current?.click()}>{t('tr.tacho.upload')}</Button>
        </>}
        <Select style={{ width: 220 }} value={unmatched ? 1 : 0} onChange={(v) => setUnmatched(v === 1)}
          options={[{ value: 0, label: t('tr.tacho.allFiles') }, { value: 1, label: t('tr.tacho.unmatched') }]} />
        <Typography.Text type="secondary">{t('tr.tacho.uploadHint')}</Typography.Text>
      </Space>
      {results && <Alert closable onClose={() => setResults(null)} style={{ marginBottom: 12 }} type={results.some((r) => r.status === 'error') ? 'warning' : 'success'}
        title={t('tr.tacho.uploaded', { n: results.filter((r) => r.status === 'created').length })}
        description={<ul style={{ margin: 0, paddingInlineStart: 18 }}>{results.map((r, i) => (
          <li key={i}><Tag color={tone[r.status]}>{t(`tr.tacho.status.${r.status}`)}</Tag><b>{r.name}</b>
            {r.employee_name ? ` — ${r.employee_name}` : ''}: {r.message}</li>))}</ul>} />}
      <Table<TachoFile> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} exportName={t('menu.tachograph')}
        columns={[
          { title: t('tr.tacho.downloaded'), dataIndex: 'downloaded_at', width: 140, render: (v: string | null, r) => dayjs(v ?? r.uploaded_at).format(DT) },
          { title: t('tr.tacho.holder'), dataIndex: 'holder', width: 200 },
          { title: t('tr.tacho.card'), dataIndex: 'card_number', width: 170, render: (v: string, r) => <Space size={4}>{v}<Tag>G{r.generation}{r.generation === 2 ? `v${r.version}` : ''}</Tag></Space> },
          { title: t('tr.tacho.expiry'), dataIndex: 'card_expiry', width: 100, render: (v: string | null) => (v ? dayjs(v).format('DD.MM.YYYY') : '') },
          { title: t('tr.tacho.period'), key: 'p', width: 190, render: (_: unknown, r) => (r.first_day ? `${dayjs(r.first_day).format('DD.MM.YYYY')} – ${dayjs(r.last_day).format('DD.MM.YYYY')}` : '—') },
          { title: t('tr.tacho.daysCount'), dataIndex: 'days', width: 70, align: 'right' },
          { title: t('tr.tacho.employee'), dataIndex: 'employee_name', render: (v: string, r) => (r.employee
            ? <Space size={4}><a onClick={() => onOpen(r.employee as number)}>{v}</a>{r.matched_by === 'name' && <Tag>{t('tr.tacho.byName')}</Tag>}</Space>
            : <Tag color="red">{t('tr.tacho.noEmployee')}</Tag>) },
          { title: '', key: 'a', width: 120, render: (_: unknown, r) => (
            <Space size={2}>
              {hasPerm('transport.edit') && <Tooltip title={t('tr.tacho.assign')}><Button size="small" type="text" icon={<UserAddOutlined />}
                onClick={() => { setAssign(r); setWho(r.employee) }} /></Tooltip>}
              <Tooltip title={t('tr.tacho.original')}><Button size="small" type="text" icon={<DownloadOutlined />}
                onClick={() => downloadFile(`/transport/tacho-files/${r.id}/original/`, {}, `C_${r.card_number}.ddd`).catch((e) => message.error(errorText(e)))} /></Tooltip>
              {hasPerm('transport.delete') && <Popconfirm title={t('tr.tacho.removeConfirm')} onConfirm={() => remove(r)}>
                <Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>}
            </Space>) },
        ]} />
      {assign && <Modal open title={`${t('tr.tacho.assign')}: ${assign.holder} (${assign.card_number})`} onCancel={() => setAssign(null)} onOk={doAssign}>
        <Typography.Paragraph type="secondary">{t('tr.tacho.assignHint')}</Typography.Paragraph>
        <EmployeeSelect value={who} onChange={(v) => setWho((v as number) ?? null)} style={{ width: '100%' }} />
      </Modal>}
    </>
  )
}

function FindingList({ items }: { items: TachoFinding[] }) {
  return (
    <ul style={{ margin: 0, paddingInlineStart: 18 }}>
      {items.map((f, i) => <li key={i}><Tag color={f.level === 'error' ? 'red' : 'gold'}>{dayjs(f.start).format(DT)}</Tag>
        <b>{f.title}</b>: {f.text}</li>)}
    </ul>
  )
}

function Days({ employee, month, onChange }: { employee: string | null; month: Dayjs; onChange: (employee: number | null, month: Dayjs) => void }) {
  const { t } = useTranslation()
  const { data: drivers } = useFetch<{ id: number; label: string }[]>('/transport/tacho-files/drivers/')
  const emp = employee ? Number(employee) : null
  const { data, loading } = useFetch<{ days: TachoDayRow[]; totals: Record<string, number>; findings: TachoFinding[] }>(
    emp ? '/transport/tacho/days/' : null, { employee: emp, month: month.format('YYYY-MM') })
  const keys = ['driving', 'work', 'availability', 'rest', 'unknown'] as const
  return (
    <>
      <Space style={{ marginBottom: 12 }} wrap>
        <Select showSearch optionFilterProp="label" style={{ width: 320 }} placeholder={t('tr.tacho.driver')} value={emp ?? undefined}
          onChange={(v) => onChange(v ?? null, month)} options={(drivers ?? []).map((d) => ({ value: d.id, label: d.label }))} />
        <DatePicker picker="month" format="MM.YYYY" value={month} allowClear={false} onChange={(v) => v && onChange(emp, v.startOf('month'))} />
        <Legend />
      </Space>
      <Typography.Paragraph type="secondary">{t('tr.tacho.daysHint')}</Typography.Paragraph>
      {data && data.findings.length > 0 && <Alert type="error" showIcon style={{ marginBottom: 12 }}
        title={t('tr.tacho.foundN', { n: data.findings.filter((f) => f.level === 'error').length })} description={<FindingList items={data.findings} />} />}
      <Table<TachoDayRow> rowKey="day" size="small" loading={loading} dataSource={emp ? data?.days ?? [] : []} pagination={false}
        exportName={t('tr.tacho.days')}
        expandable={{ rowExpandable: (r) => r.findings.length > 0, expandedRowRender: (r) => <FindingList items={r.findings} /> }}
        columns={[
          { title: t('tr.tacho.day'), dataIndex: 'day', width: 125,
            render: (v: string) => <span style={{ whiteSpace: 'nowrap' }}>{dayjs(v).format('DD.MM.YYYY dd')}</span> },
          { title: t('tr.tacho.timeline'), key: 'bar', render: (_: unknown, r) => (r.has_data ? <DayBar spans={r.spans} />
            : <Typography.Text type="secondary">{t('tr.tacho.noData')}</Typography.Text>) },
          ...keys.map((k) => ({ title: t(`tr.tacho.sum.${k}`), dataIndex: k, width: 80, align: 'right' as const,
            render: (v: number) => (v ? hm(v) : '') })),
          { title: t('tr.tacho.km'), dataIndex: 'km', width: 70, align: 'right', render: (v: number) => v || '' },
          { title: t('tr.tacho.countries'), dataIndex: 'countries', width: 100, render: (v: string[]) => v.join(', ') },
          { title: t('tr.tacho.vehicles'), dataIndex: 'vehicles', width: 120, render: (v: string[]) => v.join(', ') },
          { title: '', key: 'f', width: 50, render: (_: unknown, r) => {
            const n = r.findings.filter((f) => f.level === 'error').length
            return n ? <Tag color="red">{n}</Tag> : (r.findings.length ? <Tag color="gold">!</Tag> : '')
          } },
        ]}
        summary={() => (data && emp ? (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={3} align="right"><b>{t('tr.diem.total')}</b></Table.Summary.Cell>
            {keys.map((k, i) => <Table.Summary.Cell key={k} index={3 + i} align="right"><b>{hm(data.totals[k] ?? 0)}</b></Table.Summary.Cell>)}
            <Table.Summary.Cell index={8} align="right"><b>{data.totals.km || ''}</b></Table.Summary.Cell>
            <Table.Summary.Cell index={9} colSpan={3} />
          </Table.Summary.Row>) : null)} />
    </>
  )
}

function Findings({ month, onMonth, onOpen }: { month: Dayjs; onMonth: (m: Dayjs) => void; onOpen: (employee: number, month: string) => void }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data, loading } = useFetch<{ rows: (TachoFinding & { employee: number; name: string })[] }>('/transport/tacho/findings/',
    { month: month.format('YYYY-MM') })
  const rows = data?.rows ?? []
  return (
    <>
      <Space style={{ marginBottom: 12 }} wrap>
        <DatePicker picker="month" format="MM.YYYY" value={month} allowClear={false} onChange={(v) => v && onMonth(v.startOf('month'))} />
        <Typography.Text type="secondary">{t('tr.tacho.findingsHint')}</Typography.Text>
      </Space>
      <Table<TachoFinding & { employee: number; name: string }> rowKey={(r) => `${r.employee}-${r.code}-${r.start}`} size="small" loading={loading}
        dataSource={rows} pagination={false} exportName={t('tr.tacho.findings')}
        columns={[
          { title: t('tr.tacho.driver'), dataIndex: 'name', width: 200, render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}`)}>{v}</a> },
          { title: t('tr.tacho.from'), dataIndex: 'start', width: 140, render: (v: string, r) => <a onClick={() => onOpen(r.employee, dayjs(v).format('YYYY-MM'))}>{dayjs(v).format(DT)}</a> },
          { title: t('tr.tacho.to'), dataIndex: 'end', width: 140, render: (v: string) => dayjs(v).format(DT) },
          { title: t('tr.tacho.rule'), dataIndex: 'title', render: (v: string, r) => <Space size={4}><Tag color={r.level === 'error' ? 'red' : 'gold'}>
            {t(`tr.tacho.level.${r.level}`)}</Tag>{v}</Space> },
          { title: t('tr.tacho.what'), dataIndex: 'text' },
        ]} />
    </>
  )
}

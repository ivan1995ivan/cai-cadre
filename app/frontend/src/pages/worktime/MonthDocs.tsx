import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Form, Modal, Select, Space, Tag, Typography, message } from 'antd'
import { DownloadOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { MONTH_STATUS_COLOR, defaultMonth, type DayHeader, type MonthDoc } from '../../api/worktime'
import { useApp } from '../../auth/AppContext'
import { useSubdivisionOptions } from '../leave/LeavePage'
import SubdivisionSelect from '../../components/SubdivisionSelect'

/** Descarcă exportul lunii (Excel) cu sesiunea curentă. */
async function download(url: string, year: number, month: number) {
  try {
    const r = await api.get(url, { params: { year, month }, responseType: 'blob' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(r.data as Blob)
    a.download = `pontaj-${year}-${String(month).padStart(2, '0')}.xlsx`
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    message.error(errorText(e))
  }
}

export const monthOptions = () => Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: dayjs().month(i).format('MMMM') }))

/** Alegerea lunii și a anului (pentru listele lunare). */
export function MonthPicker({ year, month, onChange }: { year: number; month: number; onChange: (y: number, m: number) => void }) {
  return (
    <Space>
      <Select style={{ width: 130 }} value={month} onChange={(m) => onChange(year, m)} options={monthOptions()} />
      <Select style={{ width: 100 }} value={year} onChange={(y) => onChange(y, month)}
        options={Array.from({ length: 5 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />
    </Space>
  )
}

/** Antetul coloanelor cu zilele lunii (ziua din săptămână, sărbătorile și zilele libere colorate). */
export function dayTitle(d: DayHeader, t: (k: string) => string) {
  const names = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
  return (
    <div style={{ textAlign: 'center', lineHeight: 1.1, color: d.holiday ? 'var(--ant-color-error)' : !d.working ? 'var(--ant-color-text-tertiary)' : undefined }}>
      <div>{d.day}</div>
      <div style={{ fontSize: 10, fontWeight: 400 }}>{t(`wt.weekdays.${names[d.weekday]}`).slice(0, 2)}</div>
    </div>
  )
}

export const cellStyle = (d: DayHeader): React.CSSProperties => ({
  padding: '2px 2px', textAlign: 'center', background: d.holiday ? 'var(--ant-color-error-bg)' : !d.working ? 'var(--ant-color-fill-quaternary)' : undefined,
})

/** Lista documentelor lunare pe subdiviziuni (graficul lunar sau tabela de pontaj), cu „nou” pe luna aleasă. */
export function MonthDocList({ endpoint, title, route, exportUrl }: { endpoint: string; title: string; route: string; exportUrl?: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const subs = useSubdivisionOptions()
  const [{ year, month }, setYm] = useState(defaultMonth())
  const { data, loading, reload } = useFetch<Paged<MonthDoc>>(endpoint, { year, month, page_size: 500 })
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()
  const rows = data?.results ?? []
  const used = new Set(rows.map((r) => r.subdivision))

  const create = async () => {
    const v = await form.validateFields()
    try {
      const r = await api.post<MonthDoc>(endpoint, { ...v, year, month })
      setCreating(false)
      navigate(`${route}/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const createAll = async () => {
    const missing = subs.filter((s) => !used.has(s.value))
    try {
      for (const s of missing) await api.post(endpoint, { subdivision: s.value, year, month })
      message.success(t('wt.doc.createdAll', { count: missing.length }))
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <Card title={title} extra={<Space wrap>
      <MonthPicker year={year} month={month} onChange={(y, m) => setYm({ year: y, month: m })} />
      {exportUrl && hasPerm('worktime.export') && <Button icon={<DownloadOutlined />} onClick={() => download(exportUrl, year, month)}>{t('wt.doc.export')}</Button>}
      {hasPerm('worktime.create') && <Button onClick={createAll} disabled={subs.every((s) => used.has(s.value))}>{t('wt.doc.newAll')}</Button>}
      {hasPerm('worktime.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setCreating(true) }}>{t('wt.doc.new')}</Button>}
    </Space>}>
      {!loading && rows.length === 0 && <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('wt.doc.emptyHint')} />}
      <Table<MonthDoc> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} noSettings
        rowTone={(r) => ROW_TONE.monthDoc(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`${route}/${r.id}`) })}
        columns={[
          { title: t('org.subdivision'), dataIndex: 'subdivision_name', render: (v: string, r) => <a onClick={() => navigate(`${route}/${r.id}`)}>{v}</a> },
          { title: t('ord.status'), dataIndex: 'status', width: 160, render: (v: string, r) => <Tag color={MONTH_STATUS_COLOR[v]}>{r.status_label}</Tag> },
          { title: t('wt.doc.lines'), dataIndex: 'lines_count', width: 100, align: 'right' },
          { title: t('org.notes'), dataIndex: 'note', render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
        ]} />
      <Modal open={creating} title={t('wt.doc.new')} onOk={create} onCancel={() => setCreating(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="subdivision" label={t('org.subdivision')} rules={[{ required: true }]} extra={t('wt.doc.newHint')}>
            <SubdivisionSelect allowClear={false} exclude={[...used]} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

/** Butoanele de stare ale unui document lunar: transmite, aprobă / închide, redeschide. */
export function useDocActions(endpoint: string, id: string | undefined, reload: () => void) {
  const { t } = useTranslation()
  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    try {
      await fn()
      if (ok) message.success(ok)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const post = (action: string, body?: unknown) => run(() => api.post(`${endpoint}${id}/${action}/`, body), action === 'fill' ? t('wt.doc.filled') : undefined)
  return { run, post }
}

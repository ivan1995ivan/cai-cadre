import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, Row, Select, Space, Table, Tabs, Tooltip, Typography, message } from 'antd'
import { CodeOutlined, DownloadOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { downloadFile, money } from '../../api/payroll'
import { defaultMonth } from '../../api/worktime'
import { useApp } from '../../auth/AppContext'
import { MonthPicker } from '../worktime/MonthDocs'
import { useEditGuard } from '../../components/UnsavedGuard'

interface Row { no: number; idnp: string; name: string; missing_idnp: boolean; [k: string]: unknown }
interface Report { rows: Row[]; total?: Record<string, number>; table1?: Record<string, number>; header_missing?: string[] }

const d = (v: unknown) => (v ? dayjs(String(v)).format('DD.MM.YYYY') : '')

/** Exportul: Excel (pentru verificare) și declarația electronică XML după schema SFS. */
function Exports({ url, params, name }: { url: string; params: Record<string, unknown>; name: string }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  if (!hasPerm('tax_reports.export')) return null
  const get = (kind: 'xlsx' | 'xml') => downloadFile(url, { ...params, export: kind }, `${name}.${kind}`).catch((e) => message.error(errorText(e)))
  return (
    <Space>
      <Button icon={<DownloadOutlined />} onClick={() => get('xlsx')}>{t('tax.export')}</Button>
      <Tooltip title={t('tax.xmlHint')}><Button type="primary" icon={<CodeOutlined />} onClick={() => get('xml')}>{t('tax.exportXml')}</Button></Tooltip>
    </Space>
  )
}

function Warnings({ data }: { data?: Report | null }) {
  const { t } = useTranslation()
  const noIdnp = new Set((data?.rows ?? []).filter((r) => r.missing_idnp).map((r) => r.name)).size
  const noCode = new Set((data?.rows ?? []).filter((r) => r.missing_code).map((r) => r.name)).size
  const header = data?.header_missing ?? []
  return (
    <>
      {header.length > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} title={t('tax.headerMissing', { list: header.join(', ') })} />}
      {noIdnp > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} title={t('tax.missingIdnp', { count: noIdnp })} />}
      {noCode > 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} title={t('tax.missingCode', { count: noCode })} />}
    </>
  )
}

const nameCol = (t: (k: string) => string, navigate: (p: string) => void) => ({
  title: t('staff.fullName'), dataIndex: 'name', render: (v: string, r: Row) => r.employee ? <a onClick={() => navigate(`/employees/${r.employee}`)}>{v}</a> : v,
})

/** Raportările: IPC21 (lunar), IALS21 (anual), IRM19 (din ordine) — previzualizare, Excel și XML pentru SFS. */
export default function TaxReportsPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'ipc21'
  return (
    <Card title={t('menu.taxReports')}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden items={[
        { key: 'ipc21', label: 'IPC21', children: <Ipc21 /> },
        { key: 'ials21', label: 'IALS21', children: <Ials21 /> },
        { key: 'irm19', label: 'IRM19', children: <Irm19 /> },
      ]} />
    </Card>
  )
}

function Ipc21() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [ym, setYm] = useState(defaultMonth())
  const { data, loading } = useFetch<Report>('/payroll/tax-reports/ipc21/', ym)
  const tot = data?.total ?? {}
  const t1 = data?.table1 ?? {}
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <MonthPicker year={ym.year} month={ym.month} onChange={(y, m) => setYm({ year: y, month: m })} />
        <Exports url="/payroll/tax-reports/ipc21/" params={ym} name={`IPC21-${ym.year}-${String(ym.month).padStart(2, '0')}`} />
      </Space>
      <Typography.Paragraph type="secondary">{t('tax.ipcHint')}</Typography.Paragraph>
      <Warnings data={data} />
      <Descriptions size="small" bordered column={{ xs: 1, md: 3 }} style={{ marginBottom: 12 }} title={t('tax.table1')} items={[
        { key: 'i', label: t('tax.cols.income'), children: money(t1.income) },
        { key: 't', label: t('tax.cols.tax'), children: money(t1.tax) },
        { key: 'c', label: t('tax.cols.cnam'), children: money(t1.cnam) },
      ]} />
      <Typography.Text strong>{t('tax.table2')}</Typography.Text>
      <Table<Row> rowKey={(r) => `${r.no}-${r.category}-${String(r.date_from)}`} size="small" loading={loading} dataSource={data?.rows ?? []}
        pagination={false} scroll={{ x: 1200 }} style={{ marginTop: 6 }}
        summary={() => (data?.rows.length ? <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={8}><b>{t('pp.total')} ({tot.persons})</b></Table.Summary.Cell>
          {['base', 'sick', 'cas'].map((k, i) => <Table.Summary.Cell key={k} index={i + 1} align="right"><b>{money(tot[k])}</b></Table.Summary.Cell>)}
        </Table.Summary.Row> : null)}
        columns={[
          { title: 'Nr.', dataIndex: 'no', width: 50 }, nameCol(t, navigate), { title: 'IDNP', dataIndex: 'idnp', width: 130 },
          { title: 'CPAS', dataIndex: 'cpas', width: 90 },
          { title: t('tax.period'), key: 'p', width: 180, render: (_: unknown, r) => `${d(r.date_from)} – ${d(r.date_to)}` },
          { title: t('tax.category'), dataIndex: 'category', width: 90 },
          { title: '%', dataIndex: 'tariff', width: 50 },
          { title: t('tax.occupationCode'), dataIndex: 'occupation_code', width: 100,
            render: (v: string) => v || <Typography.Text type="danger">—</Typography.Text> },
          { title: t('tax.cols.base'), dataIndex: 'base', width: 120, align: 'right', render: money },
          { title: t('tax.cols.sick'), dataIndex: 'sick', width: 120, align: 'right', render: money },
          { title: t('tax.cols.cas'), dataIndex: 'cas', width: 120, align: 'right', render: money },
        ]} />
    </>
  )
}

function Ials21() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [year, setYear] = useState(dayjs().month() === 0 ? dayjs().year() - 1 : dayjs().year())
  const { data, loading } = useFetch<Report>('/payroll/tax-reports/ials21/', { year })
  const tot = data?.total ?? {}
  const sums = ['income', 'P', 'M', 'Sm', 'N', 'H', 'exemption', 'cnam', 'tax']
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select style={{ width: 100 }} value={year} onChange={setYear} options={Array.from({ length: 5 }, (_, i) => dayjs().year() - i).map((y) => ({ value: y, label: y }))} />
        <Exports url="/payroll/tax-reports/ials21/" params={{ year }} name={`IALS21-${year}`} />
      </Space>
      <Typography.Paragraph type="secondary">{t('tax.ialsHint')}</Typography.Paragraph>
      <Warnings data={data} />
      <Table<Row> rowKey="no" size="small" loading={loading} dataSource={data?.rows ?? []} pagination={false} scroll={{ x: 1300 }}
        summary={() => (data?.rows.length ? <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={5}><b>{t('pp.total')} ({tot.persons})</b></Table.Summary.Cell>
          {sums.map((k, i) => <Table.Summary.Cell key={k} index={i + 1} align="right"><b>{money(tot[k])}</b></Table.Summary.Cell>)}
        </Table.Summary.Row> : null)}
        columns={[
          { title: 'Nr.', dataIndex: 'no', width: 50 }, { title: 'IDNP', dataIndex: 'idnp', width: 130 }, nameCol(t, navigate),
          { title: t('tax.spouseIdnp'), dataIndex: 'spouse_idnp', width: 130 },
          { title: t('tax.source'), dataIndex: 'source', width: 70 },
          ...sums.map((k) => ({ title: ['P', 'M', 'Sm', 'N', 'H'].includes(k) ? k : t(`tax.cols.${k}`), dataIndex: k,
            width: ['P', 'M', 'Sm', 'N', 'H'].includes(k) ? 90 : 120, align: 'right' as const, render: money })),
        ]} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>{t('tax.dependents', { count: (data as { dependents?: unknown[] } | null)?.dependents?.length ?? 0 })}</Typography.Paragraph>
    </>
  )
}

function Irm19() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [range, setRange] = useState<[Dayjs, Dayjs]>([dayjs().startOf('month'), dayjs()])
  const params = { date_from: range[0].format('YYYY-MM-DD'), date_to: range[1].format('YYYY-MM-DD') }
  const { data, loading } = useFetch<Report>('/payroll/tax-reports/irm19/', params)
  const today = dayjs().format('YYYY-MM-DD')
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <DatePicker.RangePicker format="DD.MM.YYYY" value={range} allowClear={false} onChange={(v) => v && v[0] && v[1] && setRange([v[0], v[1]])} />
        <Exports url="/payroll/tax-reports/irm19/" params={params} name={`IRM19-${params.date_from}-${params.date_to}`} />
      </Space>
      <Typography.Paragraph type="secondary">{t('tax.irmHint')}</Typography.Paragraph>
      <Warnings data={data} />
      <Table<Row> rowKey="no" size="small" loading={loading} dataSource={data?.rows ?? []} pagination={false} scroll={{ x: 1200 }}
        columns={[
          { title: 'Nr.', dataIndex: 'no', width: 50 }, nameCol(t, navigate), { title: 'IDNP', dataIndex: 'idnp', width: 130 },
          { title: t('tax.event'), dataIndex: 'event', width: 230 },
          { title: t('tax.irmCategory'), dataIndex: 'category', width: 80 },
          { title: t('tax.period'), key: 'p', width: 180, render: (_: unknown, r) => r.period_from ? `${d(r.period_from)} – ${d(r.period_to)}` : '' },
          { title: t('tax.irmCode'), dataIndex: 'code', width: 70 },
          { title: t('tax.irmReason'), dataIndex: 'reason', width: 80 },
          { title: t('ord.date'), dataIndex: 'date', width: 100, render: d },
          { title: t('ord.tab.order'), dataIndex: 'order', width: 160, render: (v: string, r) => <a onClick={() => navigate(`/orders/${r.order_id}`)}>{v}</a> },
          { title: t('tax.deadline'), dataIndex: 'deadline', width: 110, render: (v: string) =>
            <Typography.Text type={v < today ? 'danger' : undefined}>{d(v)}</Typography.Text> },
        ]} />
    </>
  )
}

/** Datele plătitorului pentru raportări (Administrare → Setări). */
export function TaxSettingsPage({ title }: { title: string }) {
  return <Card title={title}><TaxSettings /></Card>
}

function TaxSettings() {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const { data } = useFetch<Record<string, string>>('/payroll/tax-reports/settings/')
  useEffect(() => { if (data) form.setFieldsValue(data) }, [data, form])
  const { touch, clean } = useEditGuard(() => save())
  const save = async () => {
    try {
      await api.put('/payroll/tax-reports/settings/', await form.validateFields())
      message.success(t('common.saved'))
      clean()
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  const field = (name: string, extra?: string) => (
    <Col xs={24} md={12}><Form.Item name={name} label={t(`tax.set.${name}`)} extra={extra}><Input /></Form.Item></Col>
  )
  return (
    <Form form={form} layout="vertical" style={{ maxWidth: 760 }} onValuesChange={touch}>
      <Typography.Paragraph type="secondary">{t('tax.set.hint')}</Typography.Paragraph>
      <Row gutter={12}>
        {field('cnas_code', t('tax.set.cnasHint'))}
        {field('sfs_code', t('tax.set.sfsHint'))}
        {field('cuatm', t('tax.set.cuatmHint'))}
        {field('caem', t('tax.set.caemHint'))}
        {field('email')}
        {field('phone')}
        {field('income_source', t('tax.sourceHint'))}
      </Row>
      <Button type="primary" onClick={save}>{t('common.save')}</Button>
    </Form>
  )
}

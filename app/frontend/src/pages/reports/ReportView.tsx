import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, DatePicker, InputNumber, Select, Space, Statistic, Table, Typography, message } from 'antd'
import { ArrowLeftOutlined, FileExcelOutlined, PrinterOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import PeriodPicker, { type Period } from '../../components/PeriodPicker'
import PrintDialog from '../../components/PrintDialog'
import { errorText } from '../../api/client'
import { useDict } from '../../api/staff'
import { useFetch } from '../../api/hooks'
import { downloadFile } from '../../api/payroll'
import { useApp } from '../../auth/AppContext'
import { useTabTitle } from '../../layout/tabs'
import { REPORT_NAV } from '../../layout/nav'
import type { CatalogItem } from './ReportsPage'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import EmployeeSelect from '../../components/EmployeeSelect'

interface Column { key: string; title: string; type: 'text' | 'int' | 'num' | 'date' | 'pct' }
type Row = Record<string, unknown> & { _section?: string; _subtotal?: boolean; _link?: string }
interface ReportData {
  title: string
  subtitle: string
  columns: Column[]
  rows: Row[]
  totals: Row | null
  summary: { label: string; value: number | string }[]
  conclusion?: string
}

const ABSENCES = ['annual', 'extra', 'unpaid', 'maternity', 'paternity', 'childcare', 'childcare_unpaid', 'study', 'days_off', 'travel',
  'training', 'sick', 'idle', 'tech_unemployment']

function fmt(value: unknown, type: Column['type']) {
  if (value === null || value === undefined || value === '') return ''
  if (type === 'date') return dayjs(String(value)).format('DD.MM.YYYY')
  if (type === 'int' || type === 'num' || type === 'pct') {
    const n = Number(value)
    const s = n.toLocaleString('ro-RO', { maximumFractionDigits: 2 })
    return type === 'pct' ? `${s} %` : s
  }
  return String(value)
}

/** Un raport din catalog: filtrele lui, tabelul cu secțiuni și totaluri, rezumatul, Excel și tipar. */
export default function ReportView({ reportKey, embedded }: { reportKey?: string; embedded?: boolean } = {}) {
  const { key: routeKey = '' } = useParams()
  const key = reportKey ?? routeKey
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const { data: catalog } = useFetch<CatalogItem[]>('/reports/', { lang: i18n.language })
  const info = catalog?.find((c) => c.key === key)
  const has = (f: string) => !!info?.filters.includes(f)
  // raportul din meniu își ia fila din denumirea lui de meniu (se traduce singură); ceilalți — titlul din catalog
  useTabTitle(embedded || REPORT_NAV.some((r) => r.path === `/reports/${key}`) ? null : info?.title)
  const now = dayjs()
  const [period, setPeriod] = useState<Period>([now.startOf('month'), now])
  const [onDate, setOnDate] = useState<Dayjs>(now)
  const [month, setMonth] = useState<Dayjs>(now)
  const [year, setYear] = useState<number>(now.year())
  const [subdivision, setSubdivision] = useState<number | undefined>()
  const [category, setCategory] = useState<string | undefined>()
  const staffCategories = useDict('staff_category')
  const [kinds, setKinds] = useState<'main' | 'all'>('main')
  const [absence, setAbsence] = useState<string | undefined>()
  const [search] = useSearchParams()
  const [employee, setEmployee] = useState<number | undefined>(Number(search.get('employee')) || undefined)  // din fișa angajatului
  const [printOpen, setPrintOpen] = useState(false)

  const params = useMemo(() => {
    if (!info) return null
    const p: Record<string, unknown> = { lang: i18n.language }
    if (has('period') && period) Object.assign(p, { date_from: period[0].format('YYYY-MM-DD'), date_to: period[1].format('YYYY-MM-DD') })
    if (has('on_date')) p.on_date = onDate.format('YYYY-MM-DD')
    if (has('month')) Object.assign(p, { year: month.year(), month: month.month() + 1 })
    if (has('year')) p.year = year
    if (has('subdivision') && subdivision) p.subdivision = subdivision
    if (has('category') && category) p.category = category
    if (has('kinds')) p.kinds = kinds
    if (has('absence_kind') && absence) p.absence_kind = absence
    if (has('employee')) {
      if (!employee) return null  // raportul despre un angajat: întâi se alege angajatul
      p.employee = employee
    }
    return p
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [info, period, onDate, month, year, subdivision, category, kinds, absence, employee, i18n.language])
  const { data, loading, error } = useFetch<ReportData>(params ? `/reports/${key}/` : null, params ?? undefined)

  const columns = (data?.columns ?? []).map((c, i) => ({
    title: c.title, dataIndex: c.key, key: c.key, align: (['int', 'num', 'pct'].includes(c.type) ? 'right' : 'left') as 'right' | 'left',
    onCell: (r: Row) => (r._section !== undefined ? { colSpan: i === 0 ? (data?.columns.length ?? 1) : 0 } : {}),
    render: (v: unknown, r: Row) => (r._section !== undefined ? (i === 0 ? <b>{r._section}</b> : null)
      : r._subtotal ? <b>{fmt(v, c.type)}</b> : r._link && c.type === 'text' && i === (data?.columns.findIndex((x) => x.type === 'text') ?? -1)
        ? <a onClick={() => navigate(r._link as string)}>{fmt(v, c.type)}</a> : fmt(v, c.type)),
  }))
  const excel = async () => {
    try {
      await downloadFile(`/reports/${key}/`, { ...params, export: 'xlsx' }, `${key}.xlsx`)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const buttons = <Space>
    {(hasPerm('reports.export') || hasPerm('military.export')) && <Button icon={<FileExcelOutlined />} onClick={excel} disabled={!data}>Excel</Button>}
    <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)} disabled={!data}>{t('rep.print')}</Button>
  </Space>
  const body = (
    <>
      {info?.hint && <Typography.Paragraph type="secondary">{info.hint}</Typography.Paragraph>}
      <Space wrap style={{ marginBottom: 12 }}>
        {embedded && buttons}
        {has('employee') && <EmployeeSelect style={{ width: 320 }} placeholder={t('rep.employee')} value={employee}
          onChange={(v) => setEmployee(typeof v === 'number' ? v : undefined)} />}
        {has('period') && <PeriodPicker value={period} onChange={setPeriod} />}
        {has('on_date') && <DatePicker format="DD.MM.YYYY" value={onDate} allowClear={false} onChange={(v) => v && setOnDate(v)}
          prefix={t('rep.onDate')} />}
        {has('month') && <DatePicker picker="month" format="MM.YYYY" value={month} allowClear={false} onChange={(v) => v && setMonth(v)} />}
        {has('year') && <InputNumber min={2000} max={2100} value={year} onChange={(v) => v && setYear(v)} prefix={t('rep.year')} style={{ width: 140 }} />}
        {has('subdivision') && <SubdivisionSelect style={{ width: 300 }} placeholder={t('org.subdivision')}
          value={subdivision} onChange={(v) => setSubdivision(typeof v === 'number' ? v : undefined)} />}
        {has('category') && <Select allowClear style={{ width: 240 }} placeholder={t('rep.category')} value={category} onChange={setCategory}
          options={[...staffCategories.map((c) => ({ value: String(c.value), label: c.label })), { value: 'none', label: t('org.noCategory') }]} />}
        {has('kinds') && <Select style={{ width: 230 }} value={kinds} onChange={setKinds}
          options={[{ value: 'main', label: t('rep.kindsMain') }, { value: 'all', label: t('rep.kindsAll') }]} />}
        {has('absence_kind') && <Select allowClear style={{ width: 260 }} placeholder={t('rep.allAbsences')} value={absence} onChange={setAbsence}
          options={ABSENCES.map((k) => ({ value: k, label: t(`rep.absence.${k}`) }))} />}
      </Space>
      {!!error && <Alert type="error" showIcon title={errorText(error)} style={{ marginBottom: 12 }} />}
      {data && <>
        {data.subtitle && <Typography.Paragraph strong>{data.subtitle}</Typography.Paragraph>}
        {!!data.summary.length && <Space wrap size={32} style={{ marginBottom: 16 }}>
          {data.summary.map((s) => <Statistic key={s.label} title={s.label} value={typeof s.value === 'number' ? fmt(s.value, 'num') : s.value} />)}
        </Space>}
      </>}
      <Table<Row> size="small" loading={loading} dataSource={data?.rows ?? []} columns={columns} scroll={{ x: 'max-content' }}
        rowKey={(r) => JSON.stringify(r)} pagination={(data?.rows.length ?? 0) > 200 ? { pageSize: 200 } : false}
        rowClassName={(r) => (r._section !== undefined ? 'doc-row-section' : '')}
        onRow={(r) => ({ onDoubleClick: () => r._link && navigate(r._link) })}
        summary={() => data?.totals ? (
          <Table.Summary.Row>
            {data.columns.map((c, i) => <Table.Summary.Cell key={c.key} index={i} align={['int', 'num', 'pct'].includes(c.type) ? 'right' : 'left'}>
              <b>{fmt(data.totals?.[c.key], c.type)}</b></Table.Summary.Cell>)}
          </Table.Summary.Row>) : null} />
      {has('employee') && !employee && <Typography.Paragraph type="secondary">{t('rep.chooseEmployee')}</Typography.Paragraph>}
      {data?.conclusion && <Alert type="info" showIcon style={{ marginTop: 12 }} title={<b>{data.conclusion}</b>} />}
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="report" url={`/reports/${key}/print/`}
        params={params ?? {}} optionKeys={[]} title={info?.title ?? ''} />
    </>
  )
  if (embedded) return body
  return (
    <Card title={<Space><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/reports')} />{info?.title ?? t('menu.reports')}</Space>}
      extra={buttons}>
      {body}
    </Card>
  )
}

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber, Row, Select, Space, Spin, Tag, Typography, message } from 'antd'
import { DownloadOutlined, PrinterOutlined, SaveOutlined, SettingOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import CloseForm from '../../components/CloseForm'
import PrintDialog from '../../components/PrintDialog'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { DOC_HEAD } from '../orders/OrderEditor'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { downloadFile, money, type ItParkMonthData, type ItParkPerson, type ItParkRow, type ItParkYear } from '../../api/payroll'
import { useApp } from '../../auth/AppContext'
import { useTabTitle } from '../../layout/tabs'

const monthName = (m: number, y: number) => `${dayjs().month(m - 1).format('MMMM')} ${y}`

/** Impozitul unic IT Park pe lunile anului: venitul din vânzări (scris de contabil), angajații, impozitul datorat. */
export default function ItParkPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [year, setYear] = useState(dayjs().year())
  const { data, loading } = useFetch<ItParkYear>('/payroll/it-park/', { year })
  const months = data?.months ?? []
  const today = dayjs().format('YYYY-MM-DD')
  const total = months.reduce((s, m) => s + m.due, 0)
  return (
    <Card title={t('menu.itPark')} extra={<Space wrap>
      <Select style={{ width: 100 }} value={year} onChange={setYear}
        options={Array.from({ length: 5 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />
      {hasPerm('payroll_settings.view') && <Button icon={<SettingOutlined />} onClick={() => navigate('/payroll/settings/constants')}>{t('itp.regimeButton')}</Button>}
    </Space>}>
      <Space style={{ marginBottom: 12 }} wrap>
        <Typography.Text>{t('itp.regimeNow')}</Typography.Text>
        <Tag color={data?.regime === 'it_park' ? 'purple' : 'default'}>{t(`itp.regimes.${data?.regime ?? 'general'}`)}</Tag>
        <Typography.Text type="secondary">{t('itp.listHint')}</Typography.Text>
      </Space>
      {!loading && data && !months.length && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('itp.noMonths', { year })} />}
      <Table<ItParkMonthData> rowKey="month" size="small" loading={loading} dataSource={months} pagination={false} exportName={`${t('menu.itPark')} ${year}`}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/payroll/it-park/${r.year}/${r.month}`) })}
        summary={() => (months.length ? <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={6}><b>{t('pp.total')}</b></Table.Summary.Cell>
          <Table.Summary.Cell index={1} align="right"><b>{money(total)}</b></Table.Summary.Cell>
          <Table.Summary.Cell index={2} colSpan={2} />
        </Table.Summary.Row> : null)}
        columns={[
          { title: t('pay.month'), key: 'm', width: 150, render: (_: unknown, r) =>
            <a onClick={() => navigate(`/payroll/it-park/${r.year}/${r.month}`)}>{monthName(r.month, r.year)}</a> },
          { title: t('itp.regime'), dataIndex: 'it_park', width: 110, render: (v: boolean) => <Tag color={v ? 'purple' : 'default'}>{t(`itp.regimes.${v ? 'it_park' : 'general'}`)}</Tag> },
          { title: t('itp.sales'), dataIndex: 'sales_income', width: 140, align: 'right', render: (v: number | null) =>
            v === null ? <Typography.Text type="warning">{t('itp.notEntered')}</Typography.Text> : money(v) || '0,00' },
          { title: t('itp.employees'), dataIndex: 'employees', width: 90, align: 'right' },
          { title: t('itp.bySales'), dataIndex: 'by_sales', width: 120, align: 'right', render: money },
          { title: t('itp.minimum'), dataIndex: 'minimum', width: 120, align: 'right', render: money },
          { title: t('itp.due'), dataIndex: 'due', width: 130, align: 'right', render: (v: number) => <b>{money(v) || '0,00'}</b> },
          { title: t('itp.deadline'), dataIndex: 'deadline', width: 110, render: (v: string, r) =>
            <Typography.Text type={!r.submitted_on && v < today ? 'danger' : undefined}>{dayjs(v).format('DD.MM.YYYY')}</Typography.Text> },
          { title: t('itp.submitted'), dataIndex: 'submitted_on', width: 110, render: (v: string | null) => (v ? dayjs(v).format('DD.MM.YYYY') : '') },
        ]} />
    </Card>
  )
}

/** Luna impozitului unic: venitul din vânzări, rândurile IU17 (010 / 020 / 030) cu temeiurile, angajații numărați. */
export function ItParkMonthEditor() {
  const { t } = useTranslation()
  const { year: y, month: m } = useParams()
  const year = Number(y), month = Number(m)
  const { hasPerm } = useApp()
  const url = `/payroll/it-park/${year}/${month}/`
  const { data, reload } = useFetch<ItParkMonthData>(url)
  useTabTitle(data ? { key: 'desk.tab.itPark', params: { month: `${String(month).padStart(2, '0')}.${year}` } } : null)
  const [form] = Form.useForm()
  const [dirty, setDirty] = useState(false)
  const [print, setPrint] = useState(false)
  const canEdit = hasPerm('tax_reports.create') || hasPerm('payroll.edit')

  useEffect(() => {
    if (!data) return
    form.setFieldsValue({ sales_income: data.sales_income, submitted_on: data.submitted_on ? dayjs(data.submitted_on) : null, note: data.note })
    setDirty(false)
  }, [data, form])

  const save = async (quiet = false) => {
    try {
      const v = await form.validateFields()
      await api.put(url, { sales_income: v.sales_income ?? null, submitted_on: v.submitted_on ? v.submitted_on.format('YYYY-MM-DD') : null,
        note: v.note ?? '' })
      setDirty(false)
      if (!quiet) message.success(t('common.saved'))
      reload()
      return true
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return false
      message.error(errorText(e))
      return false
    }
  }
  useUnsavedGuard(dirty && canEdit, () => save(true))

  if (!data) return <Spin />
  const people = data.people ?? []
  return (
    <Card className="doc-form" title={<Space wrap>{t('itp.monthTitle', { month: monthName(month, year) })}
      <Tag color={data.it_park ? 'purple' : 'default'}>{t(`itp.regimes.${data.it_park ? 'it_park' : 'general'}`)}</Tag></Space>}
      extra={<Space wrap>
        {canEdit && <Button icon={<SaveOutlined />} disabled={!dirty} onClick={() => save()}>{t('common.save')}</Button>}
        {hasPerm('tax_reports.export') && <Button icon={<DownloadOutlined />}
          onClick={() => downloadFile(url, { export: 'xlsx' }, `IU17-${year}-${String(month).padStart(2, '0')}.xlsx`).catch((e) => message.error(errorText(e)))}>
          {t('tax.export')}</Button>}
        <Button icon={<PrinterOutlined />} onClick={() => setPrint(true)}>{t('lv.print')}</Button>
        <CloseForm to="/payroll/it-park" />
      </Space>}>
      {!data.it_park && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('itp.notInRegime')} />}
      {data.it_park && !data.sales_entered && <Alert type="warning" showIcon style={{ marginBottom: 12 }}
        title={t('itp.salesMissing', { date: dayjs(data.deadline).format('DD.MM.YYYY') })} />}
      <Form form={form} {...DOC_HEAD} disabled={!canEdit} onValuesChange={() => setDirty(true)}>
        <Row gutter={16}>
          <Col xs={24} md={10}><Form.Item name="sales_income" label={t('itp.sales')} extra={t('itp.salesHint')}>
            <InputNumber<number> min={0} step={1000} precision={2} style={{ width: '100%' }} placeholder={t('itp.notEntered')}
              formatter={(v) => (v === undefined || v === null ? '' : String(v).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, ' '))}
              parser={(v) => (v ?? '').replace(/\s/g, '').replace(',', '.') as unknown as number} /></Form.Item></Col>
          <Col xs={24} md={6}><Form.Item name="submitted_on" label={t('itp.submitted')}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={24} md={8}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row>
      </Form>
      <Typography.Title level={5}>{t('itp.iu17Title')}</Typography.Title>
      <Table<ItParkRow> rowKey="code" size="small" dataSource={data.rows} pagination={false} noSettings style={{ maxWidth: 1100 }}
        columns={[
          { title: t('itp.indicator'), dataIndex: 'label', render: (v: string, r) => <Space orientation="vertical" size={0}>
            <span style={r.code === '030' ? { fontWeight: 600 } : undefined}>{t(`itp.rows.c${r.code}`, { defaultValue: v })}</span>
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>{t(`itp.basis.c${r.code}`, { defaultValue: r.basis })}</Typography.Text></Space> },
          { title: t('itp.code'), dataIndex: 'code', width: 70, align: 'center' },
          { title: t('itp.base'), dataIndex: 'base', width: 150, align: 'right', render: (v: number | null, r) =>
            r.code === '020' ? v : r.code === '010' && !data.sales_entered ? <Typography.Text type="warning">{t('itp.notEntered')}</Typography.Text> : money(v) },
          { title: t('itp.rate'), dataIndex: 'rate', width: 220 },
          { title: t('itp.amount'), dataIndex: 'amount', width: 140, align: 'right', render: (v: number, r) =>
            r.code === '030' ? <b>{money(v) || '0,00'}</b> : money(v) || '0,00' },
        ]} />
      <Descriptions size="small" bordered column={{ xs: 1, md: 3 }} style={{ margin: '12px 0' }} items={[
        { key: 'due', label: t('itp.due'), children: <b>{money(data.due) || '0,00'}</b> },
        { key: 'rule', label: t('itp.rule'), children: t(`itp.rules.${data.rule}`) },
        { key: 'dl', label: t('itp.deadline'), children: dayjs(data.deadline).format('DD.MM.YYYY') },
      ]} />
      <Typography.Paragraph type="secondary">{t('itp.iu17Hint')}</Typography.Paragraph>
      <Typography.Title level={5}>{t('itp.peopleTitle', { count: data.employees, total: data.persons })}</Typography.Title>
      <Table<ItParkPerson> rowKey="employee" size="small" dataSource={people} pagination={false} exportName={`IU17 ${month}.${year}`}
        columns={[
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 90 },
          { title: t('staff.fullName'), dataIndex: 'name', width: 230 },
          { title: 'IDNP', dataIndex: 'idnp', width: 130 },
          { title: t('itp.jobs'), dataIndex: 'job_list', render: (v: ItParkPerson['job_list']) =>
            v.map((j) => `${t(`staff.kinds.${j.kind}`)}: ${j.occupation}${j.rate !== 1 ? ` (${j.rate})` : ''}`).join('; ') },
          { title: t('itp.workedDays'), dataIndex: 'worked_days', width: 90, align: 'right' },
          { title: t('itp.counted'), dataIndex: 'counted', width: 280, render: (v: boolean, r) =>
            <Space size={4} wrap><Tag color={v ? 'green' : 'default'}>{t(v ? 'common.yes' : 'common.no')}</Tag>
              <Typography.Text type="secondary">{t(`itp.reasons.${r.reason_code}`, { count: r.worked_days })}</Typography.Text></Space> },
        ]} />
      {print && <PrintDialog open onClose={() => setPrint(false)} docType="it_park_tax" url={url}
        params={{ print: 1 }} optionKeys={[]} title={t('itp.monthTitle', { month: monthName(month, year) })} />}
    </Card>
  )
}

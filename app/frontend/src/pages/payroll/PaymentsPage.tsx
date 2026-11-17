import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, Card, DatePicker, Form, Modal, Select, Space, Tabs, Tag, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { PAYMENT_STATUS_COLOR, money, type DebtRow, type Payment, type Payroll } from '../../api/payroll'
import { defaultMonth } from '../../api/worktime'
import { useApp } from '../../auth/AppContext'
import { MonthPicker } from '../worktime/MonthDocs'

/** Îndreptările spre plată (salariu și avans) ale lunii — impozitul se reține la ele — și soldul salarial. */
export default function PaymentsPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const [ym, setYm] = useState(defaultMonth())
  const tab = params.get('tab') || 'payments'
  return (
    <Card title={t('menu.payrollPayments')} extra={<MonthPicker year={ym.year} month={ym.month} onChange={(y, m) => setYm({ year: y, month: m })} />}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden items={[
        { key: 'payments', label: t('pp.tabs.payments'), children: <PaymentsTab year={ym.year} month={ym.month} /> },
        { key: 'debts', label: t('pp.tabs.debts'), children: <DebtsTab year={ym.year} month={ym.month} /> },
      ]} />
    </Card>
  )
}

function PaymentsTab({ year, month }: { year: number; month: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const { data, loading } = useFetch<Paged<Payment>>('/payroll/payments/', { year, month, page_size: 200 })
  // calculele aprobate ale lunii — baza îndreptării pe salariu
  const { data: bases } = useFetch<Paged<Payroll>>('/payroll/payrolls/', { year, month, status: 'approved', page_size: 200 })
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()
  const kind = Form.useWatch('kind', form)
  const rows = data?.results ?? []

  const create = async () => {
    const v = await form.validateFields()
    const payroll = v.kind === 'salary' && v.payroll ? v.payroll : null
    try {
      const r = await api.post<Payment>('/payroll/payments/', { ...v, payroll, year, month, date: v.date.format('YYYY-MM-DD') })
      setCreating(false)
      navigate(`/payroll/payments/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        {hasPerm('payroll.create') && <Button type="primary" icon={<PlusOutlined />}
          onClick={() => { form.resetFields(); form.setFieldsValue({ kind: 'salary', payroll: 0, method: 'all', date: dayjs() }); setCreating(true) }}>{t('pp.new')}</Button>}
      </Space>
      {!loading && rows.length === 0 && <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('pp.emptyHint')} />}
      <Table<Payment> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} noSettings
        rowTone={(r) => ROW_TONE.payment(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/payroll/payments/${r.id}`) })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 140, render: (v: string, r) => <a onClick={() => navigate(`/payroll/payments/${r.id}`)}>{v}</a> },
          { title: t('ord.date'), dataIndex: 'date', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('pp.kind'), dataIndex: 'kind_label', width: 100 },
          { title: t('pp.base'), dataIndex: 'payroll_number', width: 200, render: (v: string, r) => r.kind !== 'salary' ? ''
            : v ? <a onClick={() => navigate(`/payroll/${r.payroll}`)}>{v}</a> : <Typography.Text type="secondary">{t('pp.onBalanceShort')}</Typography.Text> },
          { title: t('pp.method'), dataIndex: 'method_label', width: 180 },
          { title: t('ord.status'), dataIndex: 'status', width: 110, render: (v: string, r) => <Tag color={PAYMENT_STATUS_COLOR[v]}>{r.status_label}</Tag> },
          { title: t('pp.count'), key: 'n', width: 80, align: 'right', render: (_: unknown, r) => r.totals.count },
          { title: t('pp.card'), key: 'card', width: 130, align: 'right', render: (_: unknown, r) => money(r.totals.card) },
          { title: t('pp.cash'), key: 'cash', width: 130, align: 'right', render: (_: unknown, r) => money(r.totals.cash) },
          { title: t('pp.total'), key: 'total', width: 140, align: 'right', render: (_: unknown, r) => <b>{money(r.totals.total)}</b> },
          { title: t('pp.paidOn'), key: 'paid', render: (_: unknown, r) => r.paid_on ? `${dayjs(r.paid_on).format('DD.MM.YYYY')} ${r.reference}` : '' },
        ]} />
      <Modal open={creating} title={t('pp.new')} onOk={create} onCancel={() => setCreating(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="kind" label={t('pp.kind')} rules={[{ required: true }]}>
            <Select options={['salary', 'advance'].map((k) => ({ value: k, label: t(`pp.kinds.${k}`) }))} />
          </Form.Item>
          {kind === 'salary' && <Form.Item name="payroll" label={t('pp.base')} extra={t('pp.baseHint')}>
            <Select options={[{ value: 0, label: t('pp.onBalance') }, ...(bases?.results ?? []).map((x) => ({
              value: x.id, label: `${t('pp.baseLabel', { number: x.number, month: String(x.month).padStart(2, '0'), year: x.year })}${x.subdivision_name ? ` · ${x.subdivision_name}` : ''}`,
            }))]} />
          </Form.Item>}
          <Form.Item name="method" label={t('pp.method')} rules={[{ required: true }]}>
            <Select options={['all', 'card', 'cash'].map((k) => ({ value: k, label: t(`pp.methods.${k}`) }))} />
          </Form.Item>
          <Form.Item name="date" label={t('ord.date')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" /></Form.Item>
          <Typography.Text type="secondary">{t('pp.newHint')}</Typography.Text>
        </Form>
      </Modal>
    </>
  )
}

function DebtsTab({ year, month }: { year: number; month: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data, loading } = useFetch<{ rows: DebtRow[]; total: number }>('/payroll/debts/', { year, month })
  return (
    <>
      <Typography.Paragraph type="secondary">{t('pp.debtsHint')}</Typography.Paragraph>
      <Table<DebtRow> rowKey="employee" size="small" loading={loading} dataSource={data?.rows ?? []} pagination={false}
        exportName={t('pp.tabs.debts')}
        summary={() => data?.rows.length ? <Table.Summary.Row>
          <Table.Summary.Cell index={0} colSpan={4}><b>{t('pp.total')}</b></Table.Summary.Cell>
          <Table.Summary.Cell index={1} align="right"><b>{money(data.total)}</b></Table.Summary.Cell>
        </Table.Summary.Row> : null}
        columns={[
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 90 },
          { title: t('staff.fullName'), dataIndex: 'name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}?tab=pay`)}>{v}</a> },
          { title: t('pp.owed'), dataIndex: 'owed', width: 150, align: 'right', render: money },
          { title: t('pp.paidSum'), dataIndex: 'paid', width: 150, align: 'right', render: money },
          { title: t('pp.debt'), dataIndex: 'debt', width: 150, align: 'right', render: (v: number) =>
            <Typography.Text strong type={v < 0 ? 'warning' : undefined}>{money(v)}</Typography.Text> },
        ]} />
    </>
  )
}

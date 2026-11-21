import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, DatePicker, Form, Modal, Space, Tag, Typography, message } from 'antd'
import { PlusOutlined, SettingOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { PAYROLL_STATUS_COLOR, money, type Payroll } from '../../api/payroll'
import { defaultMonth } from '../../api/worktime'
import { useApp } from '../../auth/AppContext'
import { MonthPicker } from '../worktime/MonthDocs'
import SubdivisionSelect from '../../components/SubdivisionSelect'

/** Calculele salariului pe luni (toată întreprinderea sau pe subdiviziuni): acumulările, reținerile, CAS. Impozitul și CNAM
 *  se rețin la plată — în îndreptarea spre plată făcută din calculul aprobat. */
export default function PayrollsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [{ year, month }, setYm] = useState(defaultMonth())
  const { data, loading } = useFetch<Paged<Payroll>>('/payroll/payrolls/', { year, month, page_size: 200 })
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()
  const rows = data?.results ?? []

  const create = async () => {
    const v = await form.validateFields()
    try {
      const r = await api.post<Payroll>('/payroll/payrolls/', { ...v, year, month, date: v.date.format('YYYY-MM-DD') })
      setCreating(false)
      navigate(`/payroll/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <Card title={t('menu.payroll')} extra={<Space wrap>
      <MonthPicker year={year} month={month} onChange={(y, m) => setYm({ year: y, month: m })} />
      {hasPerm('payroll_settings.view') && <Button icon={<SettingOutlined />} onClick={() => navigate('/payroll/settings/types')}>{t('menu.payrollTypes')}</Button>}
      {hasPerm('payroll.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); form.setFieldsValue({ date: dayjs() }); setCreating(true) }}>{t('pay.new')}</Button>}
    </Space>}>
      {!loading && rows.length === 0 && <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('pay.emptyHint')} />}
      <Table<Payroll> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} noSettings
        rowTone={(r) => ROW_TONE.payroll(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/payroll/${r.id}`) })}
        columns={[
          { title: t('ord.number'), dataIndex: 'number', width: 130, render: (v: string, r) => <a onClick={() => navigate(`/payroll/${r.id}`)}>{v}</a> },
          { title: t('ord.date'), dataIndex: 'date', width: 100, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('org.subdivision'), dataIndex: 'subdivision_name', render: (v: string) => v || <Typography.Text type="secondary">{t('pay.whole')}</Typography.Text> },
          { title: t('ord.status'), dataIndex: 'status', width: 120, render: (v: string, r) => <Tag color={PAYROLL_STATUS_COLOR[v]}>{r.status_label}</Tag> },
          { title: t('pay.lines'), dataIndex: 'lines_count', width: 90, align: 'right' },
          { title: t('pay.gross'), key: 'g', width: 130, align: 'right', render: (_: unknown, r) => money(r.totals?.gross) },
          { title: t('pay.deductions'), key: 'd', width: 110, align: 'right', render: (_: unknown, r) => money(r.totals?.deductions) },
          { title: t('pay.net'), key: 'n', width: 130, align: 'right', render: (_: unknown, r) => <b>{money(r.totals?.net)}</b> },
          { title: t('pay.cas'), key: 'c', width: 120, align: 'right', render: (_: unknown, r) => money(r.totals?.cas) },
        ]} />
      <Modal open={creating} title={t('pay.new')} onOk={create} onCancel={() => setCreating(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="date" label={t('ord.date')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" /></Form.Item>
          <Form.Item name="subdivision" label={t('org.subdivision')} extra={t('pay.newHint')}>
            <SubdivisionSelect placeholder={t('pay.whole')} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

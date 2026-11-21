import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert, Button, Card, Checkbox, Col, DatePicker, Descriptions, Empty, Form, Input, InputNumber, Modal, Row, Select, Space, Table, Tag,
  Typography, message,
} from 'antd'
import { EditOutlined, PauseCircleOutlined, PlayCircleOutlined, PlusOutlined, StopOutlined, SwapOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import { api, errorText, fieldErrors } from '../../api/client'
import { RateInput, fmtRate, rateProps } from '../../components/RateInput'
import JobScheduleBox from '../worktime/JobScheduleBox'
import { useFetch } from '../../api/hooks'
import { EMPLOYMENT_KINDS, type Employee, type Employment, type HistoryRow } from '../../api/staff'
import { useApp } from '../../auth/AppContext'
import RefSelect from '../../components/RefSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'

type Mode = 'hire' | 'change' | 'suspend' | 'resume' | 'terminate' | 'edit'
const STATUS_COLOR: Record<string, string> = { active: 'green', suspended: 'orange', ended: 'default' }
const d = (v: string | null | undefined) => (v ? dayjs(v).format('DD.MM.YYYY') : '')
const num = (v: string | null | undefined) => (v === null || v === undefined || v === '' ? '—' : Number(v).toLocaleString('ro-MD', { maximumFractionDigits: 2 }))

/** Raporturile de muncă ale angajatului (de bază, cumul, suplinire) cu istoricul lor „din data”. */
export default function EmploymentsTab({ employee, onChanged }: { employee: Employee; onChanged: () => void }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const { data, reload } = useFetch<Employment[]>('/staff/employments/', { employee: employee.id })
  const [mode, setMode] = useState<Mode | null>(null)
  const [current, setCurrent] = useState<Employment | null>(null)
  const [form] = Form.useForm()
  const canEdit = hasPerm('employees.edit') || hasPerm('contracts.edit')
  const canCreate = hasPerm('employees.create') || hasPerm('contracts.create')
  const today = dayjs()

  const open = (m: Mode, emp?: Employment) => {
    setMode(m)
    setCurrent(emp ?? null)
    form.resetFields()
    if (m === 'hire') form.setFieldsValue({ kind: (data ?? []).some((e) => e.status !== 'ended' && e.kind === 'main') ? 'internal' : 'main', rate: 1, date_from: today })
    if (m === 'change' && emp) form.setFieldsValue({ date: today, subdivision: emp.subdivision, occupation: emp.occupation, rate: Number(emp.rate),
      base_salary: emp.base_salary === null ? undefined : Number(emp.base_salary), allowance_pct: emp.allowance_pct === null ? undefined : Number(emp.allowance_pct),
      combination_pct: emp.combination_pct === null ? undefined : Number(emp.combination_pct) })
    if (m === 'edit' && emp) form.setFieldsValue({ ...emp, date_from: dayjs(emp.date_from),
      date_to: emp.date_to ? dayjs(emp.date_to) : null, probation_until: emp.probation_until ? dayjs(emp.probation_until) : null,
      contract_date: emp.contract_date ? dayjs(emp.contract_date) : null, rate: Number(emp.rate),
      base_salary: emp.base_salary === null ? undefined : Number(emp.base_salary), allowance_pct: emp.allowance_pct === null ? undefined : Number(emp.allowance_pct),
      combination_pct: emp.combination_pct === null ? undefined : Number(emp.combination_pct) })
    if (m === 'suspend' || m === 'resume' || m === 'terminate') form.setFieldsValue({ date: today })
  }

  const dates = (v: Record<string, unknown>) => Object.fromEntries(Object.entries(v).map(([k, x]) => [k, dayjs.isDayjs(x) ? (x as Dayjs).format('YYYY-MM-DD') : x]))

  const submit = async () => {
    const v = dates(await form.validateFields())
    try {
      if (mode === 'hire') await api.post('/staff/employments/', { ...v, employee: employee.id })
      else if (mode === 'edit') await api.patch(`/staff/employments/${current!.id}/`, v)
      else await api.post(`/staff/employments/${current!.id}/${mode}/`, v)
      message.success(t('common.saved'))
      setMode(null)
      reload()
      onChanged()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  const rows = data ?? []
  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      <Space wrap>
        {canCreate && <Button icon={<PlusOutlined />} onClick={() => open('hire')}>{t('staff.job.hire')}</Button>}
        <Typography.Text type="secondary">{t('staff.job.ordersHint')}</Typography.Text>
      </Space>
      {rows.length === 0 && <Empty description={t('staff.job.none')} />}
      {rows.map((emp) => (
        <Card key={emp.id} size="small" type="inner"
          title={<Space wrap>
            <Tag color="blue">{emp.kind_label}</Tag>
            <b>{emp.occupation_name}</b>
            <span>· {emp.subdivision_name}</span>
            <Tag color={STATUS_COLOR[emp.status]}>{emp.status_label}{emp.status === 'suspended' && emp.suspended_from ? ` ${d(emp.suspended_from)}` : ''}</Tag>
          </Space>}
          extra={canEdit && emp.status !== 'ended' && <Space wrap size={4}>
            <Button size="small" icon={<SwapOutlined />} onClick={() => open('change', emp)}>{t('staff.job.change')}</Button>
            {emp.status === 'active' && <Button size="small" icon={<PauseCircleOutlined />} onClick={() => open('suspend', emp)}>{t('staff.job.suspend')}</Button>}
            {emp.status === 'suspended' && <Button size="small" icon={<PlayCircleOutlined />} onClick={() => open('resume', emp)}>{t('staff.job.resume')}</Button>}
            <Button size="small" danger icon={<StopOutlined />} onClick={() => open('terminate', emp)}>{t('staff.job.terminate')}</Button>
            <Button size="small" type="text" icon={<EditOutlined />} onClick={() => open('edit', emp)} title={t('staff.job.edit')} />
          </Space>}>
          <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
            { key: 'from', label: t('staff.hiredOn'), children: d(emp.date_from) },
            { key: 'rate', label: t('staff.rate'), children: fmtRate(emp.rate) },
            ...(Number(emp.combination_pct) ? [{ key: 'comb', label: t('staff.combinationPct'), children: `${num(emp.combination_pct)}%` }] : []),
            { key: 'salary', label: t('org.sl.salary'), children: emp.base_salary === null ? '—' : `${num(emp.base_salary)} lei${Number(emp.allowance_pct) ? ` + ${num(emp.allowance_pct)}%` : ''}` },
            { key: 'contract', label: t('staff.job.contract'), children: emp.contract_number ? `${emp.contract_number}${emp.contract_date ? ` / ${d(emp.contract_date)}` : ''}` : '—' },
            { key: 'term', label: t('staff.job.dateTo'), children: emp.date_to ? d(emp.date_to) : t('staff.job.indefinite') },
            { key: 'probation', label: t('staff.job.probation'), children: emp.probation_until ? d(emp.probation_until) : '—' },
            ...(emp.status === 'ended' ? [{ key: 'end', label: t('staff.job.ended'), children: `${d(emp.end_date)} · ${emp.termination_reason_name} ${emp.end_order}` }] : []),
            ...(emp.suspension_reason ? [{ key: 'susp', label: t('staff.job.suspensionReason'), children: emp.suspension_reason }] : []),
          ]} />
          {(emp.warnings ?? []).map((w) => <Alert key={w} type="warning" showIcon message={w} style={{ marginTop: 8 }} />)}
          {hasPerm('worktime.view') && emp.status !== 'ended' && emp.kind !== 'contractor' && <JobScheduleBox employment={emp.id} canEdit={hasPerm('worktime.edit')} />}
          <Table<HistoryRow> size="small" rowKey="id" pagination={false} dataSource={emp.history} style={{ marginTop: 8 }}
            columns={[
              { title: t('staff.job.from'), dataIndex: 'date', width: 110, render: d },
              { title: t('staff.job.event'), dataIndex: 'event_label', width: 140 },
              { title: t('org.subdivision'), dataIndex: 'subdivision_name' },
              { title: t('org.sl.position'), dataIndex: 'occupation_name' },
              { title: t('staff.rate'), dataIndex: 'rate', width: 70, align: 'right', render: fmtRate },
              { title: t('org.sl.salary'), dataIndex: 'base_salary', width: 110, align: 'right', render: num },
              { title: t('staff.job.order'), dataIndex: 'order', width: 160 },
              { title: t('org.notes'), dataIndex: 'note', width: 180 },
            ]} />
        </Card>
      ))}

      <Modal open={!!mode} width={720} onOk={submit} onCancel={() => setMode(null)} title={mode ? t(`staff.job.titles.${mode}`) : ''}>
        <Form form={form} layout="vertical">
          {mode === 'edit' && <>
            <Alert showIcon type="warning" style={{ marginBottom: 12 }} title={t('staff.job.editHint')} />
            <Form.Item name="correction" valuePropName="checked"><Checkbox>{t('staff.job.correction')}</Checkbox></Form.Item>
          </>}
          {(mode === 'hire' || mode === 'edit') && <FormLayout formKey="employment">
            <Row gutter={12}>
              <Col xs={24} md={8}><Form.Item name="kind" label={t('staff.kind')} rules={[{ required: true }]}>
                <Select options={EMPLOYMENT_KINDS.map((k) => ({ value: k, label: t(`staff.kinds.${k}`) }))} /></Form.Item></Col>
              <Col xs={24} md={16}><Form.Item name="subdivision" label={t('org.subdivision')} rules={[{ required: true }]}>
                <SubdivisionSelect allowClear={false} /></Form.Item></Col>
              <Col xs={24}><Form.Item name="occupation" label={t('org.sl.position')} rules={[{ required: true }]}>
                <RefSelect spec="occupation" allowClear={false} /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="rate" label={t('staff.rate')} rules={[{ required: true }]} {...rateProps}><RateInput /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="base_salary" label={t('org.sl.salary')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="allowance_pct" label={t('org.sl.allowance')}><InputNumber min={0} max={500} style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="combination_pct" label={t('staff.combinationPct')} tooltip={t('staff.combinationHint')}><InputNumber min={0} max={100} suffix="%" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={8}><Form.Item name="date_from" label={t('staff.hiredOn')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={8}><Form.Item name="date_to" label={t('staff.job.dateTo')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={8}><Form.Item name="probation_until" label={t('staff.job.probation')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={8}><Form.Item name="contract_number" label={t('staff.job.contractNo')}><Input /></Form.Item></Col>
              <Col xs={12} md={8}><Form.Item name="contract_date" label={t('staff.job.contractDate')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={24} md={8}><Form.Item name="hire_order" label={t('staff.job.hireOrder')}><Input placeholder="45-p din 01.09.2015" /></Form.Item></Col>
              <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
            </Row>
          </FormLayout>}
          {mode === 'change' && <>
            <Typography.Paragraph type="secondary">{t('staff.job.changeHint')}</Typography.Paragraph>
            <FormLayout formKey="employment-change"><Row gutter={12}>
              <Col xs={12} md={8}><Form.Item name="date" label={t('staff.job.from')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={16}><Form.Item name="order" label={t('staff.job.order')}><Input placeholder="88-p din 28.04.2023" /></Form.Item></Col>
              <Col xs={24}><Form.Item name="subdivision" label={t('org.subdivision')}><SubdivisionSelect allowClear={false} /></Form.Item></Col>
              <Col xs={24}><Form.Item name="occupation" label={t('org.sl.position')}><RefSelect spec="occupation" allowClear={false} /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="rate" label={t('staff.rate')} {...rateProps}><RateInput /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="base_salary" label={t('org.sl.salary')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="allowance_pct" label={t('org.sl.allowance')}><InputNumber min={0} max={500} style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12} md={6}><Form.Item name="combination_pct" label={t('staff.combinationPct')} tooltip={t('staff.combinationHint')}><InputNumber min={0} max={100} suffix="%" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
            </Row></FormLayout>
          </>}
          {(mode === 'suspend' || mode === 'resume' || mode === 'terminate') && (
            <Row gutter={12}>
              <Col xs={12}><Form.Item name="date" label={mode === 'terminate' ? t('staff.job.endDate') : t('staff.job.from')} rules={[{ required: true }]}>
                <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
              <Col xs={12}><Form.Item name="order" label={t('staff.job.order')}><Input /></Form.Item></Col>
              {mode === 'suspend' && <Col xs={24}><Form.Item name="reason" label={t('staff.job.suspensionReason')} rules={[{ required: true }]}>
                <Input placeholder={t('staff.job.suspensionPlaceholder')} /></Form.Item></Col>}
              {mode === 'terminate' && <>
                <Col xs={24}><Form.Item name="reason" label={t('staff.job.reason')} rules={[{ required: true }]}><RefSelect spec={{ dict: 'termination' }} /></Form.Item></Col>
                <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
                <Col xs={24}><Alert showIcon type="warning" title={t('staff.job.terminateHint')} /></Col>
              </>}
            </Row>
          )}
        </Form>
      </Modal>
    </Space>
  )
}

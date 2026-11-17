import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Form, InputNumber, Modal, Select, Space, Tag, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { SCHEDULE_STATUS_COLOR, type LeaveSchedule } from '../../api/leave'
import { useApp } from '../../auth/AppContext'
import SubdivisionSelect from '../../components/SubdivisionSelect'

/** Anul pentru care se lucrează la grafic: din octombrie — anul următor. */
export const planningYear = () => (dayjs().month() >= 9 ? dayjs().year() + 1 : dayjs().year())

/** Graficele anuale ale concediilor, pe subdiviziuni. */
export default function SchedulesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [year, setYear] = useState(planningYear())
  const { data, loading } = useFetch<Paged<LeaveSchedule>>('/leave/schedules/', { year, page_size: 500 })
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()
  const rows = data?.results ?? []

  const create = async () => {
    const v = await form.validateFields()
    try {
      const r = await api.post<LeaveSchedule>('/leave/schedules/', v)
      setCreating(false)
      navigate(`/leave/schedule/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <Card title={t('menu.leaveSchedule')} extra={hasPerm('leave.create') && <Button type="primary" icon={<PlusOutlined />}
      onClick={() => { form.resetFields(); form.setFieldsValue({ year }); setCreating(true) }}>{t('lv.sch.new')}</Button>}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select style={{ width: 110 }} value={year} onChange={setYear}
          options={Array.from({ length: 5 }, (_, i) => dayjs().year() + 1 - i).map((y) => ({ value: y, label: y }))} />
      </Space>
      {!loading && rows.length === 0 && <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('lv.sch.emptyHint')} />}
      <Table<LeaveSchedule> rowKey="id" size="small" loading={loading} dataSource={rows} pagination={false} rowTone={(r) => ROW_TONE.leaveSchedule(r.status)}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/leave/schedule/${r.id}`) })}
        columns={[
          { title: t('org.subdivision'), dataIndex: 'subdivision_name', render: (v: string, r) => <a onClick={() => navigate(`/leave/schedule/${r.id}`)}>{v}</a> },
          { title: t('lv.sch.year'), dataIndex: 'year', width: 80 },
          { title: t('ord.status'), dataIndex: 'status', width: 200, render: (v: string, r) => <Tag color={SCHEDULE_STATUS_COLOR[v]}>{r.status_label}</Tag> },
          { title: t('lv.sch.people'), key: 'n', width: 140, align: 'right', render: (_: unknown, r) => `${r.planned_count} / ${r.lines_count}` },
          { title: t('lv.sch.approvedBy'), dataIndex: 'approved_by' },
        ]} />

      <Modal open={creating} title={t('lv.sch.new')} onOk={create} onCancel={() => setCreating(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="year" label={t('lv.sch.year')} rules={[{ required: true }]}><InputNumber min={2000} max={2100} /></Form.Item>
          <Form.Item name="subdivision" label={t('org.subdivision')} rules={[{ required: true }]} extra={t('lv.sch.newHint')}>
            <SubdivisionSelect allowClear={false} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

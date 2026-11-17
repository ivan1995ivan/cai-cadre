import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, DatePicker, Form, InputNumber, Modal, Popconfirm, Select, Space, Typography, message } from 'antd'
import { ClockCircleOutlined, DeleteOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { JobSchedule, WorkSchedule } from '../../api/worktime'

/** Graficul de lucru al unui raport de muncă (cu istoric „din data”): în fișa angajatului, la fiecare raport. */
export default function JobScheduleBox({ employment, canEdit }: { employment: number; canEdit: boolean }) {
  const { t } = useTranslation()
  const { data, reload } = useFetch<JobSchedule[]>('/worktime/job-schedules/', { employment })
  const { data: schedules } = useFetch<WorkSchedule[]>('/worktime/schedules/', { active: 1 })
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()
  const rows = data ?? []
  const current = rows[0]
  const kind = Form.useWatch('schedule', form)
  const isCycle = (schedules ?? []).find((s) => s.id === kind)?.kind === 'cycle'

  const save = async () => {
    const v = await form.validateFields()
    try {
      await api.post('/worktime/job-schedules/', { ...v, employment, date_from: v.date_from.format('YYYY-MM-DD') })
      setOpen(false)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const remove = async (id: number) => {
    try {
      await api.delete(`/worktime/job-schedules/${id}/`)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <Space wrap size={6} style={{ marginTop: 6 }}>
      <ClockCircleOutlined />
      <Typography.Text type="secondary">{t('wt.job.schedule')}:</Typography.Text>
      {current ? <Typography.Text>{current.schedule_name} <Typography.Text type="secondary">({t('wt.job.from', { date: dayjs(current.date_from).format('DD.MM.YYYY') })}
        {current.cycle_offset ? `, ${t('wt.job.offset', { days: current.cycle_offset })}` : ''})</Typography.Text></Typography.Text>
        : <Typography.Text type="secondary">{t('wt.job.none')}</Typography.Text>}
      {canEdit && <Button size="small" type="link" onClick={() => { form.resetFields(); form.setFieldsValue({ date_from: dayjs().startOf('month'), cycle_offset: 0 }); setOpen(true) }}>{t('wt.job.change')}</Button>}
      {canEdit && current && <Popconfirm title={t('common.confirmDelete')} onConfirm={() => remove(current.id)}>
        <Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>}
      <Modal open={open} title={t('wt.job.change')} onOk={save} onCancel={() => setOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="schedule" label={t('wt.job.schedule')} rules={[{ required: true }]}>
            <Select options={(schedules ?? []).map((s) => ({ value: s.id, label: `${s.name} (${s.weekly_hours} h)` }))} />
          </Form.Item>
          <Form.Item name="date_from" label={t('staff.job.from')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" /></Form.Item>
          {isCycle && <Form.Item name="cycle_offset" label={t('wt.job.offsetLabel')} extra={t('wt.job.offsetHint')}><InputNumber min={0} max={60} /></Form.Item>}
          <Typography.Text type="secondary">{t('wt.job.hint')}</Typography.Text>
        </Form>
      </Modal>
    </Space>
  )
}

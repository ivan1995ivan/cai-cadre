import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Form, Input, Modal, Select, Space, Tag, Typography, message } from 'antd'
import dayjs from 'dayjs'

import AppTable from '../../components/AppTable'
import { ROW_TONE } from '../../components/rowTone'
import { api, errorText, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'

interface Row {
  id: number
  employee: number
  employee_name: string
  tab_number: string
  kind: string
  kind_label: string
  text: string
  copies: number
  status: string
  status_label: string
  answer: string
  handled_by_name: string
  created_at: string
}
const COLOR: Record<string, string> = { new: 'blue', in_work: 'orange', done: 'green', rejected: 'red', withdrawn: 'default' }

/** Cererile angajaților din cabinet (adeverințe, modificarea datelor): cadrele le iau în lucru și răspund. */
export default function RequestsInbox() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [status, setStatus] = useState('open')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Row | null>(null)
  const [form] = Form.useForm()
  const { data, loading, reload } = useFetch<Paged<Row>>('/portal/requests/', { status, page, page_size: 50 })
  const save = async (next: string) => {
    try {
      await api.patch(`/portal/requests/${editing!.id}/`, { status: next, answer: form.getFieldValue('answer') ?? '' })
      message.success(t('common.saved'))
      setEditing(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <Card title={t('menu.employeeRequests')}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select style={{ width: 200 }} value={status} onChange={(v) => { setStatus(v); setPage(1) }}
          options={[{ value: 'open', label: t('pt.inbox.open') }, { value: '', label: t('pt.inbox.all') },
            ...['done', 'rejected', 'withdrawn'].map((s) => ({ value: s, label: t(`pt.st.${s}`) }))]} />
        <Typography.Text type="secondary">{t('pt.inbox.hint')}</Typography.Text>
      </Space>
      <AppTable<Row> rowKey="id" size="small" loading={loading} dataSource={data?.results ?? []} exportName={t('menu.employeeRequests')}
        rowTone={(r) => ROW_TONE.employeeRequest(r.status)}
        pagination={{ current: page, pageSize: 50, total: data?.count ?? 0, onChange: setPage, showSizeChanger: false }}
        onRow={(r) => ({ onDoubleClick: () => { setEditing(r); form.setFieldsValue({ answer: r.answer }) } })}
        columns={[
          { title: t('ord.date'), dataIndex: 'created_at', width: 110, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('staff.fullName'), dataIndex: 'employee_name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}`)}>{v}</a> },
          { title: t('lv.kind'), dataIndex: 'kind_label' },
          { title: t('pt.text'), dataIndex: 'text' },
          { title: t('pt.copies'), dataIndex: 'copies', width: 90 },
          { title: t('pt.status'), dataIndex: 'status', width: 120, render: (v: string, r) => <Tag color={COLOR[v]}>{r.status_label}</Tag> },
          { title: t('pt.answer'), dataIndex: 'answer' },
          { title: '', key: 'x', width: 110, render: (_: unknown, r) => hasPerm('employees.edit') && ['new', 'in_work'].includes(r.status) &&
            <Button size="small" type="primary" onClick={() => { setEditing(r); form.setFieldsValue({ answer: r.answer }) }}>{t('pt.inbox.handle')}</Button> },
        ]} />
      <Modal open={!!editing} title={editing ? `${editing.employee_name} — ${editing.kind_label}` : ''} onCancel={() => setEditing(null)}
        footer={<Space>
          <Button onClick={() => save('in_work')}>{t('pt.inbox.inWork')}</Button>
          <Button danger onClick={() => save('rejected')}>{t('pt.inbox.reject')}</Button>
          <Button type="primary" onClick={() => save('done')}>{t('pt.inbox.done')}</Button>
        </Space>}>
        {editing && <>
          <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>{editing.text || '—'}</Typography.Paragraph>
          {editing.kind.startsWith('certificate') && <Typography.Paragraph type="secondary">{t('pt.inbox.printHint')}</Typography.Paragraph>}
          <Form form={form} layout="vertical">
            <Form.Item name="answer" label={t('pt.answer')}><Input placeholder={t('pt.inbox.answerHint')} /></Form.Item>
          </Form>
          <Button type="link" style={{ paddingLeft: 0 }} onClick={() => navigate(`/employees/${editing.employee}`)}>{t('pt.inbox.openCard')}</Button>
        </>}
      </Modal>
    </Card>
  )
}

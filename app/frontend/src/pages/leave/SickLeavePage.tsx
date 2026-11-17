import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import {
  Button, Card, Checkbox, Col, DatePicker, Form, Input, Modal, Row, Select, Space, Tag, Tooltip, Typography, message,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import Table from '../../components/AppTable'
import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { SICK_KINDS, type SickLeave } from '../../api/leave'
import { useApp } from '../../auth/AppContext'
import { d } from './LeavePage'
import EmployeeSelect from '../../components/EmployeeSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'
import MarkButton from '../../components/MarkButton'

const DATE_FIELDS = ['issued_on', 'date_from', 'date_to', 'return_date']

/** Formularul certificatului de concediu medical (nou sau existent). */
export function SickLeaveModal({ open, record, employee, onClose, onSaved }: {
  open: boolean
  record: SickLeave | null
  employee?: number
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const who = (Form.useWatch('employee', form) as number | undefined) ?? employee ?? record?.employee
  const { data: previous } = useFetch<Paged<SickLeave>>(open && who ? '/leave/sick-leaves/' : null, { employee: who, page_size: 20 })

  const afterOpen = (visible: boolean) => {
    if (!visible) return
    form.resetFields()
    if (record) {
      form.setFieldsValue({ ...record, ...Object.fromEntries(DATE_FIELDS.map((k) => [k, record[k as keyof SickLeave] ? dayjs(String(record[k as keyof SickLeave])) : null])) })
    } else {
      form.setFieldsValue({ kind: 'illness', employee })
    }
  }

  const save = async () => {
    const v = await form.validateFields()
    const body: Record<string, unknown> = { ...v, employee: employee ?? v.employee }
    for (const k of DATE_FIELDS) body[k] = v[k] ? (v[k] as Dayjs).format('YYYY-MM-DD') : null
    try {
      const r = record ? await api.patch<SickLeave>(`/leave/sick-leaves/${record.id}/`, body) : await api.post<SickLeave>('/leave/sick-leaves/', body)
      for (const w of r.data.warnings ?? []) message.warning(w, 8)
      message.success(t('common.saved'))
      onSaved()
      onClose()
    } catch (e) {
      form.setFields(fieldErrors(e))
      message.error(errorText(e))
    }
  }

  const from = Form.useWatch('date_from', form) as Dayjs | undefined
  const to = Form.useWatch('date_to', form) as Dayjs | undefined
  const days = from && to ? to.diff(from, 'day') + 1 : null

  return (
    <Modal open={open} title={record ? t('lv.sick.edit') : t('lv.sick.new')} onOk={save} onCancel={onClose} width={720}
      afterOpenChange={afterOpen} destroyOnHidden>
      <Form form={form} layout="vertical">
        <FormLayout formKey="sick-leave"><Row gutter={12}>
          {!employee && !record && <Col xs={24}><Form.Item name="employee" label={t('ord.employeeOne')} rules={[{ required: true }]}>
            <EmployeeSelect />
          </Form.Item></Col>}
          <Col xs={8} md={4}><Form.Item name="series" label={t('lv.sick.series')}><Input /></Form.Item></Col>
          <Col xs={16} md={8}><Form.Item name="number" label={t('lv.sick.number')} rules={[{ required: true }]}><Input /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="issued_on" label={t('lv.sick.issuedOn')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="kind" label={t('lv.sick.kind')} rules={[{ required: true }]}>
            <Select popupMatchSelectWidth={false} options={SICK_KINDS.map((k) => ({ value: k, label: t(`lv.sick.kinds.${k}`) }))} /></Form.Item></Col>
          <Col xs={24}><Form.Item name="issued_by" label={t('lv.sick.issuedBy')}><Input /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="date_from" label={t('lv.sick.from')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="date_to" label={t('lv.sick.to')} rules={[{ required: true }]}
            extra={days ? t('lv.sick.days', { count: days }) : undefined}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="return_date" label={t('lv.sick.returnDate')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="continuation_of" label={t('lv.sick.continuation')}>
            <Select allowClear popupMatchSelectWidth={false} options={(previous?.results ?? []).filter((x) => x.id !== record?.id)
              .map((x) => ({ value: x.id, label: `${x.series} ${x.number} (${d(x.date_from)} – ${d(x.date_to)})` }))} /></Form.Item></Col>
          <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
        </Row></FormLayout>
        <Typography.Text type="secondary">{t('lv.sick.hint')}</Typography.Text>
      </Form>
    </Modal>
  )
}

/** Registrul certificatelor de concediu medical. */
export default function SickLeavePage({ employee }: { employee?: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>(employee ? { employee } : {
    date_from: dayjs().startOf('month').subtract(1, 'month').format('YYYY-MM-DD') })
  const [page, setPage] = useState(1)
  const { data, loading, reload } = useFetch<Paged<SickLeave>>('/leave/sick-leaves/', { ...filters, page, page_size: 50 })
  const [editing, setEditing] = useState<SickLeave | null | undefined>(undefined)
  const set = (k: string, v: string | number | undefined) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1) }
  const canEdit = hasPerm('sick_leave.edit')

  const table = (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        {!employee && <Input.Search allowClear placeholder={t('lv.sick.searchHint')} style={{ width: 240 }} onSearch={(v) => set('q', v || undefined)} />}
        {!employee && <SubdivisionSelect style={{ width: 300 }} placeholder={t('org.subdivision')} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />}
        {!employee && <DatePicker.RangePicker format="DD.MM.YYYY" defaultValue={[dayjs(filters.date_from as string), null]} allowEmpty={[true, true]}
          onChange={(v) => { set('date_from', v?.[0]?.format('YYYY-MM-DD')); set('date_to', v?.[1]?.format('YYYY-MM-DD')) }} />}
        <Select allowClear style={{ width: 220 }} placeholder={t('lv.sick.kind')} onChange={(v) => set('kind', v)}
          options={SICK_KINDS.map((k) => ({ value: k, label: t(`lv.sick.kinds.${k}`) }))} />
        <Checkbox onChange={(e) => set('open', e.target.checked ? 1 : undefined)}>{t('lv.sick.openOnly')}</Checkbox>
        {hasPerm('sick_leave.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing(null)}>{t('lv.sick.new')}</Button>}
      </Space>
      <Table<SickLeave> rowKey="id" size="small" loading={loading} dataSource={data?.results ?? []} exportName={t('menu.sickLeave')}
        // certificatul deschis (încă nu s-a prezentat la lucru și nu-l continuă altul) — în lucru
        rowTone={(r) => (r.return_date || r.continued_by ? undefined : 'work')}
        onRow={(r) => ({ onDoubleClick: () => canEdit && !r.deletion_mark && setEditing(r) })}
        pagination={{ current: page, pageSize: 50, total: data?.count ?? 0, onChange: setPage, showTotal: (n) => t('common.total', { count: n }) }}
        columns={[
          { title: t('lv.sick.certificate'), key: 'no', width: 140, render: (_: unknown, r) => canEdit
            ? <a onClick={() => setEditing(r)}>{`${r.series} ${r.number}`.trim()}</a> : `${r.series} ${r.number}`.trim() },
          ...(employee ? [] : [
            { title: t('staff.fullName'), dataIndex: 'employee_name', render: (v: string, r: SickLeave) => <a onClick={() => navigate(`/employees/${r.employee}?tab=leave`)}>{v}</a> },
            { title: t('org.subdivision'), dataIndex: 'subdivision', width: 180 },
          ]),
          { title: t('lv.sick.kind'), dataIndex: 'kind_label', width: 220 },
          { title: t('lv.period'), key: 'p', width: 190, render: (_: unknown, r) => `${d(r.date_from)} – ${d(r.date_to)}` },
          { title: t('ord.p.days'), dataIndex: 'days', width: 60, align: 'right' },
          { title: t('lv.sick.returnDate'), dataIndex: 'return_date', width: 120, render: (v: string | null, r: SickLeave) => v ? d(v)
            : r.continued_by ? <Tooltip title={r.continued_by}><Tag>{t('lv.sick.continued')}</Tag></Tooltip>
              : <Tag color="orange">{t('lv.sick.open')}</Tag> },
          { title: t('lv.sick.continuation'), dataIndex: 'continuation_label', width: 150 },
          { title: t('lv.sick.issuedBy'), dataIndex: 'issued_by' },
          ...(hasPerm('sick_leave.delete') ? [{ title: '', key: 'del', width: 40, render: (_: unknown, r: SickLeave) => (
            <MarkButton endpoint="/leave/sick-leaves/" row={r} onDone={reload} />) }] : []),
        ]} />
      <SickLeaveModal open={editing !== undefined} record={editing ?? null} employee={employee} onClose={() => setEditing(undefined)} onSaved={reload} />
    </>
  )
  return employee ? table : <Card title={t('menu.sickLeave')}>{table}</Card>
}

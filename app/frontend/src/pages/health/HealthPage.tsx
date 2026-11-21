import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Button, Card, Checkbox, Col, DatePicker, Form, Input, InputNumber, Modal, Row, Select, Space, Tabs, Tag, Typography, message } from 'antd'
import { FileDoneOutlined, PlusOutlined, PrinterOutlined, SettingOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import AppTable from '../../components/AppTable'
import CrudTable from '../../components/CrudTable'
import PrintDialog from '../../components/PrintDialog'
import { api, errorText, fieldErrors, type Paged } from '../../api/client'
import { useFetch } from '../../api/hooks'
import RefSelect, { type RefSpec } from '../../components/RefSelect'
import { useApp } from '../../auth/AppContext'
import { d } from '../leave/LeavePage'
import EmployeeSelect from '../../components/EmployeeSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'
import MarkButton, { type Markable } from '../../components/MarkButton'

interface DueRow { employee: number; name: string; subdivision: string; what: string; label: string; last: string | null; due: string | null;
  status: string; detail: string }
type Row = Record<string, unknown> & { id: number; employee: number; employee_name: string }
interface Field { key: string; type?: 'date' | 'select' | 'number' | 'bool'; options?: { value: string | number; label: string }[]; ref?: RefSpec; required?: boolean; span?: number }
interface Kind { endpoint: string; fields: Field[]; columns: { key: string; type?: 'date' | 'tag' }[] }

const EXAM_KINDS = ['preliminary', 'periodic', 'extraordinary', 'return']
const CONCLUSIONS = ['fit', 'restricted', 'temporary', 'unfit']
const BRIEFING_KINDS = ['introductory', 'initial', 'periodic', 'unplanned', 'targeted']
const STATUS_COLOR: Record<string, string> = { overdue: 'red', missing: 'orange', due: 'blue' }
const CONCLUSION_COLOR: Record<string, string> = { fit: 'green', restricted: 'orange', temporary: 'orange', unfit: 'red' }

function useKinds(): Record<'exams' | 'briefings', Kind> {
  const { t } = useTranslation()
  const opts = (list: string[], prefix: string) => list.map((k) => ({ value: k, label: t(`hl.${prefix}.${k}`) }))
  return {
    exams: { endpoint: '/health/exams/', fields: [
      { key: 'kind', type: 'select', options: opts(EXAM_KINDS, 'examKinds'), required: true, span: 8 },
      { key: 'date', type: 'date', required: true, span: 8 }, { key: 'next_date', type: 'date', span: 8 },
      { key: 'institution', span: 12 }, { key: 'conclusion', type: 'select', options: opts(CONCLUSIONS, 'conclusions'), required: true, span: 12 },
      { key: 'restrictions', span: 24 }, { key: 'document', span: 12 }, { key: 'note', span: 12 },
    ], columns: [{ key: 'date', type: 'date' }, { key: 'kind_label' }, { key: 'institution' }, { key: 'conclusion', type: 'tag' },
      { key: 'restrictions' }, { key: 'next_date', type: 'date' }] },
    briefings: { endpoint: '/health/briefings/', fields: [
      { key: 'kind', type: 'select', options: opts(BRIEFING_KINDS, 'briefingKinds'), required: true, span: 12 },
      { key: 'date', type: 'date', required: true, span: 6 }, { key: 'next_date', type: 'date', span: 6 },
      { key: 'instructor', span: 12 }, { key: 'topic', span: 12 }, { key: 'note', span: 24 },
    ], columns: [{ key: 'date', type: 'date' }, { key: 'kind_label' }, { key: 'topic' }, { key: 'instructor' }, { key: 'next_date', type: 'date' }] },
  }
}

/** Sănătatea și securitatea în muncă: termenele (examen, instructaj), registrele lor și periodicitatea examenului pe funcții. */
export default function HealthPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'due'
  const kinds = useKinds()
  return (
    <Card title={t('menu.health')}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden items={[
        { key: 'due', label: t('hl.tabs.due'), children: <Due /> },
        { key: 'exams', label: t('hl.tabs.exams'), children: <HealthRecords kind={kinds.exams} /> },
        { key: 'briefings', label: t('hl.tabs.briefings'), children: <HealthRecords kind={kinds.briefings} /> },
        { key: 'rules', label: t('hl.tabs.rules'), children: <ExamRules /> },
      ]} />
    </Card>
  )
}

function Due() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({})
  const [picked, setPicked] = useState<number[]>([])
  const [printOpen, setPrintOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { data, loading, reload } = useFetch<{ rows: DueRow[]; counts: Record<string, number> }>('/health/due/', filters)
  const set = (k: string, v: string | number | undefined) => setFilters({ ...filters, [k]: v })
  const rows = (data?.rows ?? []).map((r, i) => ({ ...r, id: i }))
  const order = async () => {
    try {
      const people = [...new Set(rows.filter((r) => picked.includes(r.id)).map((r) => r.employee))]
      const r = await api.post('/health/due/', { employees: people })
      navigate(`/orders/${r.data.order}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select allowClear style={{ width: 200 }} placeholder={t('hl.allWhat')} onChange={(v) => set('what', v)}
          options={['exam', 'briefing'].map((k) => ({ value: k, label: t(`hl.what.${k}`) }))} />
        <SubdivisionSelect style={{ width: 280 }} placeholder={t('org.subdivision')} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />
        <InputNumber min={0} max={180} placeholder="30" prefix={t('hl.horizon')} style={{ width: 170 }} onChange={(v) => set('horizon', v ?? undefined)} />
        <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('hl.printList')}</Button>
        {hasPerm('orders.create') && <Button icon={<FileDoneOutlined />} disabled={!picked.length} onClick={order}>{t('hl.examOrder', { count: picked.length })}</Button>}
        {hasPerm('settings.edit') && <Button icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)}>{t('hl.settings')}</Button>}
      </Space>
      <Typography.Paragraph type="secondary">{t('hl.dueHint', { overdue: data?.counts.overdue ?? 0, missing: data?.counts.missing ?? 0, due: data?.counts.due ?? 0 })}</Typography.Paragraph>
      <AppTable rowKey="id" size="small" loading={loading} dataSource={rows} exportName={t('hl.tabs.due')} pagination={{ pageSize: 100 }}
        rowSelection={{ selectedRowKeys: picked, onChange: (k) => setPicked(k as number[]) }}
        columns={[
          { title: t('staff.fullName'), dataIndex: 'name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}?tab=health`)}>{v}</a> },
          { title: t('org.subdivision'), dataIndex: 'subdivision' },
          { title: t('hl.whatCol'), dataIndex: 'what', render: (v: string) => t(`hl.what.${v}`) },
          { title: t('hl.last'), dataIndex: 'last', width: 110, render: d },
          { title: t('hl.due'), dataIndex: 'due', width: 110, render: d },
          { title: '', dataIndex: 'status', width: 120, render: (v: string) => <Tag color={STATUS_COLOR[v]}>{t(`hl.status.${v}`)}</Tag> },
          { title: t('org.notes'), dataIndex: 'detail' },
        ]} />
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="report" url="/health/due/"
        params={{ ...filters, export: 'print' }} optionKeys={[]} title={t('hl.printList')} />
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} onSaved={reload} />
    </>
  )
}

function SettingsModal({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const { data } = useFetch<Record<string, number>>(open ? '/health/settings/' : null)
  useEffect(() => { if (data) form.setFieldsValue(data) }, [data, form])
  const save = async () => {
    try {
      await api.put('/health/settings/', await form.validateFields())
      onSaved()
      onClose()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <Modal open={open} title={t('hl.settings')} onCancel={onClose} onOk={save} destroyOnHidden>
      <Form form={form} layout="vertical">
        <Form.Item name="exam_months" label={t('hl.examMonths')} extra={t('hl.examMonthsHint')}><InputNumber min={1} max={60} /></Form.Item>
        <Form.Item name="briefing_months" label={t('hl.briefingMonths')}><InputNumber min={1} max={24} /></Form.Item>
        <Form.Item name="horizon_days" label={t('hl.horizonDays')}><InputNumber min={0} max={180} /></Form.Item>
      </Form>
    </Modal>
  )
}

/** Periodicitatea examenului medical periodic pe funcție / subdiviziune (din evaluarea riscurilor, HG 1025/2016). */
function ExamRules() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  return (
    <>
      <Typography.Paragraph type="secondary">{t('hl.rulesHint')}</Typography.Paragraph>
      <CrudTable endpoint="/health/exam-rules/" canEdit={hasPerm('health.edit')}
        fields={[
          { key: 'occupation', label: t('hl.rule.occupation'), ref: 'occupation', render: (_v, r) => String(r.occupation_name || '—') },
          { key: 'subdivision', label: t('hl.rule.subdivision'), render: (_v, r) => String(r.subdivision_name || '—'),
            input: () => <SubdivisionSelect /> },
          { key: 'months', label: t('hl.rule.months'), type: 'number', required: true, width: 120, extra: t('hl.rule.monthsHint'),
            render: (v) => Number(v) ? String(v) : t('hl.rule.none') },
          { key: 'note', label: t('hl.rule.note') },
        ]} />
    </>
  )
}

/** Registrul examenelor / instructajelor (în pagină sau în fișa unui angajat). */
export function HealthRecords({ kind, employee }: { kind: Kind; employee?: number }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [q, setQ] = useState<string>()
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Row | null | undefined>()
  const params = employee ? { employee } : { q, page, page_size: 50 }
  const { data, loading, reload } = useFetch<Paged<Row> | Row[]>(kind.endpoint, params)
  const rows = Array.isArray(data) ? data : data?.results ?? []
  const label = (k: string) => t(`hl.f.${k}`)
  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        {hasPerm('health.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing(null)}>{t('common.add')}</Button>}
        {!employee && <Input.Search allowClear placeholder={t('lv.sick.searchHint')} style={{ width: 240 }} onSearch={(v) => { setQ(v || undefined); setPage(1) }} />}
      </Space>
      <AppTable<Row> rowKey="id" size="small" loading={loading} dataSource={rows}
        pagination={employee ? false : { current: page, pageSize: 50, total: (data as Paged<Row>)?.count ?? 0, onChange: setPage, showSizeChanger: false }}
        onRow={(r) => ({ onDoubleClick: () => hasPerm('health.edit') && !r.deletion_mark && setEditing(r) })}
        columns={[
          ...(employee ? [] : [{ title: t('staff.fullName'), dataIndex: 'employee_name',
            render: (v: string, r: Row) => <a onClick={() => navigate(`/employees/${r.employee}?tab=health`)}>{v}</a> }]),
          ...kind.columns.map((c) => ({ title: label(c.key), dataIndex: c.key,
            render: (v: unknown, r: Row) => c.type === 'date' ? d(v as string) : c.type === 'tag'
              ? <Tag color={CONCLUSION_COLOR[String(v)]}>{String(r.conclusion_label ?? v)}</Tag> : String(v ?? '') })),
          { title: '', key: 'x', width: 90, render: (_: unknown, r: Row) => <Space size={0}>
            {hasPerm('health.edit') && !r.deletion_mark && <Button size="small" type="link" onClick={() => setEditing(r)}>{t('common.edit')}</Button>}
            {hasPerm('health.delete') && <MarkButton endpoint={kind.endpoint} row={r as Markable} onDone={reload} />}
          </Space> },
        ]} />
      <RecordModal kind={kind} record={editing} employee={employee} onClose={() => setEditing(undefined)} onSaved={reload} />
    </>
  )
}

function RecordModal({ kind, record, employee, onClose, onSaved }: {
  kind: Kind
  record: Row | null | undefined
  employee?: number
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const afterOpen = (v: boolean) => {
    if (!v) return
    form.resetFields()
    if (record) {
      form.setFieldsValue(Object.fromEntries(kind.fields.map((f) => [f.key,
        f.type === 'date' ? (record[f.key] ? dayjs(String(record[f.key])) : null) : record[f.key]])))
    }
  }
  const save = async () => {
    const v = await form.validateFields()
    const body: Record<string, unknown> = { ...v }
    for (const f of kind.fields) if (f.type === 'date') body[f.key] = v[f.key] ? (v[f.key] as Dayjs).format('YYYY-MM-DD') : null
    body.employee = employee ?? v.employee ?? record?.employee
    try {
      if (record) await api.patch(`${kind.endpoint}${record.id}/`, body)
      else await api.post(kind.endpoint, body)
      message.success(t('common.saved'))
      onSaved()
      onClose()
    } catch (e) {
      form.setFields(fieldErrors(e))
      message.error(errorText(e))
    }
  }
  return (
    <Modal open={record !== undefined} title={record ? String(record.employee_name) : t('common.add')} onCancel={onClose} onOk={save}
      afterOpenChange={afterOpen} destroyOnHidden width={680}>
      <Form form={form} layout="vertical">
        <FormLayout formKey={`health:${kind.endpoint}`}><Row gutter={12}>
          {!employee && !record && <Col xs={24}><Form.Item name="employee" label={t('ord.employeeOne')} rules={[{ required: true }]}>
            <EmployeeSelect />
          </Form.Item></Col>}
          {kind.fields.map((f) => (
            <Col key={f.key} xs={24} md={f.span ?? 12}>
              <Form.Item name={f.key} label={f.type === 'bool' ? ' ' : t(`hl.f.${f.key}`)} valuePropName={f.type === 'bool' ? 'checked' : 'value'}
                rules={f.required ? [{ required: true }] : []} extra={f.key === 'next_date' ? t('hl.nextHint') : undefined}>
                {f.ref ? <RefSelect spec={f.ref} allowClear={!f.required} /> : f.type === 'date' ? <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
                  : f.type === 'select' ? <Select options={f.options} showSearch optionFilterProp="label" />
                    : f.type === 'number' ? <InputNumber min={1} max={10} style={{ width: '100%' }} />
                      : f.type === 'bool' ? <Checkbox>{t(`hl.f.${f.key}`)}</Checkbox> : <Input />}
              </Form.Item>
            </Col>
          ))}
        </Row></FormLayout>
      </Form>
    </Modal>
  )
}

/** Fila „Sănătate” din fișa angajatului. */
export function EmployeeHealth({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const kinds = useKinds()
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={24}>
      {(['exams', 'briefings'] as const).map((k) => (
        <div key={k}>
          <Typography.Title level={5} style={{ marginTop: 0 }}>{t(`hl.tabs.${k}`)}</Typography.Title>
          <HealthRecords kind={kinds[k]} employee={employee} />
        </div>
      ))}
    </Space>
  )
}

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Alert, Avatar, Button, Card, Col, DatePicker, Divider, Dropdown, Form, Input, InputNumber, Popconfirm, Row, Select, Space, Spin,
  Statistic, Switch, Table, Tabs, Tag, Typography, Upload, message,
} from 'antd'
import {
  ArrowLeftOutlined, CameraOutlined, FileProtectOutlined, InboxOutlined, PrinterOutlined, SaveOutlined, UserOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import RefSelect from '../../components/RefSelect'
import { EmployeeTraining } from '../training/TrainingPage'
import { EmployeeHealth } from '../health/HealthPage'
import { PortalAccessButton } from '../portal/PortalAccess'
import HistoryButton from '../../components/HistoryButton'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import PrintDialog from '../../components/PrintDialog'
import { api, errorText, fieldErrors } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { Specialty } from '../../api/org'
import { useDict, type AccessEntry, type Employee } from '../../api/staff'
import { useApp, useLocalName } from '../../auth/AppContext'
import EmploymentsTab from './EmploymentsTab'
import LeaveTab from './LeaveTab'
import PayTab from './PayTab'
import OrdersTab from './OrdersTab'
import { STATUS_COLOR } from './EmployeesList'
import FormLayout from '../../components/FormLayout'
import { useEditGuard } from '../../components/UnsavedGuard'

const DATE_FIELDS = ['birth_date']
const PRINT_DOCS = [
  { key: 'employee_card', options: ['show_photo', 'show_family', 'show_military', 'show_salary'] },
  { key: 'certificate_work', options: ['show_idnp', 'show_salary'] },
  { key: 'certificate_seniority', options: ['show_periods'] },
  { key: 'certificate_salary', options: ['show_idnp'], perm: 'payroll.view' },
]
/** Perioada adeverinței privind salariul: ultimele N luni încheiate sau un interval de luni ales. */
const SALARY_MONTHS = [3, 6, 12]

/** Fișa angajatului (fișa personală MR-2 electronică), pe file. */
export default function EmployeeCard() {
  const { t } = useTranslation()
  const { id } = useParams()
  const isNew = id === 'new'
  const navigate = useNavigate()
  const { hasPerm, me, branding } = useApp()
  const military = branding?.military_enabled === true  // modulul opțional „Evidența militară” (Constante → Module)
  const [emp, setEmp] = useState<Employee | null>(null)
  const [search] = useSearchParams()
  const [tab, setTab] = useState(search.get('tab') || 'personal')
  const [form] = Form.useForm()
  const [printDoc, setPrintDoc] = useState<string | null>(null)
  const [purpose, setPurpose] = useState('')
  const [salaryMonths, setSalaryMonths] = useState<number | 'range'>(6)
  const [salaryRange, setSalaryRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([dayjs().subtract(6, 'month'), dayjs().subtract(1, 'month')])
  const canEdit = hasPerm(isNew ? 'employees.create' : 'employees.edit')
  const { touch, clean } = useEditGuard(() => save(), canEdit)
  const sensitive = hasPerm('employees.sensitive')

  const load = async () => {
    if (isNew) {
      const r = await api.get<{ tab_number: string }>('/staff/employees/next-number/')
      form.setFieldsValue({ tab_number: r.data.tab_number, citizenship: 'Republica Moldova' })
      return
    }
    try {
      const r = await api.get<Employee>(`/staff/employees/${id}/`)
      setEmp(r.data)
      form.setFieldsValue({ ...r.data, ...Object.fromEntries(DATE_FIELDS.map((f) => [f, r.data[f as keyof Employee] ? dayjs(String(r.data[f as keyof Employee])) : null])) })
    } catch (e) {
      message.error(errorText(e))
    }
  }
  useEffect(() => { load() }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    const v = await form.validateFields()
    const body = { ...v, ...Object.fromEntries(DATE_FIELDS.map((f) => [f, v[f] ? v[f].format('YYYY-MM-DD') : null])) }
    try {
      if (isNew) {
        const r = await api.post<Employee>('/staff/employees/', body)
        message.success(t('common.saved'))
        clean()
        navigate(`/employees/${r.data.id}`, { replace: true })
      } else {
        const r = await api.patch<Employee>(`/staff/employees/${id}/`, body)
        setEmp((old) => ({ ...r.data, seniority: old?.seniority ?? null }))
        message.success(t('common.saved'))
        clean()
      }
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
      return false
    }
  }

  const uploadPhoto = async (file: File) => {
    const data = new FormData()
    data.append('photo', file)
    try {
      const r = await api.patch<Employee>(`/staff/employees/${id}/`, data)
      setEmp((old) => old && { ...old, photo: r.data.photo })
    } catch (e) {
      message.error(errorText(e))
    }
    return false
  }

  const archive = async (archived: boolean) => {
    try {
      const r = await api.post<Employee>(`/staff/employees/${id}/archive/`, { archived })
      setEmp(r.data)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  if (!isNew && !emp) return <Spin />

  const personal = (
    <Form form={form} layout="vertical" disabled={!canEdit} onValuesChange={touch}>
      <FormLayout formKey="employee"><Row gutter={12}>
        <Col xs={12} md={4}><Form.Item name="tab_number" label={t('staff.tab')}><Input /></Form.Item></Col>
        <Col xs={24} md={7}><Form.Item name="last_name" label={t('staff.lastName')} rules={[{ required: true }]}><Input /></Form.Item></Col>
        <Col xs={24} md={7}><Form.Item name="first_name" label={t('staff.firstName')} rules={[{ required: true }]}><Input /></Form.Item></Col>
        <Col xs={24} md={6}><Form.Item name="patronymic" label={t('staff.patronymic')}><Input /></Form.Item></Col>
        {sensitive && <Col xs={24} md={6}><Form.Item name="idnp" label="IDNP" rules={[{ pattern: /^\d{13}$/, message: t('staff.idnpHint') }]}><Input maxLength={13} /></Form.Item></Col>}
        <Col xs={12} md={5}><Form.Item name="birth_date" label={t('staff.birthDate')}><DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
        <Col xs={12} md={4}><Form.Item name="sex" label={t('staff.sex')}><Select allowClear options={[{ value: 'M', label: t('staff.male') }, { value: 'F', label: t('staff.female') }]} /></Form.Item></Col>
        {sensitive && <Col xs={24} md={9}><Form.Item name="birth_place" label={t('staff.birthPlace')}><Input /></Form.Item></Col>}
        <Col xs={24} md={8}><Form.Item name="previous_names" label={t('staff.previousNames')}><Input /></Form.Item></Col>
        <Col xs={24} md={6}><Form.Item name="citizenship" label={t('staff.citizenship')}><Input /></Form.Item></Col>
        <Col xs={12} md={5}><Form.Item name="nationality" label={t('staff.nationality')}><RefSelect spec={{ dict: 'nationality' }} /></Form.Item></Col>
        <Col xs={12} md={5}><Form.Item name="marital_status" label={t('staff.marital')}><RefSelect spec={{ dict: 'marital' }} /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="phone" label={t('staff.phone')}><Input /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="phone2" label={t('staff.phone2')}><Input /></Form.Item></Col>
        <Col xs={24} md={6}><Form.Item name="email" label="E-mail" rules={[{ type: 'email' }]}><Input /></Form.Item></Col>
        <Col xs={24} md={6}><Form.Item name="emergency_contact" label={t('staff.emergency')}><Input /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="address" label={t('staff.address')}><Input /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="address_actual" label={t('staff.addressActual')}><Input /></Form.Item></Col>
        {sensitive && <>
          <Col xs={12} md={6}><Form.Item name="cnam_code" label={t('staff.cnam')}><Input /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="cpas" label="CPAS"><Input /></Form.Item></Col>
          <Col xs={12} md={6}><Form.Item name="disability" label={t('staff.disability')}><Input /></Form.Item></Col>
        </>}
        <Col xs={12} md={6}><Form.Item name="iban" label="IBAN"><Input maxLength={34} /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="bank_name" label={t('staff.bank')}><Input /></Form.Item></Col>
        <Col xs={24}><Form.Item name="notes" label={t('org.notes')}><Input.TextArea rows={2} /></Form.Item></Col>
        <Divider titlePlacement="start" style={{ margin: '4px 0 8px' }}>{t('staff.workwear')}</Divider>
        <Col xs={8} md={4}><Form.Item name="clothing_size" label={t('staff.clothingSize')} tooltip={t('staff.clothingHint')}><Input placeholder="48" /></Form.Item></Col>
        <Col xs={8} md={4}><Form.Item name="shoe_size" label={t('staff.shoeSize')}><Input placeholder="39" /></Form.Item></Col>
        <Col xs={8} md={4}><Form.Item name="height" label={t('staff.height')}><InputNumber min={50} max={250} style={{ width: '100%' }} placeholder="170" /></Form.Item></Col>
      </Row></FormLayout>
    </Form>
  )

  if (isNew) {
    return (
      <Card title={<Space><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/employees')} />{t('staff.new')}</Space>}
        extra={<Button type="primary" icon={<SaveOutlined />} onClick={save}>{t('common.save')}</Button>}>
        <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('staff.newHint')} />
        {personal}
      </Card>
    )
  }

  const e = emp!
  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      <Card>
        <Row gutter={16} align="middle" wrap={false}>
          <Col flex="none">
            <Upload accept=".jpg,.jpeg,.png,.webp" showUploadList={false} disabled={!canEdit} beforeUpload={uploadPhoto}>
              <Avatar size={88} src={e.photo || undefined} icon={!e.photo && <UserOutlined />} style={{ cursor: canEdit ? 'pointer' : 'default' }} />
              {canEdit && <div style={{ textAlign: 'center', fontSize: 12 }}><CameraOutlined /> {t('staff.photo')}</div>}
            </Upload>
          </Col>
          <Col flex="auto">
            <Space wrap>
              <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/employees')} />
              <Typography.Title level={4} style={{ margin: 0 }}>{e.full_name}</Typography.Title>
              <Tag>{t('staff.tab')} {e.tab_number}</Tag>
              <Tag color={STATUS_COLOR[e.status]}>{t(`staff.statuses.${e.status}`)}</Tag>
              {e.is_archived && <Tag>{t('staff.archived')}</Tag>}
            </Space>
            {e.seniority && (
              <Typography.Paragraph type="secondary" style={{ margin: '6px 0 0 40px' }}>
                {t('staff.sen.total')}: <b>{e.seniority.total.text}</b> · {t('staff.sen.institution')}: {e.seniority.institution.text}
              </Typography.Paragraph>
            )}
          </Col>
          <Col flex="none">
            <Space wrap>
              <Dropdown menu={{ items: PRINT_DOCS.filter((d) => !d.perm || hasPerm(d.perm))
                .map((d) => ({ key: d.key, label: t(`staff.print.${d.key}`), icon: <FileProtectOutlined /> })),
                onClick: ({ key }) => { setPurpose(''); setPrintDoc(key) } }}>
                <Button icon={<PrinterOutlined />}>{t('org.sl.print')}</Button>
              </Dropdown>
              {sensitive && <HistoryButton model="staff.Employee" id={e.id} onRestored={load} />}
              {hasPerm('users.create') && <PortalAccessButton employee={e.id} />}
              {canEdit && e.status === 'dismissed' && (
                <Popconfirm title={e.is_archived ? t('staff.unarchiveConfirm') : t('staff.archiveConfirm')} onConfirm={() => archive(!e.is_archived)}>
                  <Button icon={<InboxOutlined />}>{e.is_archived ? t('staff.unarchive') : t('staff.archive')}</Button>
                </Popconfirm>)}
              {/* se marchează doar dosarul fără raporturi de muncă (candidatul, dosarul greșit); ceilalți se arhivează */}
              {hasPerm('employees.delete') && e.status === 'candidate' && !e.deletion_mark && <MarkButton endpoint="/staff/employees/" row={e} onDone={load} text />}
              {canEdit && tab === 'personal' && !e.deletion_mark && <Button type="primary" icon={<SaveOutlined />} onClick={save}>{t('common.save')}</Button>}
            </Space>
          </Col>
        </Row>
        <MarkedBanner endpoint="/staff/employees/" row={e} onDone={load} canUnmark={hasPerm('employees.delete')} />
      </Card>

      <Card>
        <Tabs activeKey={tab} onChange={setTab} destroyOnHidden={false} items={[
          { key: 'personal', label: t('staff.tabs.personal'), children: personal, forceRender: true },
          { key: 'jobs', label: t('staff.tabs.jobs'), children: <EmploymentsTab employee={e} onChanged={load} /> },
          ...(hasPerm('orders.view') || hasPerm('employees.view') ? [{ key: 'orders', label: t('staff.tabs.orders'), children: <OrdersTab employee={e.id} /> }] : []),
          ...(hasPerm('leave.view') || hasPerm('sick_leave.view') ? [{ key: 'leave', label: t('staff.tabs.leave'), children: <LeaveTab employee={e.id} /> }] : []),
          ...(hasPerm('payroll.view') ? [{ key: 'pay', label: t('staff.tabs.pay'), children: <PayTab employee={e.id} /> }] : []),
          ...(sensitive ? [{ key: 'documents', label: t('staff.tabs.documents'), children: <DocumentsTab employee={e.id} /> }] : []),
          ...(me?.is_admin || hasPerm('employees.view') ? [{ key: 'family', label: t('staff.tabs.family'), children: <FamilyTab employee={e.id} /> }] : []),
          { key: 'education', label: t('staff.tabs.education'), children: <EducationTab employee={e.id} /> },
          { key: 'seniority', label: t('staff.tabs.seniority'), children: <SeniorityTab employee={e} onChanged={load} /> },
          ...(hasPerm('health.view') ? [{ key: 'health', label: t('staff.tabs.health'), children: <EmployeeHealth employee={e.id} /> }] : []),
          ...(military && (hasPerm('military.view') || me?.is_admin) ? [{ key: 'military', label: t('staff.tabs.military'), children: <MilitaryTab employee={e.id} /> }] : []),
          { key: 'checklist', label: t('staff.tabs.checklist'), children: <ChecklistTab employee={e} onSaved={(x) => setEmp(x)} /> },
          ...(sensitive || hasPerm('audit.view') ? [{ key: 'access', label: t('staff.tabs.access'), children: <AccessTab employee={e.id} /> }] : []),
        ]} />
      </Card>

      {printDoc && (
        <PrintDialog open onClose={() => setPrintDoc(null)} docType={printDoc} url={`/staff/employees/${e.id}/print/`}
          params={{ doc: printDoc, purpose, ...(printDoc !== 'certificate_salary' ? {} : salaryMonths === 'range'
            ? { from: salaryRange[0].format('YYYY-MM'), to: salaryRange[1].format('YYYY-MM') } : { months: salaryMonths }) }}
          title={t(`staff.print.${printDoc}`)}
          optionKeys={(PRINT_DOCS.find((d) => d.key === printDoc)?.options ?? []).filter((o) => military || o !== 'show_military')} />
      )}
      {printDoc && printDoc !== 'employee_card' && (
        <div style={{ position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 1100 }}>
          <Space wrap style={{ justifyContent: 'center' }}>
            {printDoc === 'certificate_salary' && <>
              <Select value={salaryMonths} onChange={setSalaryMonths} style={{ width: 190 }} aria-label={t('staff.salaryPeriod')}
                options={[...SALARY_MONTHS.map((n) => ({ value: n, label: t('staff.salaryLastMonths', { count: n }) })),
                  { value: 'range' as const, label: t('staff.salaryRange') }]} />
              {salaryMonths === 'range' && <DatePicker.RangePicker picker="month" format="MM.YYYY" allowClear={false} value={salaryRange}
                onChange={(v) => { if (v?.[0] && v[1]) setSalaryRange([v[0], v[1]]) }} />}
            </>}
            <Input addonBefore={t('staff.purpose')} value={purpose} onChange={(ev) => setPurpose(ev.target.value)} style={{ width: 460 }}
              placeholder={t(printDoc === 'certificate_salary' ? 'staff.purposeBankHint' : 'staff.purposeHint')} />
          </Space>
        </div>
      )}
    </Space>
  )
}

/* ---------------- filele cu tabele (acte, familie, studii...) ---------------- */

/** Câmpurile filei + angajatul (câmp tehnic, ascuns: se trimite la adăugare). */
function childFields(fields: CrudField[]): CrudField[] {
  return [{ key: 'employee', label: '', hidden: true }, ...fields]
}

const fmtDate = (v: unknown) => (v ? dayjs(String(v)).format('DD.MM.YYYY') : '')

function DocumentsTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const types = useDict('document')
  const today = dayjs().format('YYYY-MM-DD')
  return (
    <CrudTable endpoint="/staff/documents/" params={{ employee }} defaults={{ employee }} canEdit={hasPerm('employees.edit')}
      fields={childFields([
        { key: 'doc_type', label: t('staff.doc.type'), type: 'select', options: types, ref: { dict: 'document' }, width: 260,
          render: (_v, r) => String(r.doc_type_name ?? '') },
        { key: 'title', label: t('staff.doc.title'), inTable: false },
        { key: 'series', label: t('staff.doc.series'), width: 80 },
        { key: 'number', label: t('staff.doc.number'), width: 130 },
        { key: 'issued_by', label: t('staff.doc.issuedBy') },
        { key: 'issue_date', label: t('staff.doc.issueDate'), type: 'date', width: 110 },
        { key: 'expiry_date', label: t('staff.doc.expiry'), type: 'date', width: 130,
          render: (v) => v ? <Tag color={String(v) < today ? 'red' : dayjs(String(v)).diff(dayjs(), 'day') < 90 ? 'orange' : undefined}>{fmtDate(v)}</Tag> : '' },
        { key: 'is_identity', label: t('staff.doc.identity'), type: 'bool', width: 90 },
        { key: 'note', label: t('org.notes'), inTable: false },
      ])}
      rowActions={(r) => <ScanButton id={Number(r.id)} file={r.file as string | null} />} />
  )
}

function ScanButton({ id, file }: { id: number; file: string | null }) {
  const { t } = useTranslation()
  const [current, setCurrent] = useState(file)
  const upload = async (f: File) => {
    const data = new FormData()
    data.append('file', f)
    try {
      const r = await api.patch<{ file: string }>(`/staff/documents/${id}/`, data)
      setCurrent(r.data.file)
    } catch (e) {
      message.error(errorText(e))
    }
    return false
  }
  return (
    <Space size={4}>
      {current && <a href={current} target="_blank" rel="noreferrer">{t('staff.doc.open')}</a>}
      <Upload showUploadList={false} beforeUpload={upload}><Button size="small">{current ? t('staff.doc.replace') : t('staff.doc.scan')}</Button></Upload>
    </Space>
  )
}

function FamilyTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const relations = useDict('family')
  return (
    <CrudTable endpoint="/staff/family/" params={{ employee }} defaults={{ employee }} canEdit={hasPerm('employees.edit')}
      fields={childFields([
        { key: 'relation', label: t('staff.fam.relation'), type: 'select', options: relations, ref: { dict: 'family' }, width: 160,
          render: (_v, r) => String(r.relation_name ?? '') },
        { key: 'full_name', label: t('staff.fullName'), required: true },
        { key: 'birth_date', label: t('staff.birthDate'), type: 'date', width: 120 },
        { key: 'idnp', label: 'IDNP', width: 150 },
        { key: 'dependent', label: t('staff.fam.dependent'), type: 'bool', width: 110 },
        { key: 'disabled', label: t('staff.fam.disabled'), type: 'bool', width: 110 },
        { key: 'note', label: t('org.notes'), inTable: false },
      ])} />
  )
}

function EducationTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const localName = useLocalName()
  const levels = useDict('education')
  const forms = useDict('education_form')
  const { data: specs } = useFetch<Specialty[]>('/org/specialties/', { active: 1 })
  const specOptions = (specs ?? []).map((s) => ({ value: s.id, label: localName(s) }))
  const canEdit = hasPerm('employees.edit')
  return (
    <Space direction="vertical" style={{ width: '100%' }} size={24}>
      <CrudTable endpoint="/staff/education/" params={{ employee }} defaults={{ employee }} canEdit={canEdit}
        title={<Typography.Text strong>{t('staff.edu.title')}</Typography.Text>}
        fields={childFields([
          { key: 'level', label: t('staff.edu.level'), type: 'select', options: levels, ref: { dict: 'education' }, width: 170, render: (_v, r) => String(r.level_name ?? '') },
          { key: 'institution', label: t('staff.edu.institution'), required: true },
          { key: 'specialty', label: t('staff.edu.specialty'), type: 'select', options: specOptions, ref: 'specialty', width: 220,
            render: (_v, r) => String(r.specialty_name ?? '') },
          { key: 'specialty_text', label: t('staff.edu.specialtyText'), inTable: false },
          { key: 'qualification', label: t('staff.edu.qualification'), inTable: false },
          { key: 'form', label: t('staff.edu.form'), type: 'select', options: forms, ref: { dict: 'education_form' }, inTable: false },
          { key: 'year_from', label: t('staff.edu.yearFrom'), type: 'number', inTable: false },
          { key: 'year_to', label: t('staff.edu.yearTo'), type: 'number', width: 90 },
          { key: 'diploma_series', label: t('staff.edu.diplomaSeries'), inTable: false },
          { key: 'diploma_number', label: t('staff.edu.diplomaNumber'), width: 130 },
          { key: 'diploma_date', label: t('staff.edu.diplomaDate'), type: 'date', inTable: false },
        ])} />
      {hasPerm('training.view') && <EmployeeTraining employee={employee} />}
    </Space>
  )
}

function SeniorityTab({ employee, onChanged }: { employee: Employee; onChanged: () => void }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const s = employee.seniority
  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      {s && (
        <Row gutter={16}>
          {(['total', 'specialty', 'institution'] as const).map((k) => (
            <Col xs={12} md={8} key={k}><Statistic title={t(`staff.sen.${k}`)} value={s[k].text} /></Col>
          ))}
        </Row>
      )}
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>{t('staff.sen.hint')}</Typography.Paragraph>
      <CrudTable endpoint="/staff/experience/" params={{ employee: employee.id }} defaults={{ employee: employee.id, in_specialty: true }}
        canEdit={hasPerm('employees.edit')} title={<Typography.Text strong>{t('staff.sen.prior')}</Typography.Text>}
        extra={<Button size="small" onClick={onChanged}>{t('staff.sen.recalc')}</Button>}
        fields={childFields([
          { key: 'organization', label: t('staff.sen.organization'), required: true },
          { key: 'position', label: t('org.sl.position'), width: 220 },
          { key: 'date_from', label: t('staff.sen.from'), type: 'date', required: true, width: 110 },
          { key: 'date_to', label: t('staff.sen.to'), type: 'date', required: true, width: 110 },
          { key: 'in_specialty', label: t('staff.sen.inSpecialty'), type: 'bool', width: 110 },
          { key: 'document', label: t('staff.sen.document'), inTable: false },
        ])} />
    </Space>
  )
}

interface Military { id?: number; employee: number; status: string; category: string; group: number | null; composition: string
  rank: number | null; specialty_code: string; center: number | null; fit: boolean; special_record: boolean; book: string; note: string }

function MilitaryTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const [form] = Form.useForm()
  const [record, setRecord] = useState<Military | null>(null)
  const canEdit = hasPerm('employees.edit') || hasPerm('military.edit')
  useEffect(() => {
    api.get<Military[]>('/staff/military/', { params: { employee } }).then((r) => {
      const rec = r.data[0] ?? { employee, status: 'liable', fit: true }
      setRecord(rec as Military)
      form.setFieldsValue(rec)
    })
  }, [employee, form])
  const save = async () => {
    const v = await form.validateFields()
    try {
      const r = record?.id ? await api.patch<Military>(`/staff/military/${record.id}/`, v)
        : await api.post<Military>('/staff/military/', { ...v, employee })
      setRecord(r.data)
      message.success(t('common.saved'))
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }
  const choices = (prefix: string, keys: string[]) => keys.map((k) => ({ value: k, label: t(`${prefix}.${k}`) }))
  return (
    <Form form={form} layout="vertical" disabled={!canEdit}>
      <FormLayout formKey="employee-military"><Row gutter={12}>
        <Col xs={24} md={6}><Form.Item name="status" label={t('staff.mil.status')}><Select options={choices('staff.mil.statuses', ['liable', 'not_liable', 'recruit'])} /></Form.Item></Col>
        <Col xs={12} md={4}><Form.Item name="category" label={t('staff.mil.category')}><Select allowClear options={[{ value: '1', label: '1' }, { value: '2', label: '2' }]} /></Form.Item></Col>
        <Col xs={12} md={7}><Form.Item name="group" label={t('staff.mil.group')}><RefSelect spec={{ dict: 'military_group' }} /></Form.Item></Col>
        <Col xs={24} md={7}><Form.Item name="composition" label={t('staff.mil.composition')}><Select allowClear options={choices('staff.mil.compositions', ['command', 'sergeants', 'soldiers', 'medical'])} /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="rank" label={t('staff.mil.rank')}><RefSelect spec={{ dict: 'military_rank' }} /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="specialty_code" label={t('staff.mil.specialty')}><Input /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="center" label={t('staff.mil.center')} extra={t('staff.mil.centerHint')}><RefSelect spec={{ dict: 'military_center' }} /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="fit" label={t('staff.mil.fit')} valuePropName="checked"><Switch /></Form.Item></Col>
        <Col xs={12} md={6}><Form.Item name="special_record" label={t('staff.mil.special')} valuePropName="checked"><Switch /></Form.Item></Col>
        <Col xs={24} md={12}><Form.Item name="book" label={t('staff.mil.book')}><Input /></Form.Item></Col>
        <Col xs={24}><Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></Col>
      </Row></FormLayout>
      {canEdit && <Button type="primary" icon={<SaveOutlined />} onClick={save}>{t('common.save')}</Button>}
    </Form>
  )
}

function ChecklistTab({ employee, onSaved }: { employee: Employee; onSaved: (e: Employee) => void }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const items = useDict('checklist')
  const [state, setState] = useState(employee.checklist ?? {})
  const canEdit = hasPerm('employees.edit')
  const set = (code: string, part: 'hire' | 'exit', value: string | null) => setState((s) => ({ ...s, [code]: { ...s[code], [part]: value } }))
  const save = async () => {
    try {
      const r = await api.patch<Employee>(`/staff/employees/${employee.id}/`, { checklist: state })
      onSaved({ ...r.data, seniority: employee.seniority })
      message.success(t('common.saved'))
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <>
      <Typography.Paragraph type="secondary">{t('staff.check.hint')}</Typography.Paragraph>
      <Table size="small" rowKey="code" pagination={false} dataSource={items}
        columns={[
          { title: t('staff.check.item'), dataIndex: 'label' },
          { title: t('staff.check.hire'), key: 'hire', width: 180, render: (_: unknown, r) => (
            <DatePicker format="DD.MM.YYYY" disabled={!canEdit} value={state[r.code]?.hire ? dayjs(state[r.code]!.hire!) : null}
              onChange={(d) => set(r.code, 'hire', d ? d.format('YYYY-MM-DD') : null)} />) },
          { title: t('staff.check.exit'), key: 'exit', width: 180, render: (_: unknown, r) => r.extra?.returnable ? (
            <DatePicker format="DD.MM.YYYY" disabled={!canEdit} value={state[r.code]?.exit ? dayjs(state[r.code]!.exit!) : null}
              onChange={(d) => set(r.code, 'exit', d ? d.format('YYYY-MM-DD') : null)} />) : null },
        ]} />
      {canEdit && <Button type="primary" icon={<SaveOutlined />} style={{ marginTop: 12 }} onClick={save}>{t('common.save')}</Button>}
    </>
  )
}

function AccessTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { data, loading } = useFetch<AccessEntry[]>(`/staff/employees/${employee}/access-log/`)
  return (
    <>
      <Typography.Paragraph type="secondary">{t('staff.access.hint')}</Typography.Paragraph>
      <Table<AccessEntry> size="small" rowKey="id" loading={loading} dataSource={data ?? []} pagination={{ pageSize: 20 }}
        columns={[
          { title: t('staff.access.at'), dataIndex: 'at', width: 170, render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm') },
          { title: t('staff.access.user'), dataIndex: 'user_name' },
          { title: t('staff.access.action'), dataIndex: 'action_label', width: 140 },
          { title: t('staff.access.detail'), dataIndex: 'detail', width: 200 },
        ]} />
    </>
  )
}

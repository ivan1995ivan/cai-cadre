import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fmtRate } from '../../components/RateInput'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Input, Select, Space, Tag, Tooltip, Typography } from 'antd'
import {
  CalendarOutlined, CarOutlined, ClockCircleOutlined, ExclamationCircleOutlined, FieldTimeOutlined, MedicineBoxOutlined, PlusOutlined,
  PrinterOutlined, UploadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import EmployeePeek from '../../components/EmployeePeek'
import PrintDialog from '../../components/PrintDialog'
import { useFetch } from '../../api/hooks'
import type { Paged } from '../../api/client'
import type { Subdivision } from '../../api/org'
import { EMPLOYMENT_KINDS, useDict, type EmployeeRow } from '../../api/staff'
import { useApp } from '../../auth/AppContext'
import { useEnumOptions } from '../org/DictionariesPage'
import { BulkAccessButton } from '../portal/PortalAccess'
import SubdivisionSelect from '../../components/SubdivisionSelect'

export const STATUS_COLOR: Record<string, string> = { active: 'green', suspended: 'orange', dismissed: 'default', candidate: 'blue' }

interface TreeNode { value: number; title: string; children?: TreeNode[] }
export function subTree(nodes: Subdivision[]): TreeNode[] {
  return nodes.map((n) => ({ value: n.id, title: n.name_ro, children: n.children ? subTree(n.children) : undefined }))
}

/** Lista angajaților: căutare (nume, IDNP, nr. de tabel), filtre pe subdiviziune / categorie / tip, export și tipar. */
export default function EmployeesList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const opts = useEnumOptions()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({ status: 'current' })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [printOpen, setPrintOpen] = useState(false)
  const params = { ...filters, page, page_size: pageSize }
  const { data, loading } = useFetch<Paged<EmployeeRow>>('/staff/employees/', params)
  const staffCategories = useDict('staff_category')
  const set = (k: string, v: string | number | undefined) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1) }

  return (
    <Card title={t('menu.employees')} extra={<Space wrap>
      <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('staff.printList')}</Button>
      {hasPerm('imports.create') && <Button icon={<UploadOutlined />} onClick={() => navigate('/admin/import')}>{t('excel.import')}</Button>}
      {hasPerm('users.create') && <BulkAccessButton />}
      {hasPerm('employees.create') && <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/employees/new')}>{t('staff.new')}</Button>}
    </Space>}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search allowClear placeholder={t('staff.searchHint')} style={{ width: 280 }} onSearch={(v) => set('q', v || undefined)} />
        <Select style={{ width: 170 }} value={filters.status} onChange={(v) => set('status', v)} options={[
          'current', 'active', 'suspended', 'dismissed', 'archived', 'all'].map((s) => ({ value: s, label: t(`staff.statusFilter.${s}`) }))} />
        <SubdivisionSelect style={{ width: 300 }} placeholder={t('org.subdivision')}
          value={filters.subdivision as number | undefined} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />
        <Select allowClear style={{ width: 230 }} placeholder={t('org.category')} value={filters.category as string | undefined}
          onChange={(v) => set('category', v)}
          options={[...staffCategories.map((c) => ({ value: String(c.value), label: c.label })), { value: 'none', label: t('org.noCategory') }]} />
        <Select allowClear style={{ width: 190 }} placeholder={t('staff.kind')} value={filters.kind as string | undefined}
          onChange={(v) => set('kind', v)} options={opts('staff.kinds', EMPLOYMENT_KINDS)} />
      </Space>
      <Table<EmployeeRow> rowKey="id" size="small" loading={loading} dataSource={data?.results ?? []} exportName={t('menu.employees')}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/employees/${r.id}`) })}
        pagination={{ current: page, pageSize, total: data?.count ?? 0, showSizeChanger: true, showTotal: (n) => t('common.total', { count: n }),
          onChange: (p, s) => { setPage(p); setPageSize(s) } }}
        columns={[
          { title: '', key: 'flags', width: 70, render: (_: unknown, r) => <Flags row={r} /> },
          { title: t('staff.tab'), dataIndex: 'tab_number', width: 80 },
          { title: t('staff.fullName'), dataIndex: 'full_name', render: (v: string, r) => (
            <Space size={4}><EmployeePeek id={r.id}><a onClick={() => navigate(`/employees/${r.id}`)}>{v}</a></EmployeePeek>
              {r.jobs > 1 && <Tag color="blue">{t('staff.jobsCount', { count: r.jobs })}</Tag>}</Space>) },
          { title: t('org.subdivision'), dataIndex: 'subdivision', width: 230 },
          { title: t('org.sl.position'), dataIndex: 'occupation', width: 230 },
          { title: t('staff.kind'), dataIndex: 'kind', width: 130, render: (v: string) => v ? t(`staff.kinds.${v}`) : '' },
          { title: t('staff.rate'), dataIndex: 'rate', width: 70, align: 'right', render: fmtRate },
          { title: t('staff.hiredOn'), dataIndex: 'date_from', width: 110, render: (v: string | null) => v ? dayjs(v).format('DD.MM.YYYY') : '' },
          { title: 'IDNP', dataIndex: 'idnp', width: 140, defaultHidden: true } as never,
          { title: t('staff.birthDate'), dataIndex: 'birth_date', width: 110, defaultHidden: true, render: (v: string | null) => v ? dayjs(v).format('DD.MM.YYYY') : '' } as never,
          { title: t('staff.phone'), dataIndex: 'phone', width: 130, defaultHidden: true } as never,
          { title: t('staff.status'), dataIndex: 'status', width: 120,
            render: (v: string, r) => <Tag color={STATUS_COLOR[v]}>{r.is_archived ? t('staff.archived') : t(`staff.statuses.${v}`)}</Tag> },
        ]} />
      {!loading && (data?.count ?? 0) === 0 && !filters.q && (
        <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>{t('staff.emptyHint')}</Typography.Paragraph>)}
      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="employee_list" url="/staff/employees/print-list/"
        params={filters} optionKeys={['group_by_subdivision', 'show_rate', 'show_idnp', 'show_phone']} title={t('staff.printList')} />
    </Card>
  )
}

/** Semnele rândului: absent azi (concediu, boală, deplasare…), în probă, contractul pe termen care expiră, lipsește IDNP / IBAN. */
function Flags({ row }: { row: EmployeeRow }) {
  const { t } = useTranslation()
  const f = row.flags
  if (!f) return null
  const d = (v: string) => dayjs(v).format('DD.MM.YYYY')
  const absentIcon = f.absent && (f.absent.kind === 'sick' ? <MedicineBoxOutlined style={{ color: '#cf1322' }} />
    : f.absent.kind === 'travel' ? <CarOutlined style={{ color: '#1677ff' }} /> : <CalendarOutlined style={{ color: '#d46b08' }} />)
  return (
    <Space size={4}>
      {f.absent && <Tooltip title={t('staff.flags.absent', { what: f.absent.label, to: d(f.absent.to) })}>{absentIcon}</Tooltip>}
      {f.probation && <Tooltip title={t('staff.flags.probation', { to: d(f.probation) })}><FieldTimeOutlined style={{ color: '#d4b106' }} /></Tooltip>}
      {f.contract_ends && <Tooltip title={t('staff.flags.contractEnds', { to: d(f.contract_ends) })}>
        <ClockCircleOutlined style={{ color: '#d4380d' }} /></Tooltip>}
      {f.missing && <Tooltip title={t('staff.flags.missing', { what: f.missing.map((m) => m.toUpperCase()).join(', ') })}>
        <ExclamationCircleOutlined style={{ color: '#cf1322' }} /></Tooltip>}
    </Space>
  )
}

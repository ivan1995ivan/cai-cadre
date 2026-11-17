import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { fmtRate } from '../../components/RateInput'
import { useNavigate } from 'react-router-dom'
import { Card, Input, Select, Space, Tag } from 'antd'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { useFetch } from '../../api/hooks'
import { EMPLOYMENT_KINDS, type Employment } from '../../api/staff'
import { useEnumOptions } from '../org/DictionariesPage'
import SubdivisionSelect from '../../components/SubdivisionSelect'

const d = (v: string | null) => (v ? dayjs(v).format('DD.MM.YYYY') : '')

/** Registrul contractelor individuale de muncă: toate raporturile, cu termenele care expiră evidențiate. */
export default function ContractsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const opts = useEnumOptions()
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({ all: '1', status: 'current' })
  const { data, loading } = useFetch<Employment[]>('/staff/employments/', filters)
  const set = (k: string, v: string | number | undefined) => setFilters((f) => ({ ...f, [k]: v }))
  const soon = dayjs().add(30, 'day')

  const termTag = (v: string | null) => {
    if (!v) return ''
    const day = dayjs(v)
    const color = day.isBefore(dayjs(), 'day') ? 'red' : day.isBefore(soon) ? 'orange' : undefined
    return color ? <Tag color={color}>{d(v)}</Tag> : d(v)
  }

  return (
    <Card title={t('menu.contracts')}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input.Search allowClear placeholder={t('staff.contractSearch')} style={{ width: 260 }} onSearch={(v) => set('q', v || undefined)} />
        <Select style={{ width: 170 }} value={filters.status} onChange={(v) => set('status', v)}
          options={['current', 'active', 'suspended', 'ended', 'all'].map((s) => ({ value: s, label: t(`staff.contractStatus.${s}`) }))} />
        <Select allowClear style={{ width: 190 }} placeholder={t('staff.kind')} value={filters.kind as string | undefined}
          onChange={(v) => set('kind', v)} options={opts('staff.kinds', EMPLOYMENT_KINDS)} />
        <SubdivisionSelect style={{ width: 300 }} placeholder={t('org.subdivision')}
          value={filters.subdivision as number | undefined} onChange={(v) => set('subdivision', typeof v === 'number' ? v : undefined)} />
        <Select allowClear style={{ width: 260 }} placeholder={t('staff.expiringFilter')} value={filters.expiring as string | undefined}
          onChange={(v) => set('expiring', v)} options={[30, 60, 90].map((n) => ({ value: String(n), label: t('staff.expiringIn', { days: n }) }))} />
      </Space>
      <Table<Employment> rowKey="id" size="small" loading={loading} dataSource={data ?? []} exportName={t('menu.contracts')}
        pagination={{ pageSize: 50, showTotal: (n) => t('common.total', { count: n }) }}
        onRow={(r) => ({ onDoubleClick: () => navigate(`/employees/${r.employee}`) })}
        columns={[
          { title: t('staff.tab'), dataIndex: 'employee_tab', width: 80 },
          { title: t('staff.fullName'), dataIndex: 'employee_name', render: (v: string, r) => <a onClick={() => navigate(`/employees/${r.employee}`)}>{v}</a> },
          { title: t('staff.kind'), dataIndex: 'kind_label', width: 140 },
          { title: t('org.subdivision'), dataIndex: 'subdivision_name', width: 220 },
          { title: t('org.sl.position'), dataIndex: 'occupation_name', width: 220 },
          { title: t('staff.rate'), dataIndex: 'rate', width: 70, align: 'right', render: fmtRate },
          { title: t('staff.job.contractNo'), dataIndex: 'contract_number', width: 90 },
          { title: t('staff.job.contractDate'), dataIndex: 'contract_date', width: 110, render: d },
          { title: t('staff.hiredOn'), dataIndex: 'date_from', width: 110, render: d },
          { title: t('staff.job.dateTo'), dataIndex: 'date_to', width: 120, render: termTag },
          { title: t('staff.job.probation'), dataIndex: 'probation_until', width: 120, render: termTag },
          { title: t('staff.status'), dataIndex: 'status_label', width: 110 },
        ]} />
    </Card>
  )
}

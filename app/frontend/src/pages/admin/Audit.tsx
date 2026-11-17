import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, DatePicker, Input, Select, Space, Tag, Typography } from 'antd'
import Table from '../../components/AppTable'
import dayjs, { type Dayjs } from 'dayjs'

import { api, type Paged } from '../../api/client'
import type { AuditEntry } from '../../api/types'

const ACTION_COLOR: Record<string, string> = {
  create: 'green', update: 'blue', delete: 'red', login: 'cyan', login_failed: 'orange', action: 'purple',
}

function renderValue(v: unknown) {
  if (v === null || v === undefined || v === '') return <Typography.Text type="secondary">∅</Typography.Text>
  if (typeof v === 'object') return <Typography.Text code>{JSON.stringify(v)}</Typography.Text>
  return String(v)
}

export default function Audit() {
  const { t } = useTranslation()
  const [data, setData] = useState<Paged<AuditEntry> | null>(null)
  const [models, setModels] = useState<string[]>([])
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<{ action?: string; model?: string; search?: string; range?: [Dayjs, Dayjs] | null }>({})
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get<Paged<AuditEntry>>('/audit-log/', {
        params: {
          page,
          action: filters.action,
          model: filters.model,
          search: filters.search || undefined,
          date_from: filters.range?.[0]?.format('YYYY-MM-DD'),
          date_to: filters.range?.[1]?.format('YYYY-MM-DD'),
        },
      })
      setData(data)
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => {
    load()
  }, [load])
  useEffect(() => {
    api.get<string[]>('/audit-log/models/').then((r) => setModels(r.data))
  }, [])

  const modelName = (m: string) => t(`audit.models.${m.replace('.', '_')}`, { defaultValue: m })

  const update = (patch: typeof filters) => {
    setFilters((f) => ({ ...f, ...patch }))
    setPage(1)
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.audit')}</Typography.Title>
      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <DatePicker.RangePicker format="DD.MM.YYYY" onChange={(r) => update({ range: r as [Dayjs, Dayjs] | null })} />
          <Select allowClear placeholder={t('audit.action')} style={{ width: 180 }} onChange={(v) => update({ action: v })}
            options={Object.keys(ACTION_COLOR).map((a) => ({ value: a, label: t(`audit.actions.${a}`) }))} />
          <Select allowClear placeholder={t('audit.object')} style={{ width: 200 }} onChange={(v) => update({ model: v })}
            options={models.map((m) => ({ value: m, label: modelName(m) }))} />
          <Input.Search allowClear placeholder={t('common.search')} onSearch={(v) => update({ search: v })} style={{ width: 220 }} />
        </Space>
        <Table<AuditEntry>
          rowKey="id"
          size="small"
          loading={loading}
          dataSource={data?.results}
          scroll={{ x: 900 }}
          pagination={{ current: page, total: data?.count, pageSize: 50, onChange: setPage, showSizeChanger: false }}
          expandable={{
            rowExpandable: (r) => Object.keys(r.changes || {}).length > 0,
            expandedRowRender: (r) => (
              <Table
                size="small"
                pagination={false}
                rowKey="field"
                dataSource={Object.entries(r.changes).map(([field, value]) => ({ field, value }))}
                columns={[
                  { title: t('audit.field'), dataIndex: 'field', width: 200 },
                  {
                    title: t('audit.change'), dataIndex: 'value',
                    render: (v) => Array.isArray(v) && v.length === 2
                      ? <Space>{renderValue(v[0])} → {renderValue(v[1])}</Space>
                      : renderValue(v),
                  },
                ]}
              />
            ),
          }}
          columns={[
            { title: t('common.date'), dataIndex: 'timestamp', width: 160, render: (v) => dayjs(v).format('DD.MM.YYYY HH:mm:ss') },
            { title: t('audit.user'), dataIndex: 'username', width: 140, render: (v) => v || <Typography.Text type="secondary">{t('audit.system')}</Typography.Text> },
            { title: t('audit.action'), dataIndex: 'action', width: 150, render: (v) => <Tag color={ACTION_COLOR[v]}>{t(`audit.actions.${v}`)}</Tag> },
            { title: t('audit.object'), dataIndex: 'model', width: 160, render: modelName },
            { title: t('audit.record'), dataIndex: 'object_repr' },
            { title: 'IP', dataIndex: 'ip', width: 130 },
          ]}
        />
      </Card>
    </Space>
  )
}

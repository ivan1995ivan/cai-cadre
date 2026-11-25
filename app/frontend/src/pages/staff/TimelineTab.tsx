import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Segmented, Space, Tag, Typography } from 'antd'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import { useFetch } from '../../api/hooks'

interface TimelineEvent { date: string; kind: string; title: string; detail: string; link: string }

const COLOR: Record<string, string> = {
  job: 'blue', order: 'geekblue', absence: 'orange', sick: 'red', sanction: 'volcano', incentive: 'green', training: 'cyan',
  trip: 'purple', pay: 'gold',
}

/** Fila „Cronologia” din fișa angajatului: tot ce s-a întâmplat cu el, cele mai noi sus, cu legătura spre document. */
export default function TimelineTab({ employee, name }: { employee: number; name: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data, loading } = useFetch<TimelineEvent[]>(`/staff/employees/${employee}/timeline/`)
  const [kind, setKind] = useState('all')
  const rows = (data ?? []).filter((e) => kind === 'all' || e.kind === kind)
  const kinds = Array.from(new Set((data ?? []).map((e) => e.kind)))
  return (
    <Space orientation="vertical" style={{ width: '100%' }}>
      <Space wrap>
        <Segmented value={kind} onChange={(v) => setKind(String(v))}
          options={[{ value: 'all', label: t('staff.timeline.all') }, ...kinds.map((k) => ({ value: k, label: t(`staff.timeline.kinds.${k}`) }))]} />
        <Typography.Text type="secondary">{t('staff.timeline.hint')}</Typography.Text>
      </Space>
      <Table<TimelineEvent> rowKey={(r) => `${r.date}-${r.kind}-${r.title}-${r.detail}`} size="small" loading={loading} dataSource={rows}
        pagination={{ pageSize: 50, hideOnSinglePage: true }} exportName={`${t('staff.timeline.title')} — ${name}`}
        onRow={(r) => ({ onDoubleClick: () => r.link && navigate(r.link) })}
        columns={[
          { title: t('staff.timeline.date'), dataIndex: 'date', width: 110, render: (v: string) => dayjs(v).format('DD.MM.YYYY') },
          { title: t('staff.timeline.kind'), dataIndex: 'kind', width: 150,
            render: (v: string) => <Tag color={COLOR[v]}>{t(`staff.timeline.kinds.${v}`)}</Tag> },
          { title: t('staff.timeline.what'), dataIndex: 'title', render: (v: string, r) => (r.link ? <a onClick={() => navigate(r.link)}>{v}</a> : v) },
          { title: t('staff.timeline.detail'), dataIndex: 'detail', render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
        ]} />
    </Space>
  )
}

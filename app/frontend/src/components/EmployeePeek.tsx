import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Avatar, Descriptions, Popover, Space, Spin, Tag, Typography } from 'antd'
import { UserOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api } from '../api/client'
import { fmtRate } from './RateInput'

export interface EmployeeSummary {
  id: number
  full_name: string
  tab_number: string
  photo: string | null
  sex: string
  birth_date: string | null
  age: number | null
  status: string
  phone: string | null
  email: string | null
  jobs: { kind: string; occupation: string; subdivision: string; rate: number; date_from: string; date_to: string | null; status: string }[]
  seniority: { total: string; healthcare: string; specialty: string; institution: string }
  qualification: { category: string; valid_until: string | null } | null
  clothing_size: string
  shoe_size: string
  height: number | null
  absence: { kind: string; date_from: string; date_to: string } | null
  leave: { available: number; remaining: number } | null
}

// ce s-a adus o dată nu se mai cere la fiecare trecere a mouse-ului (până la reîncărcarea paginii)
const cache = new Map<number, EmployeeSummary>()
const d = (v: string | null | undefined) => (v ? dayjs(v).format('DD.MM.YYYY') : '')

function Card({ id }: { id: number }) {
  const { t } = useTranslation()
  const [data, setData] = useState<EmployeeSummary | null>(cache.get(id) ?? null)
  const [error, setError] = useState(false)
  useEffect(() => {
    if (cache.has(id)) return
    let alive = true
    api.get<EmployeeSummary>(`/staff/employees/${id}/summary/`)
      .then((r) => { cache.set(id, r.data); if (alive) setData(r.data) })
      .catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [id])
  if (error) return <Typography.Text type="secondary">{t('peek.error')}</Typography.Text>
  if (!data) return <div style={{ width: 360, textAlign: 'center', padding: 24 }}><Spin /></div>
  const expiring = data.qualification?.valid_until && dayjs(data.qualification.valid_until).diff(dayjs(), 'day') < 90
  const sizes = [data.clothing_size && `${t('peek.clothing')} ${data.clothing_size}`, data.shoe_size && `${t('peek.shoes')} ${data.shoe_size}`,
    data.height && `${data.height} cm`].filter(Boolean).join(' · ')
  return (
    <div style={{ width: 400, maxWidth: '86vw' }}>
      <Space align="start" size={12} style={{ marginBottom: 8 }}>
        <Avatar shape="square" size={84} src={data.photo || undefined} icon={!data.photo && <UserOutlined />} />
        <div>
          <Typography.Text strong style={{ fontSize: 15 }}>{data.full_name}</Typography.Text>
          <div><Typography.Text type="secondary">{t('staff.tab')} {data.tab_number} · {data.status}</Typography.Text></div>
          {data.birth_date && <div>{d(data.birth_date)}{data.age !== null && <> · <b>{t('peek.age', { count: data.age })}</b></>}</div>}
          {data.absence && <Tag color="orange" style={{ marginTop: 4 }}>{data.absence.kind}: {d(data.absence.date_from)} – {d(data.absence.date_to)}</Tag>}
        </div>
      </Space>
      {data.jobs.map((j, i) => (
        <div key={i} style={{ fontSize: 12, marginBottom: 2 }}>
          <b>{j.occupation}</b>, {j.subdivision} <Typography.Text type="secondary">· {j.kind} · {fmtRate(j.rate)} · {t('peek.since')} {d(j.date_from)}
            {j.date_to ? ` ${t('peek.until')} ${d(j.date_to)}` : ''}</Typography.Text>
        </div>
      ))}
      <Descriptions size="small" column={1} style={{ marginTop: 8 }} styles={{ label: { width: 150, padding: '2px 8px' }, content: { padding: '2px 8px' } }}
        bordered items={[
          { key: 'inst', label: t('peek.institution'), children: data.seniority.institution },
          { key: 'total', label: t('peek.total'), children: data.seniority.total },
          { key: 'med', label: t('peek.healthcare'), children: data.seniority.healthcare },
          ...(data.qualification ? [{ key: 'cat', label: t('peek.category'), children: <span>{data.qualification.category}
            {data.qualification.valid_until && <Typography.Text type={expiring ? 'danger' : 'secondary'}> · {t('peek.until')} {d(data.qualification.valid_until)}</Typography.Text>}</span> }] : []),
          ...(data.leave ? [{ key: 'leave', label: t('peek.leave'), children: t('peek.leaveDays', { count: Math.floor(data.leave.available) }) }] : []),
          ...(data.phone || data.email ? [{ key: 'contact', label: t('peek.contacts'), children: [data.phone, data.email].filter(Boolean).join(' · ') }] : []),
          ...(sizes ? [{ key: 'sizes', label: t('peek.sizes'), children: sizes }] : []),
        ]} />
    </div>
  )
}

/** Fișa scurtă a angajatului la trecerea mouse-ului (lista angajaților): fotografia, vârsta, vechimea, raporturile, categoria. */
export default function EmployeePeek({ id, children }: { id: number; children: ReactNode }) {
  return (
    <Popover content={<Card id={id} />} mouseEnterDelay={0.45} placement="rightTop" destroyOnHidden>
      <span>{children}</span>
    </Popover>
  )
}

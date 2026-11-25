import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Badge, Calendar, Card, Drawer, Empty, List, Space, Tag, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'

import { useFetch } from '../api/hooks'

interface CalEvent { kind: string; from: string; to: string; title: string; employee: number | null; name: string; link: string }
interface CalData { year: number; month: number; events: CalEvent[]; holidays: { date: string; name: string }[] }

export const CAL_COLOR: Record<string, string> = {
  leave: '#fa8c16', sick: '#f5222d', travel: '#1677ff', idle: '#8c8c8c', trip: '#722ed1', birthday: '#eb2f96', probation: '#d4b106',
  contract: '#d4380d', document: '#13c2c2',
}
const KINDS = Object.keys(CAL_COLOR)

/** Calendarul de personal: luna cu absențele, cursele, zilele de naștere și termenele pe zile; sărbătorile și zilele de odihnă
 *  colorate; sus — câte de fiecare fel în lună; clic pe zi — lista ei, cu legătura spre fișă sau document. */
export default function HrCalendarPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [month, setMonth] = useState<Dayjs>(dayjs().startOf('month'))
  const [day, setDay] = useState<Dayjs | null>(null)
  const [hidden, setHidden] = useState<string[]>([])
  const { data } = useFetch<CalData>('/alerts/calendar/', { month: month.format('YYYY-MM') })
  const holidays = useMemo(() => new Map((data?.holidays ?? []).map((h) => [h.date, h.name])), [data])
  const events = (data?.events ?? []).filter((e) => !hidden.includes(e.kind))
  const on = (d: Dayjs) => events.filter((e) => !d.isBefore(dayjs(e.from), 'day') && !d.isAfter(dayjs(e.to), 'day'))
  const counts = Object.fromEntries(KINDS.map((k) => [k, (data?.events ?? []).filter((e) => e.kind === k).length]))
  const free = (d: Dayjs) => holidays.has(d.format('YYYY-MM-DD')) || d.day() === 0 || d.day() === 6
  const workDays = Array.from({ length: month.daysInMonth() }, (_, i) => month.date(i + 1)).filter((d) => !free(d)).length

  return (
    <Card title={t('cal.title')} extra={<Typography.Text type="secondary">{t('cal.workDays', { n: workDays, h: holidays.size })}</Typography.Text>}>
      <Space wrap style={{ marginBottom: 8 }}>
        {KINDS.filter((k) => counts[k]).map((k) => (
          <Tag key={k} style={{ cursor: 'pointer', opacity: hidden.includes(k) ? 0.4 : 1 }} title={t('cal.toggle')}
            onClick={() => setHidden(hidden.includes(k) ? hidden.filter((x) => x !== k) : [...hidden, k])}>
            <Badge color={CAL_COLOR[k]} text={`${t(`cal.kinds.${k}`)}: ${counts[k]}`} />
          </Tag>))}
        {!(data?.events.length) && <Typography.Text type="secondary">{t('cal.empty')}</Typography.Text>}
      </Space>
      <Calendar value={month} onPanelChange={(v) => setMonth(v.startOf('month'))}
        onSelect={(v, info) => { if (info.source === 'date') setDay(v) }}
        cellRender={(d, info) => {
          if (info.type !== 'date') return info.originNode
          const list = d.month() === month.month() ? on(d) : []
          const holiday = holidays.get(d.format('YYYY-MM-DD'))
          return (
            <div style={{ background: free(d) && d.month() === month.month() ? 'rgba(245, 34, 45, 0.05)' : undefined, minHeight: '100%' }}>
              {holiday && <Typography.Text type="danger" style={{ fontSize: 11 }}>{holiday}</Typography.Text>}
              {list.slice(0, 3).map((e, i) => (
                <div key={i} style={{ fontSize: 11, lineHeight: '16px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  <Badge color={CAL_COLOR[e.kind]} /> {e.name || e.title}</div>))}
              {list.length > 3 && <Typography.Text type="secondary" style={{ fontSize: 11 }}>{t('cal.more', { n: list.length - 3 })}</Typography.Text>}
            </div>
          )
        }} />
      <Drawer open={!!day} onClose={() => setDay(null)} size="default"
        title={day ? `${day.format('DD.MM.YYYY')}${holidays.get(day.format('YYYY-MM-DD')) ? ` — ${holidays.get(day.format('YYYY-MM-DD'))}` : ''}` : ''}>
        {day && (on(day).length ? <List size="small" dataSource={on(day)} renderItem={(e) => (
          <List.Item onClick={() => e.link && navigate(e.link)} style={{ cursor: e.link ? 'pointer' : undefined }}>
            <List.Item.Meta avatar={<Badge color={CAL_COLOR[e.kind]} />}
              title={<>{e.name}{e.name && ' — '}{t(`cal.kinds.${e.kind}`)}</>}
              description={`${e.title}${e.from !== e.to ? ` · ${dayjs(e.from).format('DD.MM')} – ${dayjs(e.to).format('DD.MM')}` : ''}`} />
          </List.Item>)} /> : <Empty description={t('cal.noneDay')} />)}
      </Drawer>
    </Card>
  )
}

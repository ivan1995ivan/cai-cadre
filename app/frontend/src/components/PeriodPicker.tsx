import { useTranslation } from 'react-i18next'
import { DatePicker } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'

export type Period = [Dayjs, Dayjs] | null

/** Intervalul ales → parametrii listei (`date_from`, `date_to`); fără interval nu se trimite nimic. */
export const periodParams = (period: Period) => ({
  date_from: period?.[0].format('YYYY-MM-DD'), date_to: period?.[1].format('YYYY-MM-DD'),
})

/**
 * Intervalul de date al unei liste de documente: de la – până la, cu perioadele obișnuite la un clic (azi, săptămâna,
 * luna aceasta, luna trecută, anul). Gol = toate documentele.
 */
export default function PeriodPicker({ value, onChange, style }: {
  value: Period
  onChange: (period: Period) => void
  style?: React.CSSProperties
}) {
  const { t } = useTranslation()
  const now = dayjs()
  return (
    <DatePicker.RangePicker format="DD.MM.YYYY" value={value} style={{ width: 250, ...style }}
      placeholder={[t('period.from'), t('period.to')]}
      presets={[
        { label: t('period.today'), value: [now.startOf('day'), now.endOf('day')] },
        { label: t('period.yesterday'), value: [now.subtract(1, 'day').startOf('day'), now.subtract(1, 'day').endOf('day')] },
        { label: t('period.last7'), value: [now.subtract(6, 'day').startOf('day'), now.endOf('day')] },
        { label: t('period.thisMonth'), value: [now.startOf('month'), now.endOf('month')] },
        { label: t('period.lastMonth'), value: [now.subtract(1, 'month').startOf('month'), now.subtract(1, 'month').endOf('month')] },
        { label: t('period.thisYear'), value: [now.startOf('year'), now.endOf('year')] },
      ]}
      onChange={(v) => onChange(v && v[0] && v[1] ? [v[0], v[1]] : null)} />
  )
}

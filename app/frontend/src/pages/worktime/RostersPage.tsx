import { useTranslation } from 'react-i18next'

import { MonthDocList } from './MonthDocs'

/** Graficele lunare ale secțiilor (ture și gărzi). */
export default function RostersPage() {
  const { t } = useTranslation()
  return <MonthDocList endpoint="/worktime/rosters/" title={t('wt.rosters')} route="/worktime/rosters" />
}

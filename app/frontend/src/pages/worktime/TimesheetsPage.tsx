import { useTranslation } from 'react-i18next'

import { MonthDocList } from './MonthDocs'

/** Tabelele de pontaj ale secțiilor pe lună, cu exportul lunii pentru 1C Salariu. */
export default function TimesheetsPage() {
  const { t } = useTranslation()
  return <MonthDocList endpoint="/worktime/timesheets/" title={t('menu.timesheets')} route="/timesheets" exportUrl="/worktime/timesheets/export/" />
}

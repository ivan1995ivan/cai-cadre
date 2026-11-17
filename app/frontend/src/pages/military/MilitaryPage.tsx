import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { Card, Tabs } from 'antd'

import ReportView from '../reports/ReportView'

/** Evidența militară: registrul, cei fără fișă, modificările lunii pentru centrul militar, lista recruților. */
export default function MilitaryPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'military_register'
  return (
    <Card title={t('menu.military')}>
      <Tabs activeKey={tab} onChange={(k) => setParams({ tab: k })} destroyOnHidden
        items={['military_register', 'military_missing', 'military_changes', 'military_recruits'].map((k) => ({
          key: k, label: t(`mil.tabs.${k}`), children: <ReportView reportKey={k} embedded />,
        }))} />
    </Card>
  )
}

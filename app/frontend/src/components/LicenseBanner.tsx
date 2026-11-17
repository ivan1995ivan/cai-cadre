import { useTranslation } from 'react-i18next'
import { Alert, Button } from 'antd'

import { useApp } from '../auth/AppContext'

/** Avertizarea despre licență, pentru toți utilizatorii: expiră curând / sistemul e doar pentru citire. */
export default function LicenseBanner() {
  const { t } = useTranslation()
  const { me, hasPerm } = useApp()
  const lic = me?.license
  if (!lic || (!lic.read_only && !lic.warn)) return null
  const action = hasPerm('settings.view') ? <Button size="small" href="/admin/license">{t('license.open')}</Button> : undefined
  if (lic.read_only) {
    return <Alert type="error" showIcon banner style={{ marginBottom: 12 }} action={action}
      title={lic.mode === 'trial' ? t('license.trialReadOnly') : t('license.readOnly')} description={lic.error || undefined} />
  }
  return <Alert type="warning" showIcon banner closable style={{ marginBottom: 12 }} action={action}
    title={t(lic.mode === 'trial' ? 'license.trialEnds' : 'license.ends', { days: lic.days_left })} />
}

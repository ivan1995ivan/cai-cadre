import { useTranslation } from 'react-i18next'
import { Alert, Card, List, Space, Tag, Typography } from 'antd'

import ExcelImport from '../../components/ExcelImport'
import { invalidateCache } from '../../api/hooks'
import { useApp } from '../../auth/AppContext'

interface Step { code: string; url: string; perm: string; createOccupations?: boolean }

// Ordinea contează: un fișier se sprijină pe ce s-a importat înainte (funcțiile → angajații → filele dosarului).
const STEPS: Step[] = [
  { code: 'occupations', url: '/org/import/', perm: 'dictionaries.create' },
  { code: 'specialties', url: '/org/import/', perm: 'dictionaries.create' },
  { code: 'subdivisions', url: '/org/import/', perm: 'org.create' },
  { code: 'employees', url: '/staff/import/', perm: 'employees.create', createOccupations: true },
  { code: 'documents', url: '/staff/import/', perm: 'employees.edit' },
  { code: 'family', url: '/staff/import/', perm: 'employees.edit' },
  { code: 'education', url: '/staff/import/', perm: 'employees.edit' },
  { code: 'experience', url: '/staff/import/', perm: 'employees.edit' },
]

/** Importul din Excel: pornirea unei baze noi (fără bază 1C de preluat) — clasificatoare, subdiviziuni, angajați, dosare. */
export default function ImportPage() {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  return (
    <Card title={t('menu.excelImport')}>
      <Alert showIcon type="info" style={{ marginBottom: 16 }} title={t('imports.intro')} />
      <List
        dataSource={STEPS.filter((s) => hasPerm(s.perm))}
        renderItem={(s, i) => (
          <List.Item actions={[
            <ExcelImport key="imp" code={s.code} url={s.url} label={t('excel.import')} allowCreateOccupations={s.createOccupations}
              onDone={() => invalidateCache('')} />,
          ]}>
            <List.Item.Meta
              title={<Space><Tag>{i + 1}</Tag>{t(`imports.steps.${s.code}.title`)}</Space>}
              description={<Typography.Text type="secondary">{t(`imports.steps.${s.code}.hint`)}</Typography.Text>} />
          </List.Item>
        )} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>{t('imports.staffListHint')}</Typography.Paragraph>
    </Card>
  )
}

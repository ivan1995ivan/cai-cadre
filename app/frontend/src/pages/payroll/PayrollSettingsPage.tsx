import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Select, Space, Tag, Typography } from 'antd'
import { WalletOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import { useFetch } from '../../api/hooks'
import type { PayConstant } from '../../api/payroll'
import { useApp } from '../../auth/AppContext'
import PayTypesPage from './PayTypesPage'

/** O setare a salariului (Administrare → Setări): tipurile de calcul sau constantele cu istoric. */
export default function PayrollSettingsPage({ part, title }: { part: 'types' | 'constants'; title: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('payroll_settings.edit')
  // constantele — pentru codurile deja folosite (doar pe pagina lor)
  const { data: constants } = useFetch<PayConstant[]>(part === 'constants' ? '/payroll/constants/' : null)
  const [code, setCode] = useState<string | undefined>()
  const codes = Array.from(new Map((constants ?? []).map((c) => [c.code, c.name])).entries())

  const constantFields: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 200, input: () => <Select showSearch allowClear options={codes.map(([c, n]) => ({ value: c, label: `${c} — ${n}` }))}
      mode={undefined} /> },
    { key: 'name', label: t('pay.const.name'), required: true },
    { key: 'value', label: t('pay.const.value'), type: 'number', required: true, width: 120, render: (v, r) => `${Number(v).toLocaleString('ro-MD')} ${r.unit ?? ''}` },
    { key: 'unit', label: t('pay.const.unit'), width: 70, inTable: false },
    { key: 'date_from', label: t('pay.const.dateFrom'), type: 'date', required: true, width: 120 },
    { key: 'source', label: t('pay.const.source'), width: 260, render: (v) => {
      const text = String(v ?? '')
      // temeiul neconfirmat încă din textul oficial („— de verificat”): se arată ca atare, valoarea se poate corecta
      return /de verificat/i.test(text) ? <Space size={4}>{text.replace(/\s*—\s*de verificat/i, '')}<Tag color="warning">{t('pay.const.check')}</Tag></Space> : text
    } },
  ]
  return (
    <Card title={title} extra={<Button icon={<WalletOutlined />} onClick={() => navigate('/payroll')}>{t('menu.payroll')}</Button>}>
      {part === 'types' ? (
        <PayTypesPage />
      ) : (
        <>
          <Space style={{ marginBottom: 12 }} wrap>
            <Typography.Text type="secondary">{t('pay.const.hint')}</Typography.Text>
            <Select allowClear style={{ width: 420 }} placeholder={t('pay.const.filter')} value={code} onChange={setCode}
              options={codes.map(([c, n]) => ({ value: c, label: `${n} (${c})` }))} />
          </Space>
          <CrudTable key={code ?? 'all'} endpoint="/payroll/constants/" params={code ? { code } : {}} fields={constantFields} canEdit={canEdit}
            defaults={{ code, date_from: dayjs().startOf('year').format('YYYY-MM-DD') }} />
        </>
      )}
    </Card>
  )
}

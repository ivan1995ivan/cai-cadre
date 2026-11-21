import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button, Card, DatePicker, Select, Space, Tag, Typography } from 'antd'
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
          <FiscalRegimes canEdit={canEdit} />
          <Typography.Title level={5} style={{ marginTop: 16 }}>{t('itp.constantsTitle')}</Typography.Title>
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

/** Regimul fiscal pe luni (general / IT Park), cu istoric: lunile vechi se calculează după regimul lor (CF art. 375). */
function FiscalRegimes({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation()
  const month = (v: unknown) => (v ? dayjs(String(v)).format('MM.YYYY') : '')
  const fields: CrudField[] = [
    { key: 'regime', label: t('itp.regime'), type: 'select', required: true, width: 230,
      options: ['general', 'it_park'].map((v) => ({ value: v, label: t(`itp.regimes.${v}`) })),
      render: (v) => <Tag color={v === 'it_park' ? 'purple' : 'default'}>{t(`itp.regimes.${String(v)}`)}</Tag> },
    { key: 'status_date', label: t('itp.statusDate'), type: 'date', width: 130, extra: t('itp.statusDateHint') },
    { key: 'date_from', label: t('itp.dateFrom'), width: 120, render: month, extra: t('itp.dateFromHint'),
      input: () => <MonthField /> },
    { key: 'document', label: t('itp.document'), width: 260 },
    { key: 'note', label: t('org.notes'), inTable: false },
  ]
  return (
    <>
      <Typography.Title level={5} style={{ marginTop: 0 }}>{t('itp.regimeTitle')}</Typography.Title>
      <Typography.Paragraph type="secondary">{t('itp.regimeHint')}</Typography.Paragraph>
      <CrudTable endpoint="/payroll/fiscal-regimes/" fields={fields} canEdit={canEdit} defaults={{ regime: 'it_park' }} />
    </>
  )
}

/** „În vigoare din” — luna (se trimite prima zi a lunii); goală — luna următoare datei statutului. */
function MonthField({ value, onChange }: { value?: string | null; onChange?: (v: string | null) => void }) {
  return <DatePicker picker="month" format="MM.YYYY" allowClear style={{ width: '100%' }} value={value ? dayjs(String(value)) : null}
    onChange={(d) => onChange?.(d ? d.startOf('month').format('YYYY-MM-DD') : null)} />
}

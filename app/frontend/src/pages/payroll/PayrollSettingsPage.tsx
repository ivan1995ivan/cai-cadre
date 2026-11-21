import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Input, Select, Space, Typography } from 'antd'
import { WalletOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import CrudTable, { type CrudField } from '../../components/CrudTable'
import { useFetch } from '../../api/hooks'
import { AUTO_KEYS, FORMULAS, type PayConstant, type PayType } from '../../api/payroll'
import { useApp } from '../../auth/AppContext'
import { useNameFields } from '../org/DictionariesPage'

/** Treptele pe vechimea totală în muncă ({from: ani, pct}) scrise ca text: „3:5, 10:10, 20:15”. */
function ScaleInput({ value, onChange }: { value?: { from: number; pct: number }[]; onChange?: (v: unknown[]) => void }) {
  const { t } = useTranslation()
  const text = (value ?? []).map((s) => `${s.from}:${s.pct}`).join(', ')
  const [draft, setDraft] = useState(text)
  return (
    <Input value={draft} placeholder={t('pay.type.scalePlaceholder')} onChange={(e) => setDraft(e.target.value)} onBlur={() => {
      const steps = draft.split(/[,;]/).map((p) => p.trim()).filter(Boolean).map((p) => {
        const [k, v] = p.split(':').map((x) => x.trim())
        return { from: Number(k), pct: Number(v) }  // un text care nu e număr îl respinge serverul, cu mesajul lui
      })
      onChange?.(steps)
    }} />
  )
}

/** O setare a salariului (Administrare → Setări): tipurile de calcul sau constantele cu istoric. */
export default function PayrollSettingsPage({ part, title }: { part: 'types' | 'constants'; title: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('payroll_settings.edit')
  const names = useNameFields()
  // tipurile — pentru baza de calcul a unui tip, constantele — pentru codurile deja folosite: fiecare doar pe pagina lui
  const { data: types } = useFetch<PayType[]>(part === 'types' ? '/payroll/types/' : null)
  const { data: constants } = useFetch<PayConstant[]>(part === 'constants' ? '/payroll/constants/' : null)
  const [code, setCode] = useState<string | undefined>()
  const codes = Array.from(new Map((constants ?? []).map((c) => [c.code, c.name])).entries())
  const typeOptions = (types ?? []).map((x) => ({ value: x.code, label: `${x.code} — ${x.name_ro}` }))

  const constantFields: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 200, input: () => <Select showSearch allowClear options={codes.map(([c, n]) => ({ value: c, label: `${c} — ${n}` }))}
      mode={undefined} /> },
    { key: 'name', label: t('pay.const.name'), required: true },
    { key: 'value', label: t('pay.const.value'), type: 'number', required: true, width: 120, render: (v, r) => `${Number(v).toLocaleString('ro-MD')} ${r.unit ?? ''}` },
    { key: 'unit', label: t('pay.const.unit'), width: 70, inTable: false },
    { key: 'date_from', label: t('pay.const.dateFrom'), type: 'date', required: true, width: 120 },
    { key: 'source', label: t('pay.const.source'), width: 260 },
  ]
  const typeFields: CrudField[] = [
    { key: 'code', label: t('common.code'), required: true, width: 90 },
    ...names,
    { key: 'category', label: t('pay.type.category'), type: 'select', required: true, width: 150,
      options: ['accrual', 'deduction', 'employer'].map((c) => ({ value: c, label: t(`pay.type.categories.${c}`) })), render: (_v, r) => String(r.category_label ?? '') },
    { key: 'formula', label: t('pay.type.formula'), type: 'select', required: true, width: 200,
      options: FORMULAS.map((f) => ({ value: f, label: t(`pay.type.formulas.${f}`) })), render: (_v, r) => String(r.formula_label ?? '') },
    { key: 'auto', label: t('pay.type.auto'), type: 'select', inTable: false, options: AUTO_KEYS.map((a) => ({ value: a, label: t(`pay.type.autos.${a}`) })) },
    { key: 'percent', label: t('pay.type.percent'), type: 'number', width: 70, render: (v) => (Number(v) ? `${Number(v)}%` : '') },
    { key: 'base_codes', label: t('pay.type.base'), type: 'multiselect', options: typeOptions, inTable: false, extra: t('pay.type.baseHint') },
    { key: 'scale', label: t('pay.type.scale'), inTable: false, input: () => <ScaleInput />, extra: t('pay.type.scaleHint') },
    { key: 'taxable', label: t('pay.type.taxable'), type: 'bool', width: 80 },
    { key: 'cas', label: 'CAS', type: 'bool', width: 60 },
    { key: 'cnam', label: 'CNAM', type: 'bool', width: 70 },
    { key: 'exempt_month', label: t('pay.type.exemptMonth'), type: 'number', inTable: false },
    { key: 'exempt_year', label: t('pay.type.exemptYear'), type: 'number', inTable: false },
    { key: 'exempt_avg_pct', label: t('pay.type.exemptAvg'), type: 'number', inTable: false },
    { key: 'in_average', label: t('pay.type.inAverage'), type: 'bool', width: 90 },
    { key: 'ipc_code', label: t('pay.type.ipc'), inTable: false },
    { key: 'account', label: t('pay.type.account'), inTable: false },
    { key: 'on_payslip', label: t('pay.type.onPayslip'), type: 'bool', inTable: false },
    { key: 'sort', label: t('org.sort'), type: 'number', inTable: false },
    { key: 'is_active', label: t('common.active'), type: 'bool', width: 80 },
  ]

  return (
    <Card title={title} extra={<Button icon={<WalletOutlined />} onClick={() => navigate('/payroll')}>{t('menu.payroll')}</Button>}>
      {part === 'types' ? (
        <CrudTable endpoint="/payroll/types/" fields={typeFields} canEdit={canEdit}
          defaults={{ category: 'accrual', formula: 'fixed', auto: 'none', percent: 0, base_codes: [], scale: [], taxable: true, cas: true, cnam: true,
            exempt_month: 0, exempt_year: 0, exempt_avg_pct: 0, in_average: true, ipc_code: 'SAL', on_payslip: true }}
          title={<Typography.Text type="secondary">{t('pay.type.hint')}</Typography.Text>} />
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

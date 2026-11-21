import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AutoComplete, Button, Input, Space, Tooltip, type FormInstance } from 'antd'
import { EllipsisOutlined } from '@ant-design/icons'

import { api } from '../api/client'
import type { Paged } from '../api/client'
import PickerModal from './PickerModal'

export interface Bank {
  id: number; country: string; code: string; name: string; short_name: string; bic: string; fiscal_code: string
  address: string; phone: string; email: string; website: string; note: string; custom: boolean; deletion_mark?: boolean
}

/** Banca după identificatorul din IBAN (MD24 AG… → maib, RO49 BTRL… → Banca Transilvania). */
export async function bankByIban(iban?: string): Promise<Bank | null> {
  const clean = (iban ?? '').replace(/\s+/g, '').toUpperCase()
  if (clean.length < 8) return null
  try {
    const { data } = await api.get<Paged<Bank>>('/banks/', { params: { iban: clean } })
    return data.results.find((b) => !b.deletion_mark) ?? null
  } catch {
    return null
  }
}

/**
 * Pune banca în formular (câmpurile `bank_name` și `bic`). Aleasă din listă — se pune mereu; recunoscută după IBAN — doar
 * dacă denumirea e goală sau era altă bancă (alt BIC), ca denumirea scrisă de mână să rămână.
 */
export function applyBank(form: FormInstance, bank: Bank | null, fromIban = false) {
  if (!bank) return
  const { bank_name: name, bic } = form.getFieldsValue(['bank_name', 'bic'])
  if (!fromIban || !name || (bic && bic !== bank.bic)) form.setFieldsValue({ bank_name: bank.name, bic: bank.bic })
  else if (!bic) form.setFieldsValue({ bic: bank.bic })
}

/** Câmpul IBAN: la ieșirea din câmp banca și BIC-ul se completează singure din clasificator. */
export function IbanInput({ form, value, onChange, placeholder }: {
  form: FormInstance; value?: string; onChange?: (v: string) => void; placeholder?: string
}) {
  return (
    <Input value={value} placeholder={placeholder} onChange={(e) => onChange?.(e.target.value)}
      onBlur={(e) => bankByIban(e.target.value).then((b) => applyBank(form, b, true))} />
  )
}

/**
 * Banca din clasificator (Administrare → Setări → Bănci): scrii („maib”, „BTRL”, „Victoria”) sau apeși „…” și alegi din listă;
 * la alegere se pune și BIC-ul (`onPick`). Se păstrează ca text, deci se poate scrie și o bancă care nu e în listă.
 */
export default function BankInput({ value, onChange, onPick, placeholder, disabled }: {
  value?: string; onChange?: (v: string) => void; onPick?: (bank: Bank) => void; placeholder?: string; disabled?: boolean
}) {
  const { t } = useTranslation()
  const [text, setText] = useState('')
  const [found, setFound] = useState<Bank[]>([])
  const [listOpen, setListOpen] = useState(false)
  useEffect(() => {
    const q = text.trim()
    if (q.length < 2) {
      setFound([])
      return
    }
    const timer = setTimeout(() => {
      api.get<Paged<Bank>>('/banks/', { params: { search: q, page_size: 20 } })
        .then((r) => setFound(r.data.results.filter((b) => !b.deletion_mark)))
        .catch(() => setFound([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [text])
  const pick = (bank: Bank) => {
    onChange?.(bank.name)
    onPick?.(bank)
  }
  return (
    <>
      <Space.Compact style={{ width: '100%' }}>
        <AutoComplete value={value} disabled={disabled} placeholder={placeholder ?? t('picker.typeOrPick')} allowClear
          options={found.map((b) => ({ key: b.id, value: b.name, bank: b, label: <>{b.name} <span style={{ opacity: 0.6 }}>· {b.bic} · {b.country}</span></> }))}
          onSearch={setText} onChange={(v) => onChange?.(v ?? '')} style={{ flex: '1 1 0', minWidth: 0 }}
          onSelect={(_, option) => onPick?.((option as { bank: Bank }).bank)} />
        <Tooltip title={t('picker.openList')}>
          <Button disabled={disabled} icon={<EllipsisOutlined />} onClick={() => setListOpen(true)} aria-label={t('picker.openList')} />
        </Tooltip>
      </Space.Compact>
      <PickerModal<Bank> open={listOpen} title={t('menu.banks')} endpoint="/banks/" onClose={() => setListOpen(false)}
        onPick={(row) => { pick(row); setListOpen(false) }}
        columns={[
          { title: t('banks.name'), dataIndex: 'name', render: (v, b) => <>{v}{b.short_name && <span style={{ opacity: 0.6 }}> ({b.short_name})</span>}</> },
          { title: 'BIC / SWIFT', dataIndex: 'bic', width: 110 },
          { title: t('banks.code'), dataIndex: 'code', width: 80 },
          { title: t('banks.address'), dataIndex: 'address', width: 260 },
          { title: '', dataIndex: 'country', width: 50 },
        ]} />
    </>
  )
}

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AutoComplete, Button, Space, Tooltip } from 'antd'
import { EllipsisOutlined } from '@ant-design/icons'

import { api } from '../api/client'
import type { Paged } from '../api/client'
import PickerModal from './PickerModal'

interface Locality { id: number; label: string; name: string; kind: string; commune: string; region: string; postal_code: string; country: string; deletion_mark?: boolean }

/**
 * Localitatea din clasificator (Administrare → Setări → Localități): scrii („Sipot” → „Sipoteni, r. Călărași”) sau apeși „…” și
 * alegi din listă. Se păstrează ca text, deci se poate scrie și o localitate care nu e în listă.
 */
export default function LocalityInput({ value, onChange, placeholder, disabled }: {
  value?: string; onChange?: (v: string) => void; placeholder?: string; disabled?: boolean
}) {
  const { t } = useTranslation()
  const [text, setText] = useState('')
  const [options, setOptions] = useState<{ value: string; label: string }[]>([])
  const [listOpen, setListOpen] = useState(false)
  useEffect(() => {
    const q = text.trim()
    if (q.length < 2) {
      setOptions([])
      return
    }
    const timer = setTimeout(() => {
      api.get<Paged<Locality>>('/localities/', { params: { search: q, page_size: 20 } })
        .then((r) => setOptions(r.data.results.filter((x) => !x.deletion_mark).map((x) => ({ value: x.label, label: x.label }))))
        .catch(() => setOptions([]))
    }, 250)
    return () => clearTimeout(timer)
  }, [text])
  return (
    <>
      <Space.Compact style={{ width: '100%' }}>
        <AutoComplete value={value} options={options} disabled={disabled} placeholder={placeholder ?? t('picker.typeOrPick')} allowClear
          onSearch={setText} onChange={(v) => onChange?.(v ?? '')} style={{ width: '100%' }} />
        <Tooltip title={t('picker.openList')}>
          <Button disabled={disabled} icon={<EllipsisOutlined />} onClick={() => setListOpen(true)} aria-label={t('picker.openList')} />
        </Tooltip>
      </Space.Compact>
      <PickerModal<Locality> open={listOpen} title={t('menu.localities')} endpoint="/localities/" onClose={() => setListOpen(false)}
        onPick={(row) => { onChange?.(row.label); setListOpen(false) }}
        columns={[
          { title: t('localities.name'), dataIndex: 'name' },
          { title: t('localities.kind'), dataIndex: 'kind', width: 100 },
          { title: t('localities.commune'), dataIndex: 'commune', width: 170 },
          { title: t('localities.region'), dataIndex: 'region', width: 190 },
          { title: t('localities.postal'), dataIndex: 'postal_code', width: 90 },
          { title: '', dataIndex: 'country', width: 50 },
        ]} />
    </>
  )
}

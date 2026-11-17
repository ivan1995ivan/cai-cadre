import { useTranslation } from 'react-i18next'
import { Alert, Button, Popconfirm, Tooltip, message } from 'antd'
import { DeleteOutlined, UndoOutlined } from '@ant-design/icons'

import { api, errorText } from '../api/client'
import { invalidateCache } from '../api/hooks'

/** Rândul unei liste: `deletion_mark` vine de la server pentru obiectele care se marchează pentru ștergere. */
export interface Markable { id: number | string; deletion_mark?: boolean }

/** Marchează / scoate marcajul (ca în 1C): `DELETE …/id/` marchează, `POST …/id/unmark/` îl scoate.
 *  Ștergerea de tot se face în Administrare → Ștergerea obiectelor marcate. */
export async function toggleMark(endpoint: string, row: Markable): Promise<boolean> {
  try {
    if (row.deletion_mark) await api.post(`${endpoint}${row.id}/unmark/`)
    else await api.delete(`${endpoint}${row.id}/`)
    invalidateCache(endpoint)
    return true
  } catch (e) {
    message.error(errorText(e))
    return false
  }
}

/** Butonul de pe rândul listei: coșul (marchează) sau săgeata înapoi (scoate marcajul). */
export default function MarkButton({ endpoint, row, onDone, text }: {
  endpoint: string // cu bara la sfârșit, de ex. '/org/subdivisions/'
  row: Markable
  onDone?: () => void
  text?: boolean // buton cu text (în antetul documentului), nu doar iconiță
}) {
  const { t } = useTranslation()
  const marked = !!row.deletion_mark
  const label = t(marked ? 'marks.unmark' : 'marks.mark')
  const run = async () => { if (await toggleMark(endpoint, row)) onDone?.() }
  return (
    <Popconfirm title={t(marked ? 'marks.unmarkConfirm' : 'marks.markConfirm')} onConfirm={run}>
      {text ? <Button danger={!marked} icon={marked ? <UndoOutlined /> : <DeleteOutlined />}>{label}</Button> : (
        <Tooltip title={label}>
          <Button type="text" size="small" danger={!marked} icon={marked ? <UndoOutlined /> : <DeleteOutlined />} />
        </Tooltip>
      )}
    </Popconfirm>
  )
}

/** Banda din documentul marcat: nu se mai modifică până nu i se scoate marcajul. */
export function MarkedBanner({ endpoint, row, onDone, canUnmark }: { endpoint: string; row: Markable; onDone?: () => void; canUnmark: boolean }) {
  const { t } = useTranslation()
  if (!row.deletion_mark) return null
  return (
    <Alert type="error" showIcon style={{ marginBottom: 12 }} title={t('marks.banner')}
      action={canUnmark ? <MarkButton endpoint={endpoint} row={row} onDone={onDone} text /> : undefined} />
  )
}

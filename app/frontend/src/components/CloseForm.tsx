import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button, Tooltip } from 'antd'
import { CloseOutlined } from '@ant-design/icons'

import { useTabs } from '../layout/tabs'

/** ✕ în dreapta sus a formei (ultimul buton, ca în 1C): închide forma — fila ei de jos se închide și se trece la cea
 *  de alături; fără filă (adresa deschisă direct), la lista ei (`to`). Cu modificări nesalvate întreabă întâi
 *  (UnsavedGuard). */
export default function CloseForm({ to }: { to: string }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { tabs, close } = useTabs()
  const onClick = () => {
    const tab = tabs.find((x) => x.path.split('?')[0] === location.pathname)
    if (tab) close(tab.path)
    else navigate(to)
  }
  return (
    <Tooltip title={t('common.closeForm')}>
      <Button icon={<CloseOutlined />} onClick={onClick} aria-label={t('common.closeForm')} />
    </Tooltip>
  )
}

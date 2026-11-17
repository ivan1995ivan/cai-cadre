import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Card, Empty, Input, Space, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'

import { useSettingsItems } from '../../layout/menu'
import { navLabel } from '../../layout/nav'
import { fold } from '../../utils/text'

/**
 * Administrare → Setări: toate setările programului într-un singur loc, în ordine alfabetică, cu căutare după denumire.
 * Se văd doar cele la care utilizatorul are drept; Enter deschide setarea când căutarea a lăsat una singură.
 */
export default function SettingsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const items = useSettingsItems()
  const [search, setSearch] = useState('')
  const found = useMemo(() => {
    const q = fold(search.trim())
    return q ? items.filter((i) => fold(navLabel(t, i)).includes(q)) : items
  }, [items, search, t])

  return (
    <Card title={t('menu.settings')}>
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
        <Typography.Text type="secondary">{t('settingsPage.hint')}</Typography.Text>
        <Input allowClear autoFocus prefix={<SearchOutlined />} placeholder={t('settingsPage.search')} style={{ maxWidth: 420 }}
          value={search} onChange={(e) => setSearch(e.target.value)}
          onPressEnter={() => { if (found.length === 1) navigate(found[0].path) }} />
        {found.length === 0 ? <Empty description={t('settingsPage.none')} /> : (
          <div style={{ columnWidth: 280, columnGap: 32 }}>
            {found.map((i) => (
              <Link key={i.key} to={i.path} className="settings-link">
                {i.icon}<span>{navLabel(t, i)}</span>
              </Link>
            ))}
          </div>
        )}
      </Space>
    </Card>
  )
}

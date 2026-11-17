import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Drawer, Empty, Input, List, Spin, Typography } from 'antd'
import { ArrowLeftOutlined, SearchOutlined } from '@ant-design/icons'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { api } from '../api/client'
import { useApp } from '../auth/AppContext'

interface Article {
  key: string
  title: string
  content?: string
}

/**
 * Instrucțiunea pentru ecranul curent, ca F1 din 1C (tasta F1 sau butonul „?” din antet): sus fișa ecranului (unde vă
 * aflați), apoi articolul ecranului sau al documentului deschis; dedesubt toate instrucțiunile, cu căutare.
 */
export default function HelpDrawer({ open, onClose, helpKey, screen }: { open: boolean; onClose: () => void; helpKey: string; screen?: string }) {
  const { t } = useTranslation()
  const { lang } = useApp()
  const [key, setKey] = useState(helpKey)
  const [article, setArticle] = useState<Article | null>(null)
  const [index, setIndex] = useState<Article[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (open) {
      setKey(helpKey)
      setSearch('')
    }
  }, [open, helpKey])

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setArticle(null)
    api
      .get<Article>(`/help/${lang}/${key}/`)
      .then((r) => setArticle(r.data))
      .catch(() => setArticle(null))
      .finally(() => setLoading(false))
  }, [open, key, lang])

  useEffect(() => {
    if (open) api.get<Article[]>(`/help/${lang}/`).then((r) => setIndex(r.data)).catch(() => setIndex([]))
  }, [open, lang])

  const found = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? index.filter((a) => a.title.toLowerCase().includes(q) || a.key.includes(q)) : index
  }, [index, search])
  const own = key === helpKey

  return (
    <Drawer open={open} onClose={onClose} size="large" title={article?.title || t('help.title')}
      extra={!own && <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => setKey(helpKey)}>{t('help.back')}</Button>}>
      {own && screen && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          title={<span>{t('help.screen')}: <b>{screen}</b></span>}
          description={<Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('help.f1')}</Typography.Text>} />
      )}
      {loading ? (
        <Spin />
      ) : article ? (
        <div className="help-article">
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) =>
                href?.startsWith('help:') ? (
                  <a onClick={() => setKey(href.slice(5))}>{children}</a>
                ) : (
                  <a href={href} target="_blank" rel="noreferrer">{children}</a>
                ),
            }}
          >
            {article.content || ''}
          </Markdown>
        </div>
      ) : (
        <Empty description={t('help.notFound')} />
      )}
      {index.length > 0 && (
        <>
          <Typography.Title level={5} style={{ marginTop: 32 }}>{t('help.allArticles')}</Typography.Title>
          <Input allowClear prefix={<SearchOutlined />} placeholder={t('help.search')} value={search}
            onChange={(e) => setSearch(e.target.value)} style={{ marginBottom: 8 }} />
          <List
            size="small"
            dataSource={found}
            renderItem={(item) => (
              <List.Item style={{ background: item.key === article?.key ? 'var(--ant-color-primary-bg)' : undefined, paddingInline: 8, borderRadius: 6 }}>
                <a onClick={() => setKey(item.key)}>{item.title}</a>
              </List.Item>
            )}
          />
        </>
      )}
    </Drawer>
  )
}

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, Col, Descriptions, Divider, Row, Space, Spin, Tag, Typography } from 'antd'
import { GlobalOutlined, PhoneOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { api } from '../api/client'
import { useApp } from '../auth/AppContext'
import DevelopedBy from '../components/DevelopedBy'
import { PRODUCT } from '../product'

/**
 * „Despre program”: produsul, versiunea, producătorul și legătura cu el (site, telefon), apoi „Posibilitățile
 * sistemului” — prezentarea pe scurt a tot ce face programul (pentru angajații noi și clienți).
 */
export default function AboutPage() {
  const { t } = useTranslation()
  const { lang, branding, companyName } = useApp()
  const [text, setText] = useState<string | null>(null)
  useEffect(() => {
    api.get<{ content: string }>(`/help/${lang}/posibilitati/`).then((r) => setText(r.data.content)).catch(() => setText(''))
  }, [lang])
  const year = new Date().getFullYear()
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 960, margin: '0 auto', display: 'flex' }}>
      <Card>
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} md={9} style={{ textAlign: 'center' }}>
            <img src="/favicon.svg" alt="" width={88} height={88} />
            <Typography.Title level={2} style={{ margin: '12px 0 0' }}>{PRODUCT.name}</Typography.Title>
            <Typography.Text type="secondary">{t('about.tagline')}</Typography.Text>
            <div style={{ marginTop: 10 }}>
              {branding?.version && <Tag color="processing">{t('about.version', { version: branding.version })}</Tag>}
            </div>
            <div style={{ marginTop: 16 }}><DevelopedBy /></div>
          </Col>
          <Col xs={24} md={15}>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label={t('about.producer')}><b>{PRODUCT.producer}</b></Descriptions.Item>
              <Descriptions.Item label={t('about.website')}>
                <a href={PRODUCT.url} target="_blank" rel="noreferrer">{PRODUCT.website}</a>
              </Descriptions.Item>
              <Descriptions.Item label={t('about.phone')}><a href={PRODUCT.phoneHref}>{PRODUCT.phone}</a></Descriptions.Item>
              <Descriptions.Item label={t('about.licensee')}>{companyName}</Descriptions.Item>
            </Descriptions>
            <Space wrap style={{ marginTop: 12 }}>
              <Button type="primary" icon={<GlobalOutlined />} href={PRODUCT.url} target="_blank">{PRODUCT.website}</Button>
              <Button icon={<PhoneOutlined />} href={PRODUCT.phoneHref}>{PRODUCT.phone}</Button>
            </Space>
            <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0, fontSize: 13 }}>
              <QuestionCircleOutlined /> {t('about.support')}
            </Typography.Paragraph>
          </Col>
        </Row>
        <Divider style={{ margin: '16px 0 8px' }} />
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          © {PRODUCT.since}{year > PRODUCT.since ? `–${year}` : ''} {PRODUCT.producer}. {t('about.rights')}
        </Typography.Text>
      </Card>
      <Card title={t('about.title')}>
        {text === null ? <Spin /> : (
          <div className="help-article">
            <Markdown remarkPlugins={[remarkGfm]}>{text}</Markdown>
          </div>
        )}
      </Card>
    </Space>
  )
}

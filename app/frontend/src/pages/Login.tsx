import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Form, Input, Segmented, Space, Typography } from 'antd'
import { CheckCircleFilled, LockOutlined, IdcardOutlined, UserOutlined } from '@ant-design/icons'

import { errorText, takeLogoutReason } from '../api/client'
import { useApp } from '../auth/AppContext'
import { isDesktopLook, PALETTES } from '../theme/themes'
import { LANG_LABELS, type Lang } from '../api/types'
import DevelopedBy from '../components/DevelopedBy'
import { PRODUCT } from '../product'

export default function Login() {
  const { t } = useTranslation()
  const { login, branding, companyName, lang, setLang, themeName, languages } = useApp()
  const [error, setError] = useState(takeLogoutReason)
  const [loading, setLoading] = useState(false)
  const dark = PALETTES[themeName].dark
  const logo = (dark && branding?.logo_dark) || branding?.logo

  const submit = async (values: { username: string; password: string }) => {
    setLoading(true)
    setError('')
    try {
      await login(values.username, values.password)
    } catch (e) {
      setError(errorText(e, t('login.failed')))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <aside className="login-hero">
        <div className="login-hero-mark"><IdcardOutlined /></div>
        <Typography.Title level={2} style={{ color: '#fff', margin: '20px 0 8px' }}>{PRODUCT.name}</Typography.Title>
        <Typography.Paragraph style={{ color: 'rgba(255,255,255,0.9)', fontSize: 16, maxWidth: 420 }}>{t('login.tagline')}</Typography.Paragraph>
        <ul className="login-hero-list">
          {(t('login.features', { returnObjects: true }) as string[]).map((f) => (
            <li key={f}><CheckCircleFilled /> {f}</li>
          ))}
        </ul>
      </aside>
      <main className="login-main">
      {/* aspectul clasic de birou: fereastra de intrare cu bara ei de titlu */}
      <Card className="login-card" style={{ width: '100%', maxWidth: 400 }}
        title={isDesktopLook(themeName) ? `${PRODUCT.name} — ${t('login.title')}` : undefined}>
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            {logo ? (
              <img src={logo} alt="" style={{ maxHeight: 72, maxWidth: '100%' }} />
            ) : (
              <img src="/favicon.svg" alt="" width={56} height={56} />
            )}
            <Typography.Title level={4} style={{ marginTop: 12, marginBottom: 0 }}>{companyName}</Typography.Title>
            <Typography.Text type="secondary">{t('login.title')}</Typography.Text>
          </div>
          {error && <Alert type="error" title={error} showIcon />}
          <Form layout="vertical" onFinish={submit} requiredMark={false}>
            <Form.Item name="username" label={t('login.username')} rules={[{ required: true, message: t('common.required') }]}>
              <Input prefix={<UserOutlined />} autoFocus autoComplete="username" size="large" />
            </Form.Item>
            <Form.Item name="password" label={t('login.password')} rules={[{ required: true, message: t('common.required') }]}>
              <Input.Password prefix={<LockOutlined />} autoComplete="current-password" size="large" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={loading}>{t('login.submit')}</Button>
          </Form>
          {languages.length > 1 && <div style={{ textAlign: 'center' }}>
            <Segmented<Lang> value={lang} onChange={setLang} options={languages.map((l) => ({ label: LANG_LABELS[l], value: l }))} />
          </div>}
          <div style={{ textAlign: 'center' }}><DevelopedBy size="small" /></div>
          <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', fontSize: 12, lineHeight: 1.7 }}>
            <b>{PRODUCT.name}</b>{branding?.version ? ` v${branding.version}` : ''} · {t('about.madeBy', { producer: PRODUCT.producer })}<br />
            <a href={PRODUCT.url} target="_blank" rel="noreferrer">{PRODUCT.website}</a> · <a href={PRODUCT.phoneHref}>{PRODUCT.phone}</a>
          </Typography.Text>
        </Space>
      </Card>
      </main>
    </div>
  )
}

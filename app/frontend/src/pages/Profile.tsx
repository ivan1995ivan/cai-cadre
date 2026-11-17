import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Card, Col, Descriptions, Form, Input, Row, Segmented, Space, Tag, Typography, message } from 'antd'

import { api, errorText, fieldErrors } from '../api/client'
import { useApp, useLocalName } from '../auth/AppContext'
import { LANG_LABELS, type Lang } from '../api/types'
import type { ButtonStyle, Density, ThemeChoice } from '../theme/themes'
import { useEditGuard } from '../components/UnsavedGuard'

export default function Profile() {
  const { t } = useTranslation()
  const { me, updateMe, themeChoice, setThemeChoice, density, setDensity, buttons, setButtons, lang, setLang, languages } = useApp()
  const localName = useLocalName()
  const [form] = Form.useForm()
  const [pwdForm] = Form.useForm()
  const [saving, setSaving] = useState(false)

  if (!me) return null

  const { touch, clean } = useEditGuard(() => save())
  const save = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await updateMe(values)
      message.success(t('common.saved'))
      clean()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      return false
    } finally {
      setSaving(false)
    }
  }

  const changePassword = async () => {
    const values = await pwdForm.validateFields()
    try {
      await api.post('/auth/change-password/', values)
      message.success(t('profile.passwordChanged'))
      pwdForm.resetFields()
    } catch (e) {
      pwdForm.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('header.profile')}</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title={t('profile.personal')} extra={<Button type="primary" onClick={save} loading={saving}>{t('common.save')}</Button>}>
            <Form form={form} layout="vertical" initialValues={me} onValuesChange={touch}>
              <Row gutter={16}>
                <Col xs={24} md={8}><Form.Item name="last_name" label={t('users.last_name')}><Input /></Form.Item></Col>
                <Col xs={24} md={8}><Form.Item name="first_name" label={t('users.first_name')}><Input /></Form.Item></Col>
                <Col xs={24} md={8}><Form.Item name="middle_name" label={t('users.middle_name')}><Input /></Form.Item></Col>
                <Col xs={24} md={12}><Form.Item name="email" label="E-mail" rules={[{ type: 'email' }]}><Input /></Form.Item></Col>
                <Col xs={24} md={12}><Form.Item name="phone" label={t('users.phone')}><Input /></Form.Item></Col>
              </Row>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={t('profile.appearance')}>
            <Space orientation="vertical" size="middle">
              <div>
                <Typography.Text type="secondary">{t('header.theme')}</Typography.Text><br />
                <Segmented<ThemeChoice> value={themeChoice || 'green'} style={{ flexWrap: 'wrap' }} onChange={setThemeChoice}
                  options={(['green', 'turquoise', 'blue', 'dark', 'onec', 'auto'] as ThemeChoice[]).map((v) => ({ value: v, label: t(`themes.${v}`) }))} />
              </div>
              <div>
                <Typography.Text type="secondary">{t('profile.density')}</Typography.Text><br />
                <Segmented<Density> value={density} onChange={setDensity}
                  options={[{ value: 'normal', label: t('density.normal') }, { value: 'compact', label: t('density.compact') }]} />
              </div>
              <div>
                <Typography.Text type="secondary">{t('profile.buttons')}</Typography.Text><br />
                <Segmented<ButtonStyle> value={buttons} onChange={setButtons}
                  options={(['2d', '3d'] as ButtonStyle[]).map((v) => ({ value: v, label: t(`buttonStyles.${v}`) }))} />
                <div style={{ marginTop: 8 }}>
                  <Space wrap>
                    <Button type="primary">{t('profile.buttonsSample')}</Button>
                    <Button>{t('common.cancel')}</Button>
                  </Space>
                </div>
              </div>
              {languages.length > 1 && <div>
                <Typography.Text type="secondary">{t('profile.language')}</Typography.Text><br />
                <Segmented<Lang> value={lang} onChange={setLang} options={languages.map((l) => ({ value: l, label: LANG_LABELS[l] }))} />
              </div>}
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card title={t('profile.access')}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label={t('users.roles')}>{me.roles.map((r) => <Tag key={r.id}>{localName(r)}</Tag>)}</Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title={t('profile.emailTitle')} style={{ marginTop: 16 }}>
            <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
              {me.email ? t('profile.emailOn', { email: me.email }) : t('profile.emailOff')}
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={t('header.changePassword')} extra={<Button onClick={changePassword}>{t('common.save')}</Button>}>
            <Form form={pwdForm} layout="vertical">
              <Form.Item name="old_password" label={t('profile.oldPassword')} rules={[{ required: true }]}>
                <Input.Password autoComplete="current-password" />
              </Form.Item>
              <Form.Item name="new_password" label={t('profile.newPassword')} extra={t('users.passwordRules')} rules={[{ required: true, min: 8 }]}>
                <Input.Password autoComplete="new-password" />
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

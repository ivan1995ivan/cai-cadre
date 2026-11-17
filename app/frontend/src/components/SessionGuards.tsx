import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Form, Input, Modal, message } from 'antd'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { api, errorText, fieldErrors } from '../api/client'
import { useApp } from '../auth/AppContext'

/** După autentificare: schimbarea obligatorie a parolei și fereastra „Ce e nou” după actualizare. */
export default function SessionGuards() {
  const { t } = useTranslation()
  const { me, branding, lang, updateMe, reloadMe } = useApp()
  const [news, setNews] = useState<string | null>(null)
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)

  const version = branding?.version
  useEffect(() => {
    if (!me || !version || me.must_change_password || me.last_seen_version === version) return
    if (!me.last_seen_version) {
      // Prima intrare: nu arătăm noutățile, doar marcăm versiunea.
      updateMe({ last_seen_version: version })
      return
    }
    api
      .get(`/help/${lang}/ce-e-nou/`)
      .then((r) => setNews(r.data.content))
      .catch(() => updateMe({ last_seen_version: version }))
  }, [me, version, lang, updateMe])

  const closeNews = () => {
    setNews(null)
    if (version) updateMe({ last_seen_version: version })
  }

  const changePassword = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await api.post('/auth/change-password/', values)
      message.success(t('profile.passwordChanged'))
      await reloadMe()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Modal open={!!me?.must_change_password} title={t('profile.mustChange')} closable={false} maskClosable={false}
        cancelButtonProps={{ style: { display: 'none' } }} okText={t('common.save')} onOk={changePassword} confirmLoading={saving}>
        <Form form={form} layout="vertical">
          <Form.Item name="old_password" label={t('profile.oldPassword')} rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item name="new_password" label={t('profile.newPassword')} extra={t('users.passwordRules')} rules={[{ required: true, min: 8 }]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
      <Modal open={!!news} title={t('whatsNew.title', { version })} onOk={closeNews} onCancel={closeNews}
        cancelButtonProps={{ style: { display: 'none' } }} okText={t('whatsNew.ok')} width={640}>
        <div className="help-article"><Markdown remarkPlugins={[remarkGfm]}>{news || ''}</Markdown></div>
      </Modal>
    </>
  )
}

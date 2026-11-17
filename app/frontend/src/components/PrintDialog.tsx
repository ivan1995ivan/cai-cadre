import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Checkbox, Form, Input, Modal, Segmented, Select, Space, Spin, Typography, message } from 'antd'
import { MailOutlined, PrinterOutlined } from '@ant-design/icons'

import { api, errorText } from '../api/client'
import type { PrintTemplate } from '../api/crm'
import { useApp } from '../auth/AppContext'
import PrintFrame, { type PrintFrameHandle } from './PrintFrame'

/**
 * Dialogul de tipărire: alegerea șablonului, a limbii și a opțiunilor (cu/fără poze, coduri etc.),
 * previzualizare și tipărire prin dialogul browserului (de acolo și „Salvează ca PDF”). Cu `canSend`, documentul se poate
 * trimite și pe e-mail (/print/send/: adresa clientului și subiectul propuse; pleacă cu șablonul, limba și bifele alese).
 * Previzualizarea se cere cu `preview=1` (documentele înregistrate, ca adeverințele, nu iau încă număr); la „Tipărește” și
 * la trimitere se ia documentul final — abia atunci se înregistrează.
 */
export default function PrintDialog({ open, onClose, docType, url, params, optionKeys, title, canSend }: {
  open: boolean
  onClose: () => void
  docType: string
  url: string
  params: Record<string, unknown>
  optionKeys: string[]
  title: string
  canSend?: boolean
}) {
  const { t } = useTranslation()
  const { lang: uiLang } = useApp()
  const [templates, setTemplates] = useState<PrintTemplate[]>([])
  const [templateId, setTemplateId] = useState<number>()
  const [lang, setLang] = useState(uiLang)
  const [options, setOptions] = useState<Record<string, boolean>>({})
  const [html, setHtml] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const frame = useRef<PrintFrameHandle>(null)

  useEffect(() => {
    if (!open) return
    api.get<PrintTemplate[]>('/print-templates/', { params: { doc_type: docType } }).then((r) => {
      const active = r.data.filter((x) => x.is_active)
      setTemplates(active)
      const tpl = active.find((x) => x.is_default) ?? active[0]
      setTemplateId(tpl?.id)
      setOptions(tpl?.default_options ?? {})
    })
  }, [open, docType])

  const pickTemplate = (id: number) => {
    setTemplateId(id)
    setOptions(templates.find((x) => x.id === id)?.default_options ?? {})
  }

  const key = JSON.stringify({ templateId, lang, options, params })
  useEffect(() => {
    if (!open || !templateId) return
    setLoading(true)
    setError('')
    const flags = Object.fromEntries(optionKeys.map((k) => [k, options[k] ? 1 : 0]))
    api.get<string>(url, { params: { ...params, ...flags, template: templateId, lang, preview: 1 }, responseType: 'text' })
      .then((r) => setHtml(r.data))
      .catch((e) => setError(errorText(e)))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, key])

  const [mailForm] = Form.useForm()
  const [mailOpen, setMailOpen] = useState(false)
  const [sending, setSending] = useState(false)
  const docParams = () => ({ ...params, ...Object.fromEntries(optionKeys.map((k) => [k, options[k] ? 1 : 0])), template: templateId, lang })
  const [printing, setPrinting] = useState(false)
  const printFinal = async () => {
    setPrinting(true)
    try {
      const r = await api.get<string>(url, { params: docParams(), responseType: 'text' })
      frame.current?.print(r.data) // previzualizarea rămâne; fiecare tipărire e documentul final (înregistrat)
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setPrinting(false)
    }
  }
  const openMail = async () => {
    try {
      const { data } = await api.get('/print/send/', { params: { path: url, ...docParams() } })
      mailForm.setFieldsValue(data)
      setMailOpen(true)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const sendMail = async () => {
    const values = await mailForm.validateFields()
    setSending(true)
    try {
      const { data } = await api.post('/print/send/', { ...values, path: url, params: docParams() })
      message.success(t('print.emailSent', { to: data.to }))
      setMailOpen(false)
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setSending(false)
    }
  }

  return (
    <Modal open={open} onCancel={onClose} width={1000} title={title} destroyOnHidden
      footer={[
        <Button key="close" onClick={onClose}>{t('common.close')}</Button>,
        ...(canSend ? [
          <Button key="mail" icon={<MailOutlined />} disabled={!html || loading} onClick={openMail}>{t('print.sendEmail')}</Button>,
        ] : []),
        <Button key="print" type="primary" icon={<PrinterOutlined />} disabled={!html || loading} loading={printing} onClick={printFinal}>
          {t('print.print')}
        </Button>,
      ]}>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select style={{ minWidth: 260 }} value={templateId} onChange={pickTemplate}
          options={templates.map((x) => ({ value: x.id, label: x.name }))} placeholder={t('print.template')} />
        <Segmented value={lang} onChange={(v) => setLang(v as typeof lang)} options={[{ value: 'ro', label: 'RO' }, { value: 'ru', label: 'RU' }, { value: 'en', label: 'EN' }]} />
        {optionKeys.map((k) => (
          <Checkbox key={k} checked={!!options[k]} onChange={(e) => setOptions((o) => ({ ...o, [k]: e.target.checked }))}>
            {t(`print.options.${k}`)}
          </Checkbox>
        ))}
      </Space>
      {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 12 }} />}
      {!templates.length && <Alert type="warning" showIcon title={t('print.noTemplates')} />}
      <Spin spinning={loading}>
        <PrintFrame ref={frame} html={html} height="65vh" />
      </Spin>
      {canSend && (
        <Modal open={mailOpen} onCancel={() => setMailOpen(false)} onOk={sendMail} confirmLoading={sending}
          okText={t('print.send')} okButtonProps={{ icon: <MailOutlined /> }} title={`${t('print.sendEmail')}: ${title}`} destroyOnHidden>
          <Form form={mailForm} layout="vertical">
            <Form.Item name="to" label={t('print.emailTo')} rules={[{ required: true, type: 'email', message: t('common.required') }]}>
              <Input type="email" autoComplete="off" />
            </Form.Item>
            <Form.Item name="subject" label={t('print.emailSubject')}><Input /></Form.Item>
            <Form.Item name="message" label={t('print.emailMessage')}><Input.TextArea rows={4} /></Form.Item>
            <Form.Item name="format" label={t('print.emailFormat')}>
              <Segmented options={[{ value: 'html', label: t('print.formats.html') }, { value: 'doc', label: t('print.formats.doc') }]} />
            </Form.Item>
          </Form>
          <Typography.Text type="secondary">{t('print.emailHint')}</Typography.Text>
        </Modal>
      )}
    </Modal>
  )
}

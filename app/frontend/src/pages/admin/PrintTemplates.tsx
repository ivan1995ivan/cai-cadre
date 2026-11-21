import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert, Button, Card, Col, Collapse, Empty, Input, List, Popconfirm, Row, Segmented, Select, Space, Switch, Tabs, Tag,
  Typography, message,
} from 'antd'
import { CopyOutlined, PrinterOutlined, UndoOutlined } from '@ant-design/icons'

import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { PrintTemplate } from '../../api/crm'
import { useApp } from '../../auth/AppContext'
import PrintFrame, { type PrintFrameHandle } from '../../components/PrintFrame'
import ColumnsEditor, { useColumnFields } from './ColumnsEditor'
import { useUnsavedGuard } from '../../components/UnsavedGuard'

interface DocType { code: string; name: string; ready: boolean }

/** Datele întreprinderii (din Constante), aceleași în toate formele; datele documentului — în formele livrate. */
const COMPANY_VARIABLES = `{% company_header %}  — antetul: logo-ul, denumirea, IDNO, CAEM, adresa, contactele, contul bancar implicit
company.full_name (cu forma juridică), company.name, company.legal_form, company.idno, company.caem
company.address, company.postal_address, company.phone, company.email, company.website
company.logo, company.stamp, company.signature  (imaginile din Constante, puse în pagină)
company.director / director_position, company.chief_accountant / chief_accountant_position,
company.hr_head / hr_head_position  (numele și funcțiile semnatarilor, în limba formei)
company.bank.iban / bank / bic (contul implicit), company.bank_accounts[ ].iban / bank / bic / currency
lang, today, texts.<cheie> (fila „Simplu”), options.<opțiune>, style.show_logo
Filtre: {{ valoare|money }}  {{ valoare|money:0 }}  {{ cantitate|qty }}`

const mono: React.CSSProperties = { fontFamily: 'Consolas, "Courier New", monospace', fontSize: 12.5 }

export default function PrintTemplates() {
  const { t } = useTranslation()
  const { hasPerm, languages } = useApp()
  const canEdit = hasPerm('settings.edit')
  const docTypes = useFetch<DocType[]>('/print-templates/doc-types/')
  const [docType, setDocType] = useState('order')
  const { data: templates, reload } = useFetch<PrintTemplate[]>('/print-templates/', { doc_type: docType })
  const [current, setCurrent] = useState<PrintTemplate | null>(null)
  const [draft, setDraft] = useState<PrintTemplate | null>(null)
  const [preview, setPreview] = useState('')
  const [previewError, setPreviewError] = useState('')
  const [lang, setLang] = useState<'ro' | 'ru'>('ro')
  const frame = useRef<PrintFrameHandle>(null)
  const ready = docTypes.data?.find((d) => d.code === docType)?.ready
  const fieldsInfo = useColumnFields(docType)

  useEffect(() => {
    if (!templates) return
    const keep = templates.find((x) => x.id === current?.id) ?? templates[0] ?? null
    setCurrent(keep)
    setDraft(keep ? { ...keep } : null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templates])

  // Previzualizare cu întârziere, ca să nu se trimită la fiecare tastă.
  useEffect(() => {
    if (!draft || !ready || !canEdit) return
    const timer = setTimeout(() => {
      api.post<string>('/print/preview/', { doc_type: docType, body: draft.body, css: draft.css, orientation: draft.orientation,
        options: draft.default_options, texts: draft.texts, style: draft.style, columns: draft.columns ?? [], lang }, { responseType: 'text' })
        .then((r) => { setPreview(r.data); setPreviewError('') })
        .catch((e) => setPreviewError(errorText(e)))
    }, 500)
    return () => clearTimeout(timer)
  }, [draft, docType, lang, ready, canEdit])

  const save = async () => {
    if (!draft) return
    try {
      await api.patch(`/print-templates/${draft.id}/`, {
        name: draft.name, body: draft.body, css: draft.css, orientation: draft.orientation,
        default_options: draft.default_options, texts: draft.texts ?? {}, style: draft.style ?? {}, columns: draft.columns ?? [], is_default: draft.is_default,
        is_active: draft.is_active,
      })
      message.success(t('common.saved'))
      await reload()
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }

  const action = async (name: 'restore' | 'duplicate') => {
    try {
      const { data } = await api.post<PrintTemplate>(`/print-templates/${draft!.id}/${name}/`)
      setCurrent(data)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const remove = async () => {
    try {
      await api.delete(`/print-templates/${draft!.id}/`)
      setCurrent(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const dirty = draft && current && (draft.body !== current.body || draft.css !== current.css || draft.name !== current.name
    || draft.is_default !== current.is_default || draft.is_active !== current.is_active || draft.orientation !== current.orientation
    || JSON.stringify(draft.default_options) !== JSON.stringify(current.default_options)
    || JSON.stringify(draft.texts ?? {}) !== JSON.stringify(current.texts ?? {}) || JSON.stringify(draft.style ?? {}) !== JSON.stringify(current.style ?? {})
    || JSON.stringify(draft.columns ?? []) !== JSON.stringify(current.columns ?? []))
  useUnsavedGuard(!!dirty && canEdit, () => save())
  const setText = (l: 'ro' | 'ru', key: string, value: string) => draft && setDraft({
    ...draft, texts: { ...(draft.texts ?? {}), [l]: { ...((draft.texts ?? {})[l] ?? {}), [key]: value } },
  })

  const optionKeys = Object.keys(draft?.default_options ?? {})

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.printTemplates')}</Typography.Title>
      <Typography.Paragraph type="secondary">{t('print.editorHint')}</Typography.Paragraph>
      <Row gutter={16}>
        <Col xs={24} lg={6}>
          <Card size="small">
            <Select style={{ width: '100%', marginBottom: 12 }} value={docType} onChange={setDocType}
              options={(docTypes.data ?? []).map((d) => ({ value: d.code, label: `${t(`print.docTypes.${d.code}`)}${d.ready ? '' : ` — ${t('common.soon')}`}` }))} />
            <List size="small" dataSource={templates ?? []} locale={{ emptyText: t('print.noTemplates') }}
              renderItem={(tpl) => (
                <List.Item onClick={() => { setCurrent(tpl); setDraft({ ...tpl }) }} style={{
                  cursor: 'pointer', paddingInline: 8, borderRadius: 6, background: current?.id === tpl.id ? 'var(--ant-color-primary-bg)' : undefined,
                }}>
                  <Space orientation="vertical" size={0}>
                    <Typography.Text strong>{tpl.name}</Typography.Text>
                    <Space size={4}>
                      {tpl.is_default && <Tag color="green">{t('currencies.default')}</Tag>}
                      {tpl.is_system && <Tag>{t('print.system')}</Tag>}
                      {tpl.modified && <Tag color="orange">{t('print.modified')}</Tag>}
                      {!tpl.is_active && <Tag>{t('catalog.inactive')}</Tag>}
                    </Space>
                  </Space>
                </List.Item>
              )} />
          </Card>
        </Col>
        <Col xs={24} lg={18}>
          {!draft ? <Card><Empty description={ready ? t('print.pickTemplate') : t('print.notReady')} /></Card> : (
            <Card size="small"
              title={<Input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} disabled={!canEdit} style={{ maxWidth: 360 }} />}
              extra={canEdit && (
                <Space wrap>
                  {draft.is_system && draft.modified && (
                    <Popconfirm title={t('print.restoreConfirm')} onConfirm={() => action('restore')}><Button icon={<UndoOutlined />}>{t('print.restore')}</Button></Popconfirm>
                  )}
                  <Button icon={<CopyOutlined />} onClick={() => action('duplicate')}>{t('print.duplicate')}</Button>
                  {!draft.is_system && <Popconfirm title={t('common.confirmDelete')} onConfirm={remove}><Button danger>{t('common.delete')}</Button></Popconfirm>}
                  <Button type="primary" disabled={!dirty} onClick={save}>{t('common.save')}</Button>
                </Space>
              )}>
              <Space wrap style={{ marginBottom: 12 }}>
                <Space><Switch size="small" checked={draft.is_default} disabled={!canEdit} onChange={(v) => setDraft({ ...draft, is_default: v })} />{t('currencies.default')}</Space>
                <Space><Switch size="small" checked={draft.is_active} disabled={!canEdit} onChange={(v) => setDraft({ ...draft, is_active: v })} />{t('users.active')}</Space>
                <Segmented size="small" value={draft.orientation} disabled={!canEdit} onChange={(v) => setDraft({ ...draft, orientation: v as PrintTemplate['orientation'] })}
                  options={[{ value: 'portrait', label: t('print.portrait') }, { value: 'landscape', label: t('print.landscape') }]} />
                {optionKeys.map((k) => (
                  <Space key={k}>
                    <Switch size="small" checked={!!draft.default_options[k]} disabled={!canEdit}
                      onChange={(v) => setDraft({ ...draft, default_options: { ...draft.default_options, [k]: v } })} />
                    {t(`print.options.${k}`)}
                  </Space>
                ))}
              </Space>
              <Row gutter={12}>
                <Col xs={24} xl={12}>
                  <Tabs size="small" items={[
                    {
                      key: 'simple', label: t('print.simple'),
                      children: (
                        <Space orientation="vertical" style={{ width: '100%' }}>
                          <Space wrap>
                            <Typography.Text>{t('print.fontSize')}</Typography.Text>
                            <Segmented size="small" disabled={!canEdit} value={draft.style?.font_size ?? 'normal'}
                              onChange={(v) => setDraft({ ...draft, style: { ...(draft.style ?? {}), font_size: v as 'small' | 'normal' | 'large' } })}
                              options={(['small', 'normal', 'large'] as const).map((k) => ({ value: k, label: t(`print.fonts.${k}`) }))} />
                            <Switch size="small" disabled={!canEdit} checked={draft.style?.show_logo !== false}
                              onChange={(v) => setDraft({ ...draft, style: { ...(draft.style ?? {}), show_logo: v } })} />
                            <Typography.Text>{t('print.showLogo')}</Typography.Text>
                          </Space>
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('print.logoHint')}</Typography.Text>
                          {(draft.text_fields ?? []).length > 0 && <>
                            <Typography.Text strong>{t('print.texts')}</Typography.Text>
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('print.textsHint')}</Typography.Text>
                            {(draft.placeholders ?? []).length > 0 && (
                              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                                {t('printColumns.placeholders')} {(draft.placeholders ?? []).map((p) => <Tag key={p} style={{ marginInlineEnd: 4 }}>{`{${p}}`}</Tag>)}
                              </Typography.Text>
                            )}
                            {(draft.text_fields ?? []).map((f) => (
                              <Row key={f.key} gutter={8}>
                                <Col span={24}><Typography.Text>{f.label}</Typography.Text></Col>
                                {(['ro', 'ru'] as const).filter((l) => languages.includes(l)).map((l) => {
                                  const Field = f.multiline ? Input.TextArea : Input
                                  return (
                                    <Col key={l} xs={24} md={12}>
                                      <Field disabled={!canEdit} value={(draft.texts ?? {})[l]?.[f.key] ?? ''} placeholder={f[l] || l.toUpperCase()}
                                        addonBefore={f.multiline ? undefined : l.toUpperCase()} rows={f.multiline ? 2 : undefined}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setText(l, f.key, e.target.value)} />
                                    </Col>
                                  )
                                })}
                              </Row>
                            ))}
                          </>}
                        </Space>
                      ),
                    },
                    ...(fieldsInfo?.supports_columns ? [{
                      key: 'columns', label: t('printColumns.tab'),
                      children: <ColumnsEditor value={draft.columns ?? []} info={fieldsInfo} disabled={!canEdit}
                        onChange={(columns) => setDraft({ ...draft, columns })} />,
                    }] : []),
                    {
                      key: 'html', label: `${t('print.advanced')} — HTML`,
                      children: <Input.TextArea value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                        readOnly={!canEdit} spellCheck={false} style={{ ...mono, height: '58vh' }} />,
                    },
                    {
                      key: 'css', label: 'CSS',
                      children: <Input.TextArea value={draft.css} onChange={(e) => setDraft({ ...draft, css: e.target.value })}
                        readOnly={!canEdit} spellCheck={false} style={{ ...mono, height: '58vh' }} placeholder={t('print.cssHint')} />,
                    },
                  ]} />
                  <Collapse size="small" items={[{
                    key: 'vars', label: t('print.variables'),
                    children: <pre style={{ ...mono, whiteSpace: 'pre-wrap', margin: 0 }}>{COMPANY_VARIABLES}</pre>,
                  }]} />
                </Col>
                <Col xs={24} xl={12}>
                  <Space style={{ marginBottom: 8 }}>
                    <Typography.Text strong>{t('print.preview')}</Typography.Text>
                    {languages.includes('ru') && <Segmented size="small" value={lang} onChange={(v) => setLang(v as 'ro' | 'ru')} options={['ro', 'ru']} />}
                    <Button size="small" icon={<PrinterOutlined />} onClick={() => frame.current?.print()} disabled={!preview}>{t('print.print')}</Button>
                  </Space>
                  {previewError && <Alert type="error" showIcon title={previewError} style={{ marginBottom: 8 }} />}
                  <PrintFrame ref={frame} html={preview} height="62vh" />
                </Col>
              </Row>
            </Card>
          )}
        </Col>
      </Row>
    </Space>
  )
}

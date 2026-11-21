import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Checkbox, Button, Card, Col, ColorPicker, Divider, Form, Input, Modal, Popconfirm, Row, Select, Space, Switch, Tabs, Tag, Typography, Upload, message,
} from 'antd'
import Table from '../../components/AppTable'
import { DeleteOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons'

import { api, errorText, fieldErrors } from '../../api/client'
import { LANG_LABELS, type BankAccount, type Company, type Currency } from '../../api/types'
import BankInput, { applyBank, IbanInput } from '../../components/BankInput'
import { useApp } from '../../auth/AppContext'
import { PALETTES, type ThemeName } from '../../theme/themes'
import { ThemePicker } from '../setup/SetupWizard'
import FormLayout from '../../components/FormLayout'
import { useEditGuard } from '../../components/UnsavedGuard'

const IMAGE_FIELDS = ['logo', 'logo_small', 'logo_dark', 'signature', 'stamp'] as const
type ImageField = (typeof IMAGE_FIELDS)[number]

export default function Constants() {
  const { t } = useTranslation()
  const { hasPerm, reloadBranding, reloadMe, languages } = useApp()
  const canEdit = hasPerm('settings.edit')
  const { touch, clean } = useEditGuard(() => save(), canEdit)
  const [company, setCompany] = useState<Company | null>(null)
  const [currencies, setCurrencies] = useState<Currency[]>([])
  const [saving, setSaving] = useState(false)
  const [bank, setBank] = useState<Partial<BankAccount> | null>(null)
  const [form] = Form.useForm()
  const [bankForm] = Form.useForm()

  const load = useCallback(async () => {
    const { data } = await api.get<Company>('/company/')
    setCompany(data)
    form.setFieldsValue(data)
  }, [form])

  useEffect(() => {
    load()
    api.get<Currency[]>('/currencies/').then((r) => setCurrencies(r.data))
  }, [load])

  const save = async () => {
    const values = await form.validateFields()
    if (values.primary_color && typeof values.primary_color !== 'string') {
      values.primary_color = values.primary_color.toHexString().toUpperCase()
    }
    IMAGE_FIELDS.forEach((f) => delete values[f])
    setSaving(true)
    try {
      const { data } = await api.patch<Company>('/company/', values)
      setCompany(data)
      message.success(t('common.saved'))
      clean()
      reloadBranding()
      reloadMe()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
      return false
    } finally {
      setSaving(false)
    }
  }

  const uploadImage = async (field: ImageField, file: File | null) => {
    const body = new FormData()
    body.append(field, file ?? '')
    try {
      const { data } = await api.patch<Company>('/company/', body)
      setCompany(data)
      message.success(t('common.saved'))
      reloadBranding()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const saveBank = async () => {
    const values = await bankForm.validateFields()
    try {
      if (bank?.id) await api.patch(`/bank-accounts/${bank.id}/`, values)
      else await api.post('/bank-accounts/', values)
      setBank(null)
      load()
    } catch (e) {
      bankForm.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  const deleteBank = async (id: number) => {
    await api.delete(`/bank-accounts/${id}/`)
    load()
  }

  if (!company) return null

  const imageCard = (field: ImageField) => {
    const url = company[field]
    const isLogo = field.startsWith('logo')
    return (
      <Card size="small" title={t(`constants.images.${field}`)} key={field}
        extra={canEdit && url && (
          <Popconfirm title={t('common.confirmDelete')} onConfirm={() => uploadImage(field, null)}>
            <Button size="small" type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        )}>
        <Space orientation="vertical" style={{ width: '100%' }}>
          {url ? (
            isLogo ? (
              <Row gutter={8}>
                {(Object.keys(PALETTES) as ThemeName[])
                  .filter((name) => (field === 'logo_dark' ? PALETTES[name].dark : true))
                  .map((name) => (
                    <Col span={field === 'logo_dark' ? 24 : 6} key={name}>
                      <div title={t(`themes.${name}`)} style={{
                        background: PALETTES[name].dark ? PALETTES[name].siderBg : '#fff', borderRadius: 6, padding: 8,
                        height: 64, display: 'grid', placeItems: 'center', border: `2px solid ${PALETTES[name].primary}`,
                      }}>
                        <img src={(PALETTES[name].dark && company.logo_dark) || url} alt="" style={{ maxHeight: 44, maxWidth: '100%' }} />
                      </div>
                    </Col>
                  ))}
              </Row>
            ) : (
              <img src={url} alt="" style={{ maxHeight: 80, maxWidth: '100%' }} />
            )
          ) : (
            <Typography.Text type="secondary">{t('constants.images.empty')}</Typography.Text>
          )}
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t(`constants.images.${field}Hint`)}</Typography.Text>
          {canEdit && (
            <Upload accept=".png,.jpg,.jpeg,.svg,.webp" showUploadList={false}
              beforeUpload={(file) => { uploadImage(field, file); return false }}>
              <Button icon={<UploadOutlined />}>{url ? t('constants.images.replace') : t('constants.images.upload')}</Button>
            </Upload>
          )}
        </Space>
      </Card>
    )
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.constants')}</Typography.Title>
        {canEdit && <Button type="primary" onClick={save} loading={saving}>{t('common.save')}</Button>}
      </Space>
      <Form form={form} layout="vertical" disabled={!canEdit} onValuesChange={touch}>
        <Tabs
          items={[
            {
              key: 'company', label: t('constants.tabs.company'), forceRender: true,
              children: (
                <Card>
                  <Typography.Paragraph type="secondary">{t('constants.companyHint')}</Typography.Paragraph>
                  <FormLayout formKey="constants-company"><Row gutter={16}>
                    <Divider titlePlacement="start" style={{ marginTop: 0 }}>{t('constants.sections.identity')}</Divider>
                    <Col xs={24} md={12}>
                      <Form.Item name="name_ro" label={t('constants.name_ro')} rules={[{ required: true, message: t('common.required') }]}
                        extra={t('constants.nameHint')}><Input placeholder={t('constants.namePlaceholder')} /></Form.Item>
                    </Col>
                    {languages.includes('ru') && <Col xs={24} md={12}><Form.Item name="name_ru" label={t('constants.name_ru')}><Input /></Form.Item></Col>}
                    {languages.includes('en') && <Col xs={24} md={12}><Form.Item name="name_en" label={t('constants.name_en')}><Input /></Form.Item></Col>}
                    <Col xs={8} md={4}><Form.Item name="legal_form" label={t('constants.legal_form')}><Input placeholder="SRL" /></Form.Item></Col>
                    <Col xs={16} md={6}>
                      <Form.Item name="idno" label="IDNO" rules={[{ pattern: /^\d{13}$/, message: t('constants.idnoHint') }]}><Input maxLength={13} /></Form.Item>
                    </Col>
                    <Col xs={24} md={6}>
                      <Form.Item name="caem" label={t('constants.caem')} extra={t('constants.caemHint')}
                        rules={[{ pattern: /^\d{2}\.?\d{2}$/, message: t('constants.caemHint') }]}><Input maxLength={5} placeholder="6201" /></Form.Item>
                    </Col>
                    <Divider titlePlacement="start">{t('constants.sections.contacts')}</Divider>
                    <Col xs={24} md={12}><Form.Item name="legal_address" label={t('constants.legal_address')}><Input /></Form.Item></Col>
                    <Col xs={24} md={12}><Form.Item name="postal_address" label={t('constants.postal_address')}><Input /></Form.Item></Col>
                    <Col xs={24} md={8}><Form.Item name="phone" label={t('constants.phone')}><Input /></Form.Item></Col>
                    <Col xs={24} md={8}><Form.Item name="email" label="E-mail" rules={[{ type: 'email' }]}><Input /></Form.Item></Col>
                    <Col xs={24} md={8}><Form.Item name="website" label={t('constants.website')}><Input /></Form.Item></Col>
                    <Divider titlePlacement="start">{t('constants.sections.signers')}</Divider>
                    <Col xs={24}><Typography.Text type="secondary">{t('constants.signersHint')}</Typography.Text></Col>
                    <Col xs={24} md={8}><Form.Item name="director" label={t('constants.director')}><Input /></Form.Item></Col>
                    <Col xs={24} md={8}><Form.Item name="director_position_ro" label={t('constants.position_ro')}><Input placeholder="Director" /></Form.Item></Col>
                    {languages.includes('ru') && <Col xs={24} md={8}><Form.Item name="director_position_ru" label={t('constants.position_ru')}><Input placeholder="Директор" /></Form.Item></Col>}
                    <Col xs={24} md={8}><Form.Item name="chief_accountant" label={t('constants.chief_accountant')}><Input /></Form.Item></Col>
                    <Col xs={24} md={8}><Form.Item name="chief_accountant_position_ro" label={t('constants.position_ro')}><Input placeholder="Contabil-șef" /></Form.Item></Col>
                    {languages.includes('ru') && <Col xs={24} md={8}><Form.Item name="chief_accountant_position_ru" label={t('constants.position_ru')}><Input placeholder="Главный бухгалтер" /></Form.Item></Col>}
                    <Col xs={24} md={8}><Form.Item name="hr_head" label={t('constants.hr_head')}><Input /></Form.Item></Col>
                    <Col xs={24} md={8}><Form.Item name="hr_head_position_ro" label={t('constants.position_ro')}><Input placeholder="Șef resurse umane" /></Form.Item></Col>
                    {languages.includes('ru') && <Col xs={24} md={8}><Form.Item name="hr_head_position_ru" label={t('constants.position_ru')}><Input placeholder="Начальник отдела кадров" /></Form.Item></Col>}
                  </Row></FormLayout>
                </Card>
              ),
            },
            {
              key: 'images', label: t('constants.tabs.images'), forceRender: true,
              children: (
                <Row gutter={[16, 16]}>
                  {IMAGE_FIELDS.map((f) => <Col xs={24} md={12} xl={8} key={f}>{imageCard(f)}</Col>)}
                </Row>
              ),
            },
            {
              key: 'bank', label: t('constants.tabs.bank'),
              children: (
                <Card extra={canEdit && <Button icon={<PlusOutlined />} onClick={() => { setBank({ currency: 'MDL' }); bankForm.resetFields(); bankForm.setFieldsValue({ currency: 'MDL' }) }}>{t('common.add')}</Button>}>
                  <Table<BankAccount> rowKey="id" pagination={false} dataSource={company.bank_accounts} size="small"
                    columns={[
                      { title: 'IBAN', dataIndex: 'iban', render: (v, b) => <a onClick={() => { setBank(b); bankForm.setFieldsValue(b) }}>{v}</a> },
                      { title: t('constants.bank'), dataIndex: 'bank_name' },
                      { title: 'BIC', dataIndex: 'bic' },
                      { title: t('constants.currency'), dataIndex: 'currency' },
                      { title: '', dataIndex: 'is_default', render: (v) => v && <Tag color="green">{t('constants.defaultAccount')}</Tag> },
                      {
                        title: '', key: 'del', width: 50,
                        render: (_, b) => canEdit && (
                          <Popconfirm title={t('common.confirmDelete')} onConfirm={() => deleteBank(b.id)}>
                            <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                          </Popconfirm>
                        ),
                      },
                    ]} />
                </Card>
              ),
            },
            {
              key: 'modules', label: t('constants.tabs.modules'), forceRender: true,
              children: (
                <Card>
                  <Form.Item name="payroll_enabled" label={t('constants.payroll_enabled')} valuePropName="checked"
                    extra={t('constants.payroll_enabledHint')}>
                    <Switch checkedChildren={t('constants.withPayroll')} unCheckedChildren={t('constants.withoutPayroll')} />
                  </Form.Item>
                  <Form.Item name="military_enabled" label={t('constants.military_enabled')} valuePropName="checked"
                    extra={t('constants.military_enabledHint')}>
                    <Switch />
                  </Form.Item>
                  <Form.Item name="function_panel" label={t('constants.function_panel')} valuePropName="checked"
                    extra={t('constants.function_panelHint')}>
                    <Switch />
                  </Form.Item>
                  <Form.Item name="languages" label={t('constants.languages')} extra={t('constants.languagesHint')}
                    rules={[{ type: 'array', min: 1, message: t('constants.languagesMin') }]}>
                    <Checkbox.Group options={(['ro', 'ru', 'en'] as const).map((l) => ({ value: l, label: LANG_LABELS[l] }))} />
                  </Form.Item>
                </Card>
              ),
            },
            {
              key: 'theme', label: t('constants.tabs.theme'), forceRender: true,
              children: (
                <Card>
                  <Form.Item name="default_theme" label={t('constants.default_theme')} extra={t('constants.default_themeHint')}>
                    <ThemePicker />
                  </Form.Item>
                  <Form.Item name="primary_color" label={t('constants.primary_color')} extra={t('constants.primary_colorHint')}>
                    <ColorPicker allowClear format="hex" disabledAlpha
                      presets={[{ label: t('constants.presets'), colors: ['#1FA463', '#07BCCB', '#1E6FD9', '#2E9E5B', '#D9480F', '#7048E8'] }]}
                      onClear={() => form.setFieldValue('primary_color', '')} />
                  </Form.Item>
                </Card>
              ),
            },
          ]}
        />
      </Form>

      <Modal open={!!bank} title={bank?.id ? t('constants.editAccount') : t('constants.newAccount')} onOk={saveBank} onCancel={() => setBank(null)}>
        <Form form={bankForm} layout="vertical">
          <Form.Item name="iban" label="IBAN" rules={[{ required: true }]} extra={t('banks.pickHint')}><IbanInput form={bankForm} /></Form.Item>
          <Form.Item name="bank_name" label={t('constants.bank')} rules={[{ required: true }]}>
            <BankInput onPick={(b) => applyBank(bankForm, b)} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="bic" label="BIC"><Input /></Form.Item></Col>
            <Col span={12}>
              <Form.Item name="currency" label={t('constants.currency')}>
                <Select options={currencies.map((c) => ({ value: c.code, label: c.code }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="is_default" valuePropName="checked"><Switch /></Form.Item>
          <Typography.Text type="secondary">{t('constants.defaultAccount')}</Typography.Text>
        </Form>
      </Modal>
    </Space>
  )
}

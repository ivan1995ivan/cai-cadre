import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert, Button, Card, Checkbox, Col, Collapse, Form, Input, InputNumber, Radio, Result, Row, Space, Spin, Steps,
  Tag, Typography, message,
} from 'antd'
import {
  CheckCircleFilled, CloseCircleFilled, CloudServerOutlined, DatabaseOutlined, DesktopOutlined,
} from '@ant-design/icons'
import axios from 'axios'

import { errorText, fieldErrors } from '../../api/client'
import { useApp } from '../../auth/AppContext'
import { PALETTES, type ThemeName } from '../../theme/themes'
import type { Lang } from '../../api/types'

interface Driver {
  code: string
  label: string
  default_port: number | null
  available: boolean
  odbc?: string
  install_url?: string
}

interface Probe {
  server_ok: boolean
  database_exists: boolean
  has_crm: boolean
  unfinished?: boolean
  other_product?: boolean
  table_count: number
  version: string
  error: string
}

interface DbForm {
  engine: string
  host?: string
  port?: number | null
  name?: string
  user?: string
  password?: string
}

const setup = axios.create({ baseURL: '/api/setup' })

export default function SetupWizard() {
  const { t } = useTranslation()
  const { lang, setLang, setThemeChoice } = useApp()
  const [step, setStep] = useState(0)
  const [drivers, setDrivers] = useState<Driver[]>([])
  const [db, setDb] = useState<DbForm>({ engine: 'sqlite', name: 'crm.sqlite3' })
  const [probe, setProbe] = useState<Probe | null>(null)
  const [testing, setTesting] = useState(false)
  const [creating, setCreating] = useState(false)
  const [mode, setMode] = useState<'new' | 'existing'>('new')
  const [installing, setInstalling] = useState(false)
  const [installLog, setInstallLog] = useState('')
  const [installError, setInstallError] = useState('')
  const [done, setDone] = useState(false)
  const [demo, setDemo] = useState(false)
  const probeSeq = useRef(0) // ignoră răspunsurile întârziate ale unui test vechi
  const [dbForm] = Form.useForm<DbForm>()
  const [adminDbForm] = Form.useForm<{ admin_user: string; admin_password: string }>()
  const [companyForm] = Form.useForm()
  const [adminForm] = Form.useForm()

  useEffect(() => {
    setup.get<Driver[]>('/drivers/').then((r) => setDrivers(r.data))
  }, [])

  const engine = drivers.find((d) => d.code === db.engine)
  const isSqlite = db.engine === 'sqlite'

  const chooseEngine = (code: string) => {
    const driver = drivers.find((d) => d.code === code)
    const next: DbForm = code === 'sqlite'
      ? { engine: code, name: 'crm.sqlite3' }
      : { engine: code, host: 'localhost', port: driver?.default_port ?? null, name: 'crm', user: '' }
    setDb(next)
    dbForm.setFieldsValue({ host: undefined, port: undefined, name: undefined, user: undefined, password: undefined, ...next })
    probeSeq.current += 1
    setTesting(false)
    setProbe(null)
  }

  const testConnection = async () => {
    const values = await dbForm.validateFields()
    const payload = { ...db, ...values, engine: db.engine }
    setDb(payload)
    const seq = ++probeSeq.current
    setTesting(true)
    setProbe(null)
    try {
      const { data } = await setup.post<Probe>('/test/', payload)
      if (seq !== probeSeq.current) return
      setProbe(data)
      setMode(data.has_crm && !data.unfinished ? 'existing' : 'new')
    } catch (e) {
      if (seq !== probeSeq.current) return
      dbForm.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    } finally {
      if (seq === probeSeq.current) setTesting(false)
    }
  }

  const createDatabase = async () => {
    const admin = adminDbForm.getFieldsValue()
    setCreating(true)
    try {
      const { data } = await setup.post('/create-db/', { db, ...admin })
      message.success(data.message)
      setProbe(data.probe)
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setCreating(false)
    }
  }

  const connectionReady = !!probe && probe.server_ok && (isSqlite || probe.database_exists) && !probe.other_product
  const foreignTables = !!probe && !probe.has_crm && probe.table_count > 0

  const install = async () => {
    setInstalling(true)
    setInstallError('')
    setInstallLog('')
    const payload: Record<string, unknown> = { db, mode, language: lang }
    if (mode === 'new') {
      const company = companyForm.getFieldsValue(true)
      payload.company = {
        ...company,
        bank: company.iban ? { iban: company.iban, bank_name: company.bank_name, bic: company.bic } : undefined,
      }
      payload.admin = adminForm.getFieldsValue(true)
      payload.demo = demo
    }
    try {
      const { data } = await setup.post('/install/', payload, { timeout: 30 * 60 * 1000 })
      setInstallLog(data.log)
      setDone(true)
      waitForRestart()
    } catch (e) {
      setInstallError(errorText(e))
      const log = (e as { response?: { data?: { log?: string } } }).response?.data?.log
      if (log) setInstallLog(log)
    } finally {
      setInstalling(false)
    }
  }

  const waitForRestart = () => {
    const started = Date.now()
    const poll = async () => {
      try {
        const { data } = await setup.get('/status/')
        if (data.installed) {
          window.location.href = '/'
          return
        }
      } catch {
        /* serverul repornește */
      }
      if (Date.now() - started < 120000) setTimeout(poll, 1500)
    }
    setTimeout(poll, 2000)
  }

  const steps = useMemo(() => {
    const list = [
      { key: 'lang', title: t('setup.steps.language') },
      { key: 'engine', title: t('setup.steps.engine') },
      { key: 'connection', title: t('setup.steps.connection') },
    ]
    if (mode === 'new') {
      list.push({ key: 'company', title: t('setup.steps.company') }, { key: 'admin', title: t('setup.steps.admin') })
    }
    list.push({ key: 'install', title: t('setup.steps.install') })
    return list
  }, [mode, t])

  const current = steps[step]?.key

  const next = async () => {
    if (current === 'company') await companyForm.validateFields()
    if (current === 'admin') await adminForm.validateFields()
    setStep((s) => Math.min(s + 1, steps.length - 1))
  }
  const back = () => setStep((s) => Math.max(s - 1, 0))

  const Check = ({ ok, label }: { ok: boolean; label: string }) => (
    <Space>
      {ok ? <CheckCircleFilled style={{ color: '#2E9E5B' }} /> : <CloseCircleFilled style={{ color: '#D64545' }} />}
      <span>{label}</span>
    </Space>
  )

  return (
    <div style={{ minHeight: '100vh', padding: '32px 16px' }}>
      <div style={{ maxWidth: 920, margin: '0 auto' }}>
        <Space align="center" style={{ marginBottom: 24 }}>
          <img src="/favicon.svg" width={40} height={40} alt="" />
          <div>
            <Typography.Title level={3} style={{ margin: 0 }}>{t('setup.title')}</Typography.Title>
            <Typography.Text type="secondary">{t('setup.subtitle')}</Typography.Text>
          </div>
        </Space>

        <Steps current={step} items={steps.map((s) => ({ title: s.title }))} size="small" style={{ marginBottom: 24 }} />

        <Card>
          {current === 'lang' && (
            <Space orientation="vertical" size="large" style={{ width: '100%' }}>
              <Typography.Title level={4}>{t('setup.chooseLanguage')}</Typography.Title>
              <Row gutter={16}>
                {(['ro', 'ru', 'en'] as Lang[]).map((l) => (
                  <Col xs={24} sm={8} key={l}>
                    <Card hoverable onClick={() => setLang(l)}
                      style={{ borderColor: lang === l ? 'var(--ant-color-primary)' : undefined, borderWidth: 2 }}>
                      <Typography.Title level={4} style={{ margin: 0 }}>{{ ro: 'Română', ru: 'Русский', en: 'English' }[l]}</Typography.Title>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Space>
          )}

          {current === 'engine' && (
            <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
              <Typography.Title level={4}>{t('setup.chooseEngine')}</Typography.Title>
              <Typography.Paragraph type="secondary">{t('setup.engineHint')}</Typography.Paragraph>
              <Row gutter={[16, 16]}>
                {drivers.map((d) => (
                  <Col xs={24} sm={12} md={8} key={d.code}>
                    <Card hoverable={d.available} onClick={() => d.available && chooseEngine(d.code)}
                      style={{
                        height: '100%', opacity: d.available ? 1 : 0.5, borderWidth: 2,
                        borderColor: db.engine === d.code ? 'var(--ant-color-primary)' : undefined,
                      }}>
                      <Space orientation="vertical" size={4}>
                        {d.code === 'sqlite' ? <DesktopOutlined style={{ fontSize: 24 }} /> : <CloudServerOutlined style={{ fontSize: 24 }} />}
                        <Typography.Text strong>{d.label}</Typography.Text>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {t(`setup.engineDesc.${d.code}`)}
                        </Typography.Text>
                        {!d.available && <Tag color="red">{t('setup.driverMissing')}</Tag>}
                        {!d.available && d.install_url && (
                          <Typography.Link href={d.install_url} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}
                            onClick={(e) => e.stopPropagation()}>{t('setup.odbcInstall')}</Typography.Link>
                        )}
                        {d.available && d.odbc && <Typography.Text type="secondary" style={{ fontSize: 12 }}>ODBC: {d.odbc}</Typography.Text>}
                        {d.code === 'postgresql' && <Tag color="green">{t('setup.recommended')}</Tag>}
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Space>
          )}

          {current === 'connection' && (
            <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
              <Typography.Title level={4}><DatabaseOutlined /> {engine?.label}</Typography.Title>
              <Form form={dbForm} layout="vertical" initialValues={db} onValuesChange={() => setProbe(null)}>
                {isSqlite ? (
                  <Form.Item name="name" label={t('setup.sqliteFile')} extra={t('setup.sqliteHint')} rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                ) : (
                  <Row gutter={16}>
                    <Col xs={24} md={16}>
                      <Form.Item name="host" label={t('setup.host')} rules={[{ required: true, message: t('common.required') }]}>
                        <Input placeholder="192.168.1.10" />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={8}>
                      <Form.Item name="port" label={t('setup.port')}>
                        <InputNumber style={{ width: '100%' }} min={1} max={65535} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={8}>
                      <Form.Item name="name" label={db.engine === 'oracle' ? t('setup.serviceName') : t('setup.dbName')}
                        rules={[{ required: true, message: t('common.required') }]}>
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={8}>
                      <Form.Item name="user" label={db.engine === 'oracle' ? t('setup.schemaUser') : t('setup.user')}
                        rules={[{ required: true, message: t('common.required') }]}>
                        <Input autoComplete="off" />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={8}>
                      <Form.Item name="password" label={t('setup.password')}>
                        <Input.Password autoComplete="new-password" />
                      </Form.Item>
                    </Col>
                  </Row>
                )}
              </Form>
              <Button type="primary" onClick={testConnection} loading={testing}>{t('setup.testConnection')}</Button>

              {probe && (
                <Card size="small">
                  <Space orientation="vertical">
                    {!isSqlite && <Check ok={probe.server_ok} label={t('setup.serverOk')} />}
                    <Check ok={probe.database_exists} label={t('setup.dbExists')} />
                    {probe.version && <Typography.Text type="secondary">{probe.version}</Typography.Text>}
                    {probe.error && <Alert type="error" title={probe.error} showIcon />}
                  </Space>
                </Card>
              )}

              {probe && probe.server_ok && !probe.database_exists && (
                <Alert type="warning" showIcon title={t('setup.dbMissing')}
                  description={
                    <Space orientation="vertical" style={{ width: '100%' }}>
                      <span>{t('setup.dbMissingHint')}</span>
                      {!isSqlite && (
                        <Collapse size="small" items={[{
                          key: 'adm', label: t('setup.serverAdmin'),
                          children: (
                            <Form form={adminDbForm} layout="vertical">
                              <Typography.Paragraph type="secondary">{t('setup.serverAdminHint')}</Typography.Paragraph>
                              <Row gutter={16}>
                                <Col xs={24} md={12}>
                                  <Form.Item name="admin_user" label={t('setup.user')}>
                                    <Input placeholder={db.engine === 'postgresql' ? 'postgres' : db.engine === 'mysql' ? 'root' : db.engine === 'mssql' ? 'sa' : 'system'} />
                                  </Form.Item>
                                </Col>
                                <Col xs={24} md={12}>
                                  <Form.Item name="admin_password" label={t('setup.password')}>
                                    <Input.Password autoComplete="new-password" />
                                  </Form.Item>
                                </Col>
                              </Row>
                            </Form>
                          ),
                        }]} />
                      )}
                      <Button type="primary" onClick={createDatabase} loading={creating}>{t('setup.createDb')}</Button>
                    </Space>
                  } />
              )}

              {connectionReady && probe?.has_crm && !probe.unfinished && (
                <Alert type="info" showIcon title={t('setup.existingCrm')} description={t('setup.existingCrmHint')} />
              )}
              {connectionReady && probe?.unfinished && (
                <Alert type="warning" showIcon title={t('setup.unfinished')} description={t('setup.unfinishedHint')} />
              )}
              {connectionReady && foreignTables && (
                <Alert type="error" showIcon title={t('setup.foreignTables', { count: probe?.table_count })} />
              )}
              {connectionReady && !probe?.has_crm && !foreignTables && (
                <Alert type="success" showIcon title={t('setup.readyNew')} />
              )}
            </Space>
          )}

          {current === 'company' && (
            <Form form={companyForm} layout="vertical" initialValues={{ default_theme: 'green', base_currency: 'MDL' }}>
              <Typography.Title level={4}>{t('setup.companyTitle')}</Typography.Title>
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item name="name_ro" label={t('constants.name_ro')} rules={[{ required: true, message: t('common.required') }]}>
                    <Input placeholder="Alimente Grup SRL" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="name_ru" label={t('constants.name_ru')}><Input /></Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="idno" label="IDNO" rules={[{ pattern: /^\d{13}$/, message: t('constants.idnoHint') }]}>
                    <Input maxLength={13} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="vat_code" label={t('constants.vat_code')}><Input /></Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item name="phone" label={t('constants.phone')}><Input /></Form.Item>
                </Col>
                <Col xs={24}>
                  <Form.Item name="legal_address" label={t('constants.legal_address')}><Input /></Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="iban" label="IBAN"><Input placeholder="MD24AG000225100013104168" /></Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="bank_name" label={t('constants.bank')}><Input /></Form.Item>
                </Col>
                <Col xs={24}>
                  <Form.Item name="default_theme" label={t('constants.default_theme')}>
                    <ThemePicker onPick={(th) => setThemeChoice(th)} />
                  </Form.Item>
                </Col>
              </Row>
              <Typography.Text type="secondary">{t('setup.companyLater')}</Typography.Text>
            </Form>
          )}

          {current === 'admin' && (
            <Form form={adminForm} layout="vertical" initialValues={{ username: 'admin' }}>
              <Typography.Title level={4}>{t('setup.adminTitle')}</Typography.Title>
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item name="last_name" label={t('users.last_name')}><Input /></Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="first_name" label={t('users.first_name')}><Input /></Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="username" label={t('login.username')} rules={[{ required: true, message: t('common.required') }]}>
                    <Input autoComplete="off" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="email" label="E-mail" rules={[{ type: 'email' }]}><Input /></Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="password" label={t('login.password')} extra={t('users.passwordRules')}
                    rules={[{ required: true, message: t('common.required') }, { min: 8, message: t('users.passwordRules') }]}>
                    <Input.Password autoComplete="new-password" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="password2" label={t('users.passwordRepeat')} dependencies={['password']}
                    rules={[{ required: true, message: t('common.required') }, ({ getFieldValue }) => ({
                      validator: (_, v) => (!v || v === getFieldValue('password') ? Promise.resolve() : Promise.reject(new Error(t('users.passwordMismatch')))),
                    })]}>
                    <Input.Password autoComplete="new-password" />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          )}

          {current === 'install' && (
            <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
              {done ? (
                <Result status="success" title={t('setup.doneTitle')} subTitle={t('setup.doneRestart')} extra={<Spin />} />
              ) : (
                <>
                  <Typography.Title level={4}>{t('setup.summary')}</Typography.Title>
                  <ul>
                    <li>{t('setup.steps.engine')}: <b>{engine?.label}</b></li>
                    {!isSqlite && <li>{t('setup.host')}: <b>{db.host}:{db.port}</b> / <b>{db.name}</b></li>}
                    {isSqlite && <li>{t('setup.sqliteFile')}: <b>{db.name}</b></li>}
                    <li>{mode === 'new' ? t('setup.modeNew') : t('setup.modeExisting')}</li>
                    {mode === 'new' && <li>{t('setup.steps.company')}: <b>{companyForm.getFieldValue('name_ro')}</b></li>}
                    {mode === 'new' && <li>{t('setup.steps.admin')}: <b>{adminForm.getFieldValue('username')}</b></li>}
                  </ul>
                  {mode === 'new' && (
                    <div style={{ marginBottom: 12 }}>
                      <Checkbox checked={demo} onChange={(e) => setDemo(e.target.checked)}>{t('setup.demo')}</Checkbox>
                      <div><Typography.Text type="secondary">{t('setup.demoHint')}</Typography.Text></div>
                    </div>
                  )}
                  {installError && <Alert type="error" showIcon title={installError} />}
                  <Button type="primary" size="large" onClick={install} loading={installing}>
                    {installing ? t('setup.installing') : t('setup.install')}
                  </Button>
                </>
              )}
              {installLog && (
                <Collapse size="small" items={[{
                  key: 'log', label: t('setup.log'),
                  children: <pre style={{ maxHeight: 300, overflow: 'auto', fontSize: 12, margin: 0 }}>{installLog}</pre>,
                }]} />
              )}
            </Space>
          )}

          {!done && (
            <Space style={{ marginTop: 24, width: '100%', justifyContent: 'space-between' }}>
              <Button onClick={back} disabled={step === 0 || installing}>{t('common.back')}</Button>
              {current !== 'install' && (
                <Button type="primary" onClick={next}
                  disabled={(current === 'engine' && !engine?.available) || (current === 'connection' && (!connectionReady || foreignTables))}>
                  {t('common.next')}
                </Button>
              )}
            </Space>
          )}
        </Card>
      </div>
    </div>
  )
}

/** Alegerea temei, cu mostre de culoare. */
export function ThemePicker({ value, onChange, onPick }: {
  value?: ThemeName
  onChange?: (v: ThemeName) => void
  onPick?: (v: ThemeName) => void
}) {
  const { t } = useTranslation()
  return (
    <Radio.Group value={value} onChange={(e) => { onChange?.(e.target.value); onPick?.(e.target.value) }}>
      <Space wrap>
        {(Object.keys(PALETTES) as ThemeName[]).map((name) => {
          const p = PALETTES[name]
          return (
            <Radio.Button key={name} value={name} style={{ height: 'auto', padding: 8 }}>
              <Space>
                <span style={{
                  display: 'inline-flex', width: 44, height: 28, borderRadius: 6, overflow: 'hidden',
                  border: '1px solid rgba(0,0,0,.15)', verticalAlign: 'middle',
                }}>
                  <span style={{ flex: 1, background: p.bg }} />
                  <span style={{ flex: 1, background: p.primary }} />
                </span>
                {t(`themes.${name}`)}
              </Space>
            </Radio.Button>
          )
        })}
      </Space>
    </Radio.Group>
  )
}


import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert, Button, Col, Divider, Form, Input, InputNumber, Modal, Row, Select, Space, Switch, Tag, Tooltip, Typography, message,
} from 'antd'
import { ExperimentOutlined, PlusOutlined } from '@ant-design/icons'

import Table from '../../components/AppTable'
import EmployeeSelect from '../../components/EmployeeSelect'
import MarkButton from '../../components/MarkButton'
import { api, errorText, fieldErrors } from '../../api/client'
import { invalidateCache, useFetch } from '../../api/hooks'
import { defaultMonth } from '../../api/worktime'
import {
  AUTO_KEYS, FORMULAS, GENERAL_FORMULAS, money, type FormulaCatalog, type FormulaCheck, type PayType, type TryResult,
} from '../../api/payroll'
import { useApp, useLocalName } from '../../auth/AppContext'
import { MonthPicker } from '../worktime/MonthDocs'

type Lang = 'ro' | 'ru' | 'en'

/** Treptele pe vechimea totală în muncă ({from: ani, pct}) scrise ca text: „3:5, 10:10, 20:15”. */
function ScaleInput({ value, onChange }: { value?: { from: number; pct: number }[]; onChange?: (v: unknown[]) => void }) {
  const { t } = useTranslation()
  const text = (value ?? []).map((s) => `${s.from}:${s.pct}`).join(', ')
  const [draft, setDraft] = useState(text)
  useEffect(() => setDraft(text), [text])
  return (
    <Input value={draft} placeholder={t('pay.type.scalePlaceholder')} onChange={(e) => setDraft(e.target.value)} onBlur={() => {
      const steps = draft.split(/[,;]/).map((p) => p.trim()).filter(Boolean).map((p) => {
        const [k, v] = p.split(':').map((x) => x.trim())
        return { from: Number(k), pct: Number(v) }  // un text care nu e număr îl respinge serverul, cu mesajul lui
      })
      onChange?.(steps)
    }} />
  )
}

/**
 * Editorul formulei: textul, verificarea pe loc (eroarea cu poziția), variabilele (clic — se inserează la cursor), funcțiile,
 * constantele C.<cod> și celelalte tipuri [COD].
 */
function FormulaInput({ value, onChange, types, code, disabled }: {
  value?: string
  onChange?: (v: string) => void
  types: PayType[]
  code?: string
  disabled?: boolean
}) {
  const { t } = useTranslation()
  const { lang } = useApp()
  const localName = useLocalName()
  const { data: catalog } = useFetch<FormulaCatalog>('/payroll/types/variables/')
  const [check, setCheck] = useState<FormulaCheck | null>(null)
  const ref = useRef<HTMLTextAreaElement | null>(null)
  const text = value ?? ''

  useEffect(() => {
    if (!text.trim()) { setCheck(null); return }
    const timer = setTimeout(() => {
      api.post<FormulaCheck>('/payroll/types/check/', { expression: text, code }).then((r) => setCheck(r.data)).catch(() => setCheck(null))
    }, 400)
    return () => clearTimeout(timer)
  }, [text, code])

  const insert = (piece: string) => {
    const el = ref.current
    const start = el?.selectionStart ?? text.length
    const end = el?.selectionEnd ?? text.length
    const next = text.slice(0, start) + piece + text.slice(end)
    onChange?.(next)
    requestAnimationFrame(() => {
      if (!el) return
      el.focus()
      el.setSelectionRange(start + piece.length, start + piece.length)
    })
  }
  const describe = (v: { ro: string; ru: string; en: string }) => v[lang as Lang] || v.ro

  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={6}>
      <Input.TextArea ref={(el) => { ref.current = el?.resizableTextArea?.textArea ?? null }} rows={3} value={text} disabled={disabled}
        style={{ fontFamily: 'monospace' }} placeholder="TarifOrar * OreNoapte * C.night_pct / 100"
        onChange={(e) => onChange?.(e.target.value)} />
      {check && (check.ok
        ? <Alert type="success" showIcon title={t('pay.fx.ok', { vars: [...(check.variables ?? []), ...(check.constants ?? []).map((c) => `C.${c}`),
          ...(check.refs ?? []).map((c) => `[${c}]`)].join(', ') || '—' })} />
        : <Alert type="error" showIcon title={check.position ? t('pay.fx.errorAt', { error: check.error, position: check.position }) : check.error} />)}
      {!disabled && <>
        <Typography.Text type="secondary">{t('pay.fx.variables')}</Typography.Text>
        <Space wrap size={[4, 4]}>
          {(catalog?.variables ?? []).map((v) => (
            <Tooltip key={v.name} title={describe(v)}><Tag style={{ cursor: 'pointer' }} color="blue" onClick={() => insert(v.name)}>{v.name}</Tag></Tooltip>
          ))}
        </Space>
        <Typography.Text type="secondary">{t('pay.fx.functions')}</Typography.Text>
        <Space wrap size={[4, 4]}>
          {(catalog?.functions ?? []).map((f) => (
            <Tooltip key={f.name} title={describe(f)}><Tag style={{ cursor: 'pointer' }} color="purple" onClick={() => insert(`${f.name}(`)}>{f.name}( ; )</Tag></Tooltip>
          ))}
          {['+', '-', '*', '/', '(', ')', ';', '>=', '<=', '=', '<>', 'și', 'sau'].map((op) => (
            <Tag key={op} style={{ cursor: 'pointer' }} onClick={() => insert(` ${op} `.replace('( ', '(').replace(' )', ')'))}>{op}</Tag>
          ))}
        </Space>
        <Row gutter={8}>
          <Col xs={24} md={12}>
            <Select showSearch allowClear style={{ width: '100%' }} placeholder={t('pay.fx.insertType')} value={null} optionFilterProp="label"
              onChange={(c: string | null) => c && insert(`[${c}]`)}
              options={types.filter((x) => x.code !== code).map((x) => ({ value: x.code, label: `[${x.code}] ${localName(x)}` }))} />
          </Col>
          <Col xs={24} md={12}>
            <Select showSearch allowClear style={{ width: '100%' }} placeholder={t('pay.fx.insertConstant')} value={null} optionFilterProp="label"
              onChange={(c: string | null) => c && insert(`C.${c}`)}
              options={(catalog?.constants ?? []).map((c) => ({ value: c.code, label: `C.${c.code} — ${c.name}` }))} />
          </Col>
        </Row>
        <Typography.Text type="secondary">{t('pay.fx.syntax')}</Typography.Text>
      </>}
    </Space>
  )
}

/** „Încearcă pe un angajat”: calculul lunii în memorie (nimic nu se salvează), cu variabilele și valorile lor. */
function TryPanel({ form, editingId }: { form: ReturnType<typeof Form.useForm>[0]; editingId?: number }) {
  const { t } = useTranslation()
  const [employee, setEmployee] = useState<number | null>(null)
  const [ym, setYm] = useState(defaultMonth())
  const [row, setRow] = useState<{ amount?: number | null; percent?: number | null; quantity?: number | null }>({})
  const [result, setResult] = useState<TryResult | null>(null)
  const [busy, setBusy] = useState(false)
  const run = async () => {
    if (!employee) { message.warning(t('pay.fx.chooseEmployee')); return }
    setBusy(true)
    try {
      const values = form.getFieldsValue(true)
      const r = await api.post<TryResult>('/payroll/types/try/', {
        ...values, id: editingId, code: values.code || 'NOU', name_ro: values.name_ro || values.code || 'NOU',
        employee, year: ym.year, month: ym.month, ...row })
      setResult(r.data)
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={8}>
      <Space wrap>
        <EmployeeSelect value={employee} onChange={(v) => setEmployee((v as number | null) ?? null)} style={{ width: 300 }} />
        <MonthPicker year={ym.year} month={ym.month} onChange={(y, m) => setYm({ year: y, month: m })} />
        <InputNumber placeholder={t('pay.fx.amount')} value={row.amount ?? null} onChange={(v) => setRow({ ...row, amount: v })} style={{ width: 110 }} />
        <InputNumber placeholder="%" value={row.percent ?? null} onChange={(v) => setRow({ ...row, percent: v })} style={{ width: 80 }} />
        <InputNumber placeholder={t('pay.fx.quantity')} value={row.quantity ?? null} onChange={(v) => setRow({ ...row, quantity: v })} style={{ width: 110 }} />
        <Button icon={<ExperimentOutlined />} loading={busy} onClick={run}>{t('pay.fx.try')}</Button>
      </Space>
      <Typography.Text type="secondary">{t('pay.fx.tryHint')}</Typography.Text>
      {result?.errors.map((e) => <Alert key={e} type="error" showIcon title={e} />)}
      {result?.lines.map((ln) => (
        <div key={ln.employment} style={{ border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6, padding: 8 }}>
          <Space wrap><b>{ln.employment_label}</b><Tag color="green">{t('pay.fx.result')}: {money(ln.result)}</Tag></Space>
          {ln.traces.map((tr, i) => (
            <div key={i} style={{ marginTop: 6 }}>
              {tr.error ? <Alert type="error" showIcon title={tr.error} /> : <Typography.Text code>{tr.note}</Typography.Text>}
              {tr.variables.length > 0 && <Table rowKey="name" size="small" pagination={false} noSettings style={{ marginTop: 6 }}
                dataSource={tr.variables} columns={[
                  { title: t('pay.fx.variable'), dataIndex: 'name', width: 200, render: (v: string) => <Typography.Text code>{v}</Typography.Text> },
                  { title: t('pay.fx.value'), dataIndex: 'value', width: 120, align: 'right', render: (v: string) => Number(v).toLocaleString('ro-MD', { maximumFractionDigits: 4 }) },
                  { title: t('pay.fx.meaning'), dataIndex: 'description' },
                ]} />}
            </div>
          ))}
          {!ln.traces.length && ln.notes.map((n) => <div key={n}><Typography.Text type="secondary">{n}</Typography.Text></div>)}
          <Typography.Text type="secondary" style={{ display: 'block', marginTop: 6 }}>
            {t('pay.fx.lineItems')}: {ln.items.map((i) => `${i.code} ${money(i.amount)}`).join(' · ')}
          </Typography.Text>
        </div>
      ))}
    </Space>
  )
}

/** Tipurile de calcul (Administrare → Setări): tabelul cu baza vizibilă și fiscalitatea, editorul cu formula și „Încearcă”. */
export default function PayTypesPage() {
  const { t } = useTranslation()
  const { hasPerm, lang, languages } = useApp()
  const localName = useLocalName()
  const canEdit = hasPerm('payroll_settings.edit')
  const { data, loading, reload } = useFetch<PayType[]>('/payroll/types/')
  const types = useMemo(() => data ?? [], [data])
  const [editing, setEditing] = useState<Partial<PayType> | null>(null)
  const [form] = Form.useForm()
  const formula = Form.useWatch('formula', form)
  const code = Form.useWatch('code', form)
  const how = (r: PayType) => r.how?.[lang as Lang] || r.how?.ro || ''

  const open = (row?: PayType) => {
    const value: Partial<PayType> = row ?? { category: 'accrual', formula: 'fixed', auto: 'none', percent: '0', base_codes: [], scale: [],
      expression: '', applies_to: 'row', taxable: true, cas: true, cnam: true, exempt_month: '0', exempt_year: '0', exempt_avg_pct: '0',
      in_average: true, ipc_code: 'SAL', on_payslip: true, is_active: true, sort: 0 }
    setEditing(value)
    form.resetFields()
    form.setFieldsValue(value)
  }
  const save = async () => {
    const values = await form.validateFields()
    try {
      if (editing?.id) await api.patch(`/payroll/types/${editing.id}/`, values)
      else await api.post('/payroll/types/', values)
      message.success(t('common.saved'))
      setEditing(null)
      invalidateCache('/payroll/types/')
      reload()
    } catch (e) {
      form.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }
  const exempt = (r: PayType) => [
    Number(r.exempt_month) ? t('pay.fx.perMonth', { v: money(r.exempt_month) }) : '',
    Number(r.exempt_year) ? t('pay.fx.perYear', { v: money(r.exempt_year) }) : '',
    Number(r.exempt_avg_pct) ? t('pay.fx.perAvg', { v: Number(r.exempt_avg_pct) }) : '',
  ].filter(Boolean).join('; ')
  const yes = (v: boolean) => (v ? <Tag color="green">{t('common.yes')}</Tag> : <Tag>{t('common.no')}</Tag>)
  const typeOptions = types.filter((x) => x.code !== code).map((x) => ({ value: x.code, label: `${x.code} — ${localName(x)}` }))

  return (
    <>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }} wrap>
        <Typography.Text type="secondary">{t('pay.fx.hint')}</Typography.Text>
        {canEdit && <Button icon={<PlusOutlined />} onClick={() => open()}>{t('common.add')}</Button>}
      </Space>
      <Table<PayType> rowKey="id" size="small" loading={loading} dataSource={types} pagination={false} exportName={t('menu.payrollTypes')}
        onRow={(r) => ({ onDoubleClick: () => canEdit && !r.deletion_mark && open(r) })}
        columns={[
          { title: t('common.code'), dataIndex: 'code', width: 100, render: (v: string, r) => canEdit && !r.deletion_mark ? <a onClick={() => open(r)}>{v}</a> : v },
          { title: t('common.name'), key: 'name', width: 230, render: (_: unknown, r) => localName(r) },
          { title: t('pay.type.category'), dataIndex: 'category_label', width: 120 },
          { title: t('pay.fx.how'), key: 'how', render: (_: unknown, r) => (
            <Space orientation="vertical" size={0}>
              {r.formula === 'expr' ? <Typography.Text code>{r.expression}</Typography.Text> : <Typography.Text type="secondary">{r.formula_label}</Typography.Text>}
              <span>{how(r)}</span>
            </Space>) },
          { title: t('pay.type.taxable'), dataIndex: 'taxable', width: 85, render: yes },
          { title: 'CNAM', dataIndex: 'cnam', width: 70, render: yes },
          { title: 'CAS', dataIndex: 'cas', width: 65, render: yes },
          { title: t('pay.type.inAverage'), dataIndex: 'in_average', width: 85, render: yes },
          { title: t('pay.fx.exempt'), key: 'exempt', width: 160, render: (_: unknown, r) => exempt(r) },
          { title: t('pay.fx.ipc'), dataIndex: 'ipc_code', width: 80 },
          { title: t('common.active'), dataIndex: 'is_active', width: 70, render: (v: boolean) => (v ? '✓' : '') },
          ...(canEdit ? [{ title: '', key: '_del', width: 50, render: (_: unknown, r: PayType) => (
            <MarkButton endpoint="/payroll/types/" row={r} onDone={reload} />) }] : []),
        ]} />
      <Modal open={!!editing} onOk={save} onCancel={() => setEditing(null)} width={1100} destroyOnHidden
        title={editing?.id ? `${editing.code} — ${localName(editing as PayType)}` : t('common.add')}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col xs={24} md={6}><Form.Item name="code" label={t('common.code')} rules={[{ required: true }]} extra={t('pay.fx.codeHint')}><Input /></Form.Item></Col>
            <Col xs={24} md={18}><Form.Item name="name_ro" label={t('org.nameRo')} rules={[{ required: true }]}><Input /></Form.Item></Col>
            {languages.includes('ru') && <Col xs={24} md={12}><Form.Item name="name_ru" label={t('org.nameRu')}><Input /></Form.Item></Col>}
            {languages.includes('en') && <Col xs={24} md={12}><Form.Item name="name_en" label={t('org.nameEn')}><Input /></Form.Item></Col>}
            <Col xs={24} md={8}><Form.Item name="category" label={t('pay.type.category')} rules={[{ required: true }]}>
              <Select options={['accrual', 'deduction', 'employer'].map((c) => ({ value: c, label: t(`pay.type.categories.${c}`) }))} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="formula" label={t('pay.type.formula')} rules={[{ required: true }]}>
              <Select options={FORMULAS.map((f) => ({ value: f, label: t(`pay.type.formulas.${f}`) }))} /></Form.Item></Col>
            {formula === 'auto'
              ? <Col xs={24} md={8}><Form.Item name="auto" label={t('pay.type.auto')}>
                <Select options={AUTO_KEYS.map((a) => ({ value: a, label: t(`pay.type.autos.${a}`) }))} /></Form.Item></Col>
              : <Col xs={24} md={8}><Form.Item name="applies_to" label={t('pay.fx.appliesTo')} extra={t('pay.fx.appliesToHint')}>
                <Select options={['row', 'all'].map((a) => ({ value: a, label: t(`pay.fx.applies.${a}`), disabled: a === 'all' && !GENERAL_FORMULAS.includes(formula) }))} />
              </Form.Item></Col>}
          </Row>
          {editing?.id && editing.how && <Alert type="info" showIcon style={{ marginBottom: 12 }} title={t('pay.fx.how')}
            description={how(editing as PayType)} />}
          {formula === 'expr' && <Form.Item name="expression" label={t('pay.fx.expression')} rules={[{ required: true }]}>
            <FormulaInput types={types} code={code} />
          </Form.Item>}
          {['pct_salary', 'pct_base', 'expr'].includes(formula) && <Form.Item name="percent" label={t('pay.fx.defaultPercent')} extra={t('pay.fx.defaultPercentHint')}>
            <InputNumber style={{ width: 160 }} /></Form.Item>}
          {['pct_base', 'scale', 'expr'].includes(formula) && <Form.Item name="base_codes" label={t('pay.type.base')}
            extra={formula === 'expr' ? t('pay.fx.baseHint') : t('pay.type.baseHint')}>
            <Select mode="multiple" allowClear optionFilterProp="label" options={typeOptions} /></Form.Item>}
          {formula === 'scale' && <Form.Item name="scale" label={t('pay.type.scale')} extra={t('pay.type.scaleHint')}><ScaleInput /></Form.Item>}
          {formula && formula !== 'auto' && <>
            <Divider titlePlacement="start">{t('pay.fx.tryTitle')}</Divider>
            <TryPanel form={form} editingId={editing?.id} />
          </>}
          <Divider titlePlacement="start">{t('pay.fx.taxTitle')}</Divider>
          <Row gutter={16}>
            <Col xs={12} md={6}><Form.Item name="taxable" label={t('pay.fx.taxableLong')} valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={12} md={6}><Form.Item name="cnam" label={t('pay.fx.cnamLong')} valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={12} md={6}><Form.Item name="cas" label={t('pay.fx.casLong')} valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={12} md={6}><Form.Item name="in_average" label={t('pay.fx.inAverageLong')} valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="exempt_month" label={t('pay.type.exemptMonth')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="exempt_year" label={t('pay.type.exemptYear')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="exempt_avg_pct" label={t('pay.type.exemptAvg')}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={8}><Form.Item name="ipc_code" label={t('pay.type.ipc')}><Input /></Form.Item></Col>
          </Row>
          <Typography.Paragraph type="secondary">{t('pay.fx.taxHint')}</Typography.Paragraph>
          <Divider titlePlacement="start">{t('pay.fx.otherTitle')}</Divider>
          <Row gutter={16}>
            <Col xs={24} md={8}><Form.Item name="account" label={t('pay.type.account')}><Input /></Form.Item></Col>
            <Col xs={12} md={6}><Form.Item name="sort" label={t('org.sort')}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={12} md={5}><Form.Item name="on_payslip" label={t('pay.type.onPayslip')} valuePropName="checked"><Switch /></Form.Item></Col>
            <Col xs={12} md={5}><Form.Item name="is_active" label={t('common.active')} valuePropName="checked"><Switch /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>
    </>
  )
}

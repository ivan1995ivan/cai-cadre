import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Popconfirm, Row, Select, Space, Spin, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  CheckCircleOutlined, DeleteOutlined, FileTextOutlined, PlusOutlined, PrinterOutlined, ReloadOutlined, SaveOutlined, StopOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import CloseForm from '../../components/CloseForm'
import PrintDialog from '../../components/PrintDialog'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import { api, errorText, fieldErrors } from '../../api/client'
import { useFetch } from '../../api/hooks'
import { ORDER_STATUS_COLOR, type Order, type OrderItem } from '../../api/orders'
import { useApp } from '../../auth/AppContext'
import ItemParams, { paramsIn, paramsOut } from './ItemParams'
import EmployeeSelect from '../../components/EmployeeSelect'
import FormLayout from '../../components/FormLayout'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'

/** Câmpurile antetului și ale punctelor, ca în 1C: eticheta în stânga, câmpul în dreapta (clasa `doc-head` din styles.css). */
export const DOC_HEAD = { layout: 'horizontal' as const, labelAlign: 'left' as const, labelWrap: true, labelCol: { flex: '150px' },
  wrapperCol: { flex: 1 }, className: 'doc-head' }

/**
 * Editorul ordinului: antetul, punctele (angajatul + parametrii + textul), semnarea, tiparul, anularea. Antetul e pe două
 * coloane, ca în 1C — în stânga numărul și data, titlul, temeiurile legale (unul sau mai multe; preambulul se compune din
 * ele) și preambulul; în dreapta temeiul, punctele finale, semnatarul și vizele. Plecarea cu modificări nesalvate (Esc, ✕,
 * altă filă) întreabă „Salvați modificările?”.
 */
export default function OrderEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [order, setOrder] = useState<Order | null>(null)
  const [header] = Form.useForm()
  const forms = useRef<Record<number, ReturnType<typeof Form.useForm>[0]>>({})
  const [print, setPrint] = useState<{ item?: number } | null>(null)
  const [busy, setBusy] = useState(false)
  const [adding, setAdding] = useState<number | undefined>()
  const [dirty, setDirty] = useState(false)
  const { data: bases } = useFetch<{ id: number; code: string; name_ro: string }[]>('/org/legal-bases/', { active: 1 })
  const draft = order?.status === 'draft' && !order.deletion_mark  // ordinul marcat pentru ștergere nu se mai schimbă
  const canEdit = draft && hasPerm('orders.edit')

  const apply = (o: Order) => {
    setOrder(o)
    header.setFieldsValue({ ...o, date: dayjs(o.date) })
    setDirty(false)
  }
  /** Temeiurile alese: preambulul se compune din nou din ele (în ordinea alegerii). */
  const pickBases = async (ids: number[]) => {
    try {
      const r = await api.get<{ text: string }>('/org/legal-bases/preamble/', { params: { ids: ids.join(',') } })
      header.setFieldValue('preamble', r.data.text)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const load = () => api.get<Order>(`/orders/orders/${id}/`).then((r) => apply(r.data)).catch((e) => message.error(errorText(e)))
  useEffect(() => { load() }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  /** Salvează antetul și punctele (fiecare punct își regenerează textul pe server). */
  const saveAll = async (quiet = false) => {
    if (!order) return false
    try {
      const h = await header.validateFields()
      await api.patch(`/orders/orders/${order.id}/`, { ...h, date: h.date.format('YYYY-MM-DD'), seq: h.seq || null })
      for (const item of order.items ?? []) {
        const f = forms.current[item.id]
        if (!f) continue
        const v = (await f.validateFields()) as Record<string, unknown>
        const { __text, ...rest } = v
        const body: Record<string, unknown> = { params: paramsOut(rest) }
        if (__text !== undefined && __text !== item.text) body.text = __text
        await api.patch(`/orders/items/${item.id}/`, body)
      }
      if (!quiet) message.success(t('common.saved'))
      await load()
      return true
    } catch (e) {
      header.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
      return false
    }
  }
  useUnsavedGuard(dirty && !!canEdit, () => saveAll(true))

  const sign = async () => {
    setBusy(true)
    try {
      if (!(await saveAll(true))) return
      const r = await api.post<Order>(`/orders/orders/${id}/sign/`)
      apply(r.data)
      message.success(t('ord.signed', { number: r.data.number }))
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const addEmployee = async () => {
    if (!adding || !order) return
    try {
      await api.post('/orders/items/', { order: order.id, employee: adding })
      setAdding(undefined)
      load()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const removeItem = async (item: OrderItem) => {
    try {
      await api.delete(`/orders/items/${item.id}/`)
      load()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const regenerate = async () => {
    if (!(await saveAll(true))) return
    const r = await api.post<Order>(`/orders/orders/${id}/refresh-texts/`, { force: true })
    apply(r.data)
  }

  const cancelByOrder = async () => {
    try {
      const r = await api.post<Order>(`/orders/orders/${id}/cancel-by-order/`)
      navigate(`/orders/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const acknowledge = async () => {
    try {
      const r = await api.post<Order>(`/orders/orders/${id}/acknowledge/`, { date: dayjs().format('YYYY-MM-DD') })
      apply(r.data)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  if (!order) return <Spin />
  const items = order.items ?? []
  const canAdd = canEdit && order.effect !== 'staff_list' && order.effect !== 'cancel' && (order.collective || items.length === 0)

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      <Card className="doc-form"
        title={<Space wrap>
          <span>{order.number ? t('ord.heading', { number: order.number, date: dayjs(order.date).format('DD.MM.YYYY') }) : t('ord.draftHeading')}</span>
          <Tag>{order.type_name}</Tag>
          <Tag color={ORDER_STATUS_COLOR[order.status]}>{t(`ord.statuses.${order.status}`)}</Tag>
        </Space>}
        extra={<Space wrap>
          <Button icon={<PrinterOutlined />} onClick={() => setPrint({})}>{t('org.sl.print')}</Button>
          {canEdit && <Button icon={<SaveOutlined />} onClick={() => saveAll()}>{t('common.save')}</Button>}
          {draft && hasPerm('orders.approve') && (
            <Popconfirm title={t('ord.signConfirm')} onConfirm={sign}>
              <Button type="primary" icon={<CheckCircleOutlined />} loading={busy}>{t('ord.sign')}</Button>
            </Popconfirm>)}
          {order.status === 'signed' && hasPerm('orders.edit') && <Button onClick={acknowledge}>{t('ord.acknowledgeAll')}</Button>}
          {order.status === 'signed' && order.type_code !== 'cancel_order' && hasPerm('orders.create') && (
            <Popconfirm title={t('ord.cancelConfirm')} onConfirm={cancelByOrder}>
              <Button danger icon={<StopOutlined />}>{t('ord.cancelByOrder')}</Button>
            </Popconfirm>)}
          {draft && hasPerm('orders.delete') && <MarkButton endpoint="/orders/orders/" row={order} onDone={load} text />}
          <CloseForm to="/orders" />
        </Space>}>
        <MarkedBanner endpoint="/orders/orders/" row={order} onDone={load} canUnmark={hasPerm('orders.delete')} />
        {order.status === 'cancelled' && <Alert type="error" showIcon style={{ marginBottom: 12 }} title={t('ord.cancelledBy', { label: order.cancelled_by_label })} />}
        {order.status === 'signed' && <Alert type="success" showIcon style={{ marginBottom: 12 }} title={t('ord.appliedHint')} />}
        <Form form={header} {...DOC_HEAD} disabled={!canEdit} onValuesChange={() => setDirty(true)}>
          <FormLayout formKey="order"><Row gutter={24}>
            <Col xs={24} lg={12}>
              <Form.Item label={<Tooltip title={t('ord.seqHint')}>{t('ord.numberDate')}</Tooltip>} required>
                <Space.Compact style={{ width: '100%' }}>
                  <Form.Item name="seq" noStyle><InputNumber min={1} placeholder={t('ord.seqAuto')} style={{ width: 120 }} /></Form.Item>
                  <Space.Addon>{t('ord.of')}</Space.Addon>
                  <Form.Item name="date" noStyle rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" style={{ width: 150 }} /></Form.Item>
                </Space.Compact>
              </Form.Item>
              <Form.Item name="title" label={t('ord.title')} rules={[{ required: true }]}><Input /></Form.Item>
              <Form.Item name="legal_bases" label={t('ord.legalBases')} extra={t('ord.legalBasesHint')}>
                <Select mode="multiple" allowClear showSearch optionFilterProp="label" onChange={(ids: number[]) => pickBases(ids)}
                  options={(bases ?? []).map((b) => ({ value: b.id, label: `${b.code} — ${b.name_ro}` }))} />
              </Form.Item>
              <Form.Item name="preamble" label={t('ord.preamble')}><Input.TextArea autoSize={{ minRows: 1, maxRows: 4 }} /></Form.Item>
            </Col>
            <Col xs={24} lg={12}>
              <Form.Item name="basis" label={t('ord.basis')}><Input.TextArea autoSize={{ minRows: 1, maxRows: 4 }} placeholder={t('ord.basisHint')} /></Form.Item>
              <Form.Item name="footer" label={t('ord.footer')}><Input.TextArea autoSize={{ minRows: 1, maxRows: 4 }} placeholder={t('ord.footerHint')} /></Form.Item>
              <Form.Item label={t('ord.signer')}>
                <Space.Compact style={{ width: '100%' }}>
                  <Form.Item name="signer_position" noStyle><Input placeholder={t('ord.signerPosition')} style={{ width: '40%' }} /></Form.Item>
                  <Form.Item name="signer_name" noStyle><Input placeholder={t('ord.signerName')} style={{ width: '60%' }} /></Form.Item>
                </Space.Compact>
              </Form.Item>
              <Form.Item label={t('ord.approvals')}>
                <Form.List name="approvals">{(fields, { add, remove: rm }) => (<>
                  {fields.map((f) => (
                    <Space.Compact key={f.key} style={{ display: 'flex', marginBottom: 4 }}>
                      <Form.Item name={[f.name, 'position']} noStyle><Input placeholder={t('ord.signerPosition')} style={{ width: '40%' }} /></Form.Item>
                      <Form.Item name={[f.name, 'name']} noStyle><Input placeholder={t('ord.signerName')} style={{ width: '60%' }} /></Form.Item>
                      {canEdit && <Button danger icon={<DeleteOutlined />} onClick={() => rm(f.name)} />}
                    </Space.Compact>))}
                  {canEdit && <Button size="small" icon={<PlusOutlined />} onClick={() => add({ name: '', position: '' })}>{t('ord.addApproval')}</Button>}
                </>)}
                </Form.List>
              </Form.Item>
            </Col>
          </Row></FormLayout>
        </Form>
      </Card>

      <Card title={<Space><FileTextOutlined />{t('ord.points')}</Space>}
        extra={canEdit && items.length > 0 && <Button icon={<ReloadOutlined />} onClick={regenerate}>{t('ord.regenerate')}</Button>}>
        {items.length === 0 && order.effect !== 'staff_list' && <Typography.Paragraph type="secondary">{t('ord.noPoints')}</Typography.Paragraph>}
        {order.effect === 'staff_list' && items.length === 0 && canEdit && (
          <Button icon={<PlusOutlined />} onClick={async () => { await api.post('/orders/items/', { order: order.id, params: {} }); load() }}>{t('ord.addPoint')}</Button>)}
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          {items.map((item, idx) => (
            <PointCard key={item.id} no={idx + 1} item={item} order={order} disabled={!canEdit}
              register={(f) => { forms.current[item.id] = f }} onChange={() => setDirty(true)}
              onRemove={() => removeItem(item)} onExtract={() => setPrint({ item: item.id })} />
          ))}
        </Space>
        {canAdd && (
          <Space style={{ marginTop: 12 }}>
            <EmployeeSelect style={{ width: 420 }} placeholder={t('ord.addEmployee')} value={adding}
              onChange={(v) => setAdding(typeof v === 'number' ? v : undefined)} />
            <Button icon={<PlusOutlined />} disabled={!adding} onClick={addEmployee}>{t('common.add')}</Button>
          </Space>
        )}
      </Card>

      {print && (
        <PrintDialog open onClose={() => setPrint(null)} docType={print.item ? 'order_extract' : 'order'} url={`/orders/orders/${order.id}/print/`}
          params={print.item ? { item: print.item } : {}} optionKeys={[]} title={print.item ? t('ord.extract') : t('ord.printOrder')} />
      )}
    </Space>
  )
}

function PointCard({ no, item, order, disabled, register, onChange, onRemove, onExtract }: {
  no: number
  item: OrderItem
  order: Order
  disabled: boolean
  register: (f: ReturnType<typeof Form.useForm>[0]) => void
  onChange: () => void
  onRemove: () => void
  onExtract: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [preview, setPreview] = useState(false)
  useEffect(() => { register(form) }, [form, register])
  useEffect(() => { form.setFieldsValue({ ...paramsIn(item.params), __text: item.text }) }, [item, form])
  return (
    <Card size="small" type="inner"
      title={<Space wrap>
        <Tag>{no}</Tag>
        <b>{item.employee_name || t('ord.noEmployee')}</b>
        {item.employee_tab && <Typography.Text type="secondary">{t('staff.tab')} {item.employee_tab}</Typography.Text>}
        {item.acknowledged_on && <Tag color="green">{t('ord.acknowledged', { date: dayjs(item.acknowledged_on).format('DD.MM.YYYY') })}</Tag>}
        {item.text_edited && <Tag>{t('ord.manualText')}</Tag>}
      </Space>}
      extra={<Space>
        {order.status !== 'draft' && item.employee && <Button size="small" onClick={onExtract}>{t('ord.extract')}</Button>}
        {!disabled && <Popconfirm title={t('common.confirmDelete')} onConfirm={onRemove}><Button size="small" type="text" danger icon={<DeleteOutlined />} /></Popconfirm>}
      </Space>}>
      {(item.warnings ?? []).map((w) => <Alert key={w} type="warning" showIcon message={w} style={{ marginBottom: 8 }} />)}
      <Form form={form} {...DOC_HEAD} disabled={disabled} onValuesChange={onChange}>
        <ItemParams form={form} effect={order.effect === 'cancel' || order.type_code === 'cancel_order' ? 'cancel' : order.effect}
          code={order.type_code} employee={item.employee} disabled={disabled} />
        <Form.Item name="__text" label={<Space>{t('ord.pointText')}<a onClick={() => setPreview((x) => !x)}>{preview ? t('ord.hide') : t('ord.edit')}</a></Space>}
          extra={!preview && t('ord.textHint')} style={{ marginBottom: 0 }}>
          {preview ? <Input.TextArea rows={4} /> : <TextView />}
        </Form.Item>
      </Form>
    </Card>
  )
}

/** Textul punctului (doar citire, când nu se editează). */
function TextView({ value }: { value?: string }) {
  return <Typography.Paragraph style={{ margin: 0, padding: '6px 10px', background: 'var(--ant-color-fill-quaternary)', borderRadius: 6 }}>{value}</Typography.Paragraph>
}

import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { DatePicker, Form, Modal, Select, Typography, message } from 'antd'
import dayjs from 'dayjs'

import EmployeeSelect from '../../components/EmployeeSelect'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { OrgMeta } from '../../api/org'
import type { Order, OrderTypeLite } from '../../api/orders'
import { useLocalName } from '../../auth/AppContext'

/** Ordinul nou: tipul, data, angajatul / angajații; din fișa angajatului vine cu el deja ales. Creat — se deschide. */
export default function NewOrderDialog({ open, onClose, employee, employeeName }: {
  open: boolean
  onClose: () => void
  employee?: number
  employeeName?: string
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const localName = useLocalName()
  const [form] = Form.useForm()
  const { data: meta } = useFetch<OrgMeta>(open ? '/org/meta/' : null)
  const { data: types } = useFetch<OrderTypeLite[]>(open ? '/org/order-types/' : null, { active: 1 })
  const typeId = Form.useWatch('order_type', form)
  const chosenType = (types ?? []).find((x) => x.id === typeId)
  const typeOptions = (meta?.order_groups ?? []).map((g) => ({
    label: t(`org.orderGroup.${g}`),
    options: (types ?? []).filter((x) => x.group === g && (!employee || x.needs_employee !== false))
      .map((x) => ({ value: x.id, label: localName(x) })),
  }))

  useEffect(() => {
    if (!open) return
    form.resetFields()
    form.setFieldsValue({ date: dayjs(), employees: employee ? (chosenType?.collective ? [employee] : employee) : undefined })
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  const create = async () => {
    const v = await form.validateFields()
    try {
      const r = await api.post<Order>('/orders/orders/', { order_type: v.order_type, date: v.date.format('YYYY-MM-DD'),
        employees: Array.isArray(v.employees) ? v.employees : v.employees ? [v.employees] : [] })
      onClose()
      navigate(`/orders/${r.data.id}`)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <Modal open={open} title={t('ord.new')} onOk={create} onCancel={onClose} width={640}>
      <Form form={form} layout="vertical">
        <Form.Item name="order_type" label={t('ord.type')} rules={[{ required: true }]}>
          <Select showSearch optionFilterProp="label" options={typeOptions}
            onChange={(id) => {
              const ty = (types ?? []).find((x) => x.id === id)
              const cur = form.getFieldValue('employees')
              const one = Array.isArray(cur) ? cur[0] : cur
              form.setFieldValue('employees', one ? (ty?.collective ? [one] : one) : undefined)
            }} />
        </Form.Item>
        <Form.Item name="date" label={t('ord.date')} rules={[{ required: true }]}><DatePicker format="DD.MM.YYYY" /></Form.Item>
        {chosenType?.needs_employee !== false && (
          <Form.Item name="employees" label={chosenType?.collective ? t('ord.employeesMany') : t('ord.employeeOne')}
            extra={t('ord.employeeHint')}>
            <EmployeeSelect mode={chosenType?.collective ? 'multiple' : undefined} label={employeeName} />
          </Form.Item>
        )}
        {chosenType && <Typography.Text type="secondary">{t('org.registers.' + chosenType.register)} · {t('org.effects.' + chosenType.effect)}</Typography.Text>}
      </Form>
    </Modal>
  )
}

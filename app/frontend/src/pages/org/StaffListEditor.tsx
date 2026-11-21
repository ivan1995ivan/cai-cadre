import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Form, Input, InputNumber, Modal, Popconfirm, Row, Space, Spin,
  Statistic, Table as AntTable, Tabs, Tag, Typography, message,
} from 'antd'
import {
  ArrowLeftOutlined, BranchesOutlined, CheckOutlined, DeleteOutlined, PlusOutlined, PrinterOutlined, SaveOutlined, StopOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import Table from '../../components/AppTable'
import ExcelImport from '../../components/ExcelImport'
import PrintDialog from '../../components/PrintDialog'
import { api, errorText, fieldErrors } from '../../api/client'
import type { DiffRow, StaffList, StaffListLine, Totals } from '../../api/org'
import { useApp } from '../../auth/AppContext'
import { STATUS_COLOR } from './StaffListsPage'
import RefSelect from '../../components/RefSelect'
import SubdivisionSelect from '../../components/SubdivisionSelect'
import FormLayout from '../../components/FormLayout'
import MarkButton, { MarkedBanner } from '../../components/MarkButton'
import { useEditGuard } from '../../components/UnsavedGuard'
import { useTabTitle } from '../../layout/tabs'

const num = (v: string | number) => Number(v).toLocaleString('ro-MD', { maximumFractionDigits: 2 })

/** O versiune a statelor de personal: antetul, rândurile pe subdiviziuni, totalurile, diferențele, aprobarea și tiparul. */
export default function StaffListEditor() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPerm } = useApp()
  const [doc, setDoc] = useState<StaffList | null>(null)
  const [lines, setLines] = useState<StaffListLine[]>([])
  const [totals, setTotals] = useState<Totals | null>(null)
  const [diff, setDiff] = useState<DiffRow[]>([])
  const [header] = Form.useForm()
  const [lineForm] = Form.useForm()
  const [editingLine, setEditingLine] = useState<Partial<StaffListLine> | null>(null)
  const [versionOpen, setVersionOpen] = useState(false)
  const [versionDate, setVersionDate] = useState(dayjs())
  const [printOpen, setPrintOpen] = useState(false)

  const draft = doc?.status === 'draft' && !doc.deletion_mark  // statele marcate pentru ștergere nu se mai schimbă
  const canEdit = draft && hasPerm('org.edit')
  const { touch, clean } = useEditGuard(() => saveHeader(), !!canEdit)
  useTabTitle(doc ? { key: 'org.sl.title', params: { date: dayjs(doc.effective_from).format('DD.MM.YYYY') } } : null)

  const load = async () => {
    try {
      const [d, l, tt] = await Promise.all([
        api.get<StaffList>(`/org/staff-lists/${id}/`),
        api.get<StaffListLine[]>('/org/staff-list-lines/', { params: { staff_list: id } }),
        api.get<Totals>(`/org/staff-lists/${id}/totals/`),
      ])
      setDoc(d.data)
      setLines(l.data)
      setTotals(tt.data)
      header.setFieldsValue({ ...d.data, effective_from: dayjs(d.data.effective_from), date: dayjs(d.data.date) })
      if (d.data.previous) setDiff((await api.get<DiffRow[]>(`/org/staff-lists/${id}/diff/`)).data)
      else setDiff([])
    } catch (e) {
      message.error(errorText(e))
    }
  }
  useEffect(() => { load() }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const saveHeader = async () => {
    const v = await header.validateFields()
    try {
      await api.patch(`/org/staff-lists/${id}/`, {
        ...v, effective_from: v.effective_from.format('YYYY-MM-DD'), date: v.date.format('YYYY-MM-DD'),
      })
      message.success(t('common.saved'))
      clean()
      load()
    } catch (e) {
      header.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
      return false
    }
  }

  const act = async (action: string, body: Record<string, unknown> = {}) => {
    try {
      const r = await api.post<StaffList>(`/org/staff-lists/${id}/${action}/`, body)
      if (action === 'new-version') {
        setVersionOpen(false)
        navigate(`/staff-list/${r.data.id}`)
      } else load()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  const openLine = (line?: StaffListLine) => {
    const value = line ?? { units: '1', base_salary: '0', allowance_pct: '0', subdivision: lines.at(-1)?.subdivision }
    setEditingLine(value)
    lineForm.resetFields()
    lineForm.setFieldsValue(value)
  }

  const saveLine = async () => {
    const v = await lineForm.validateFields()
    try {
      if (editingLine?.id) await api.patch(`/org/staff-list-lines/${editingLine.id}/`, v)
      else await api.post('/org/staff-list-lines/', { ...v, staff_list: Number(id), sort: (lines.at(-1)?.sort ?? 0) + 10 })
      setEditingLine(null)
      load()
    } catch (e) {
      lineForm.setFields(fieldErrors(e) as never)
      message.error(errorText(e))
    }
  }

  const removeLine = async (line: StaffListLine) => {
    try {
      await api.delete(`/org/staff-list-lines/${line.id}/`)
      load()
    } catch (e) {
      message.error(errorText(e))
    }
  }

  // rândurile grupate pe subdiviziuni, cu subtotal (ca în anexa la decizie)
  const grouped = useMemo(() => {
    const out: { key: string; subdivision: string; units: number; fund: number; children: StaffListLine[] }[] = []
    for (const l of lines) {
      let g = out.find((x) => x.key === `s${l.subdivision}`)
      if (!g) out.push(g = { key: `s${l.subdivision}`, subdivision: l.subdivision_name, units: 0, fund: 0, children: [] })
      g.children.push(l)
      g.units += Number(l.units)
      g.fund += Number(l.monthly_fund)
    }
    return out
  }, [lines])

  if (!doc) return <Spin />


  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      <Card
        title={<Space wrap>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/staff-list')} />
          <span>{t('org.sl.title', { date: dayjs(doc.effective_from).format('DD.MM.YYYY') })}</span>
          <Tag color={STATUS_COLOR[doc.status]}>{t(`org.sl.statuses.${doc.status}`)}</Tag>
        </Space>}
        extra={<Space wrap>
          <Button icon={<PrinterOutlined />} onClick={() => setPrintOpen(true)}>{t('org.sl.print')}</Button>
          {canEdit && <Button icon={<SaveOutlined />} onClick={saveHeader}>{t('common.save')}</Button>}
          {draft && hasPerm('org.approve') && (
            <Popconfirm title={t('org.sl.approveConfirm')} onConfirm={() => act('approve')}>
              <Button type="primary" icon={<CheckOutlined />}>{t('org.sl.approve')}</Button>
            </Popconfirm>)}
          {doc.status === 'approved' && hasPerm('org.create') && (
            <Button type="primary" icon={<BranchesOutlined />} onClick={() => setVersionOpen(true)}>{t('org.sl.newVersion')}</Button>)}
          {doc.status === 'approved' && hasPerm('org.approve') && (
            <Popconfirm title={t('org.sl.cancelConfirm')} onConfirm={() => act('cancel')}>
              <Button danger icon={<StopOutlined />}>{t('org.sl.cancel')}</Button>
            </Popconfirm>)}
          {draft && hasPerm('org.delete') && <MarkButton endpoint="/org/staff-lists/" row={doc} onDone={load} text />}
        </Space>}>
        <MarkedBanner endpoint="/org/staff-lists/" row={doc} onDone={load} canUnmark={hasPerm('org.delete')} />
        {!draft && !doc.deletion_mark && <Alert showIcon type="info" style={{ marginBottom: 12 }} title={t('org.sl.lockedHint')} />}
        <Form form={header} layout="vertical" disabled={!canEdit} onValuesChange={touch}>
          <FormLayout formKey="staff-list"><Row gutter={12}>
            <Col xs={12} md={4}><Form.Item name="number" label={t('org.sl.number')}><Input /></Form.Item></Col>
            <Col xs={12} md={4}><Form.Item name="date" label={t('org.sl.date')} rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={12} md={4}><Form.Item name="effective_from" label={t('org.sl.effectiveFrom')} rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="approved_by" label={t('org.sl.approvedBy')} extra={t('org.sl.approvedByHint')}>
              <Input /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="basis" label={t('org.sl.basis')}><Input.TextArea rows={2} /></Form.Item></Col>
            <Col xs={24} md={12}><Form.Item name="notes" label={t('org.notes')}><Input.TextArea rows={2} /></Form.Item></Col>
          </Row></FormLayout>
        </Form>
        {doc.previous_label && <Typography.Text type="secondary">{t('org.sl.basedOn')}: {doc.previous_label}</Typography.Text>}
      </Card>

      <Card>
        <Tabs items={[
          { key: 'lines', label: t('org.sl.linesTab', { count: lines.length }), children: (
            <>
              <Space style={{ marginBottom: 12 }} wrap>
                {canEdit && <Button icon={<PlusOutlined />} onClick={() => openLine()}>{t('org.sl.addLine')}</Button>}
                {canEdit && <ExcelImport code="staff_lines" extra={{ staff_list: Number(id) }} allowCreateOccupations onDone={load}
                  label={t('org.sl.importLines')} />}
              </Space>
              <AntTable rowKey={(r) => ('key' in r ? (r as { key: string }).key : (r as StaffListLine).id)} size="small"
                pagination={false} expandable={{ defaultExpandAllRows: true, expandedRowKeys: grouped.map((g) => g.key) }}
                dataSource={grouped as never[]}
                onRow={(r) => ({ onDoubleClick: () => canEdit && 'id' in (r as object) && openLine(r as StaffListLine) })}
                columns={[
                  { title: t('org.sl.position'), key: 'pos', render: (_: unknown, r: never) => {
                    const row = r as StaffListLine & { subdivision: string | number; children?: unknown }
                    if (row.children) return <b>{String(row.subdivision)}</b>
                    return <Space size={4} wrap>
                      {canEdit ? <a onClick={() => openLine(row)}>{row.occupation_name}</a> : row.occupation_name}
                      {row.note && <Typography.Text type="secondary">({row.note})</Typography.Text>}
                    </Space>
                  } },
                  { title: t('org.corm'), key: 'code', width: 110, render: (_: unknown, r: never) => (r as StaffListLine).occupation_code },
                  { title: t('org.category'), key: 'cat', width: 210, render: (_: unknown, r: never) => {
                    const row = r as StaffListLine
                    return row.effective_category_name ?? ''
                  } },
                  { title: t('org.sl.units'), key: 'units', width: 90, align: 'right' as const,
                    render: (_: unknown, r: never) => <b style={{ fontWeight: 'children' in (r as object) ? 700 : 400 }}>{num((r as StaffListLine).units)}</b> },
                  { title: t('org.sl.salary'), key: 'salary', width: 120, align: 'right' as const,
                    render: (_: unknown, r: never) => 'children' in (r as object) ? '' : num((r as StaffListLine).base_salary) },
                  { title: t('org.sl.allowance'), key: 'allow', width: 90, align: 'right' as const,
                    render: (_: unknown, r: never) => 'children' in (r as object) || !Number((r as StaffListLine).allowance_pct) ? '' : `${num((r as StaffListLine).allowance_pct)}%` },
                  { title: t('org.sl.fund'), key: 'fund', width: 130, align: 'right' as const,
                    render: (_: unknown, r: never) => num('children' in (r as object) ? (r as { fund: number }).fund : (r as StaffListLine).monthly_fund) },
                  ...(canEdit ? [{ title: '', key: 'del', width: 50, render: (_: unknown, r: never) => 'children' in (r as object) ? null : (
                    <Popconfirm title={t('common.confirmDelete')} onConfirm={() => removeLine(r as StaffListLine)}>
                      <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                    </Popconfirm>) }] : []),
                ]} />
            </>
          ) },
          { key: 'totals', label: t('org.sl.totalsTab'), children: totals && (
            <Row gutter={24}>
              <Col xs={24} md={8}>
                <Space direction="vertical">
                  <Statistic title={t('org.sl.totalUnits')} value={num(totals.units)} />
                  <Statistic title={t('org.sl.totalFund')} value={num(totals.fund)} suffix="lei" />
                </Space>
              </Col>
              <Col xs={24} md={16}>
                <Descriptions bordered size="small" column={1} title={t('org.sl.byCategory')}
                  items={totals.categories.map((c) => ({ key: String(c.id ?? 'none'), label: c.name, children: num(c.units) }))} />
              </Col>
            </Row>
          ) },
          ...(doc.previous ? [{ key: 'diff', label: t('org.sl.diffTab', { count: diff.length }), children: (
            <Table<DiffRow> rowKey={(r) => `${r.subdivision}|${r.occupation}`} size="small" pagination={false} dataSource={diff}
              columns={[
                { title: t('org.subdivision'), dataIndex: 'subdivision' },
                { title: t('org.sl.position'), dataIndex: 'occupation' },
                { title: t('org.sl.change'), dataIndex: 'change', width: 140,
                  render: (v: string) => <Tag color={{ added: 'green', removed: 'red', changed: 'blue' }[v]}>{t(`org.sl.changes.${v}`)}</Tag> },
                { title: t('org.sl.unitsBefore'), dataIndex: 'units_before', width: 110, align: 'right' },
                { title: t('org.sl.unitsAfter'), dataIndex: 'units_after', width: 110, align: 'right' },
                { title: t('org.sl.salaryBefore'), dataIndex: 'salary_before', width: 120, align: 'right' },
                { title: t('org.sl.salaryAfter'), dataIndex: 'salary_after', width: 120, align: 'right' },
              ]} />
          ) }] : []),
        ]} />
      </Card>

      <Modal open={!!editingLine} width={680} onOk={saveLine} onCancel={() => setEditingLine(null)}
        title={editingLine?.id ? t('common.edit') : t('org.sl.addLine')}>
        <Form form={lineForm} layout="vertical">
          <FormLayout formKey="staff-list-line"><Form.Item name="subdivision" label={t('org.subdivision')} rules={[{ required: true }]}>
            <SubdivisionSelect allowClear={false} />
          </Form.Item>
          <Form.Item name="occupation" label={t('org.sl.position')} rules={[{ required: true }]}>
            <RefSelect spec="occupation" allowClear={false} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="units" label={t('org.sl.units')} rules={[{ required: true }]}>
              <InputNumber min={0.01} step={0.25} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="base_salary" label={t('org.sl.salary')}>
              <InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="allowance_pct" label={t('org.sl.allowance')}>
              <InputNumber min={0} max={500} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item name="category" label={t('org.sl.categoryOverride')} extra={t('org.sl.categoryOverrideHint')}>
            <RefSelect spec={{ dict: 'staff_category' }} />
          </Form.Item>
          <Form.Item name="note" label={t('org.notes')}><Input /></Form.Item></FormLayout>
        </Form>
      </Modal>

      <Modal open={versionOpen} title={t('org.sl.newVersion')} onCancel={() => setVersionOpen(false)}
        onOk={() => act('new-version', { effective_from: versionDate.format('YYYY-MM-DD') })}>
        <Typography.Paragraph>{t('org.sl.newVersionHint')}</Typography.Paragraph>
        <DatePicker format="DD.MM.YYYY" value={versionDate} onChange={(d) => d && setVersionDate(d)} />
      </Modal>

      <PrintDialog open={printOpen} onClose={() => setPrintOpen(false)} docType="staff_list" url={`/org/staff-lists/${id}/print/`}
        params={{}} optionKeys={['show_salary', 'show_fund', 'show_categories']} title={t('org.sl.print')} />
    </Space>
  )
}

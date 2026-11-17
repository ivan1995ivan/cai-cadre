import { useTranslation } from 'react-i18next'
import { Descriptions, Space, Table, Typography } from 'antd'
import dayjs from 'dayjs'

import CrudTable from '../../components/CrudTable'
import { useFetch } from '../../api/hooks'
import { ADJUSTMENT_KINDS, RIGHT_REASONS, fmtDays, type Balance, type WorkYear } from '../../api/leave'
import { useApp } from '../../auth/AppContext'
import { RequestsTab } from '../leave/LeavePage'
import SickLeavePage from '../leave/SickLeavePage'

const d = (v: unknown) => (v ? dayjs(String(v)).format('DD.MM.YYYY') : '')

/** Fila „Concedii” din fișa angajatului: soldul pe anii de muncă, drepturile suplimentare, corectările, cererile, foile de boală. */
export default function LeaveTab({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const canView = hasPerm('leave.view')
  const { data: bal, reload } = useFetch<Balance>(canView ? `/leave/balance/${employee}/` : null)
  const canEdit = hasPerm('leave.edit')

  return (
    <Space orientation="vertical" style={{ width: '100%' }} size={20}>
      {bal && <Descriptions size="small" column={{ xs: 1, md: 4 }} bordered items={[
        { key: 'start', label: t('lv.hired'), children: d(bal.start) },
        { key: 'cur', label: t('lv.workYear'), children: bal.current ? `${d(bal.current.from)} – ${d(bal.current.to)}` : '' },
        { key: 'rem', label: t('lv.remaining'), children: <Typography.Text strong type={bal.remaining < 0 ? 'danger' : undefined}>{fmtDays(bal.remaining)}</Typography.Text> },
        { key: 'av', label: t('lv.available'), children: fmtDays(bal.available) },
      ]} />}
      {canView && <div>
        <Typography.Text strong>{t('lv.tab.years')}</Typography.Text>
        <Table<WorkYear> size="small" rowKey="from" pagination={false} dataSource={bal?.years ?? []} style={{ marginTop: 6 }}
          summary={() => bal && bal.opening ? <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={8}>{t('lv.tab.opening')}</Table.Summary.Cell>
            <Table.Summary.Cell index={1} align="right">{fmtDays(bal.opening)}</Table.Summary.Cell>
          </Table.Summary.Row> : null}
          columns={[
            { title: t('lv.workYear'), key: 'y', render: (_: unknown, r) => <>{d(r.from)} – {d(r.to)}{r.skipped
              ? <Typography.Text type="secondary"> ({t('lv.tab.skipped', { days: r.skipped })})</Typography.Text> : null}</> },
            { title: t('lv.tab.base'), dataIndex: 'base', width: 70, align: 'right' },
            { title: t('lv.tab.extra'), dataIndex: 'extra', width: 90, align: 'right' },
            { title: t('lv.tab.personal'), dataIndex: 'personal', width: 90, align: 'right' },
            { title: t('lv.entitled'), dataIndex: 'entitled', width: 80, align: 'right' },
            { title: t('lv.accrued'), dataIndex: 'accrued', width: 90, align: 'right', render: fmtDays },
            { title: t('lv.tab.used'), dataIndex: 'used', width: 80, align: 'right', render: fmtDays },
            { title: t('lv.tab.adjusted'), dataIndex: 'adjusted', width: 90, align: 'right', render: fmtDays },
            { title: t('lv.remaining'), dataIndex: 'remaining', width: 90, align: 'right',
              render: (v: number) => <Typography.Text strong type={v < 0 ? 'danger' : undefined}>{fmtDays(v)}</Typography.Text> },
          ]} />
        <Typography.Paragraph type="secondary" style={{ marginTop: 6 }}>{t('lv.tab.hint')}</Typography.Paragraph>
      </div>}
      {canView && <CrudTable endpoint="/leave/rights/" params={{ employee }} canEdit={canEdit} defaults={{ employee }} onChanged={reload}
        title={<Typography.Text strong>{t('lv.tab.rights')}</Typography.Text>}
        fields={[
          { key: 'employee', label: '', hidden: true },
          { key: 'reason', label: t('lv.tab.reason'), type: 'select', width: 260, required: true,
            options: RIGHT_REASONS.map((k) => ({ value: k, label: t(`lv.reasons.${k}`) })), render: (_v, r) => String(r.reason_label ?? '') },
          { key: 'days', label: t('lv.tab.daysPerYear'), type: 'number', width: 100, required: true },
          { key: 'date_from', label: t('staff.sen.from'), type: 'date', width: 110 },
          { key: 'date_to', label: t('staff.sen.to'), type: 'date', width: 110 },
          { key: 'note', label: t('org.notes') },
        ]} />}
      {canView && <CrudTable endpoint="/leave/adjustments/" params={{ employee }} canEdit={canEdit} defaults={{ employee, kind: 'opening' }}
        onChanged={reload}
        title={<Typography.Text strong>{t('lv.tab.adjustments')}</Typography.Text>}
        fields={[
          { key: 'employee', label: '', hidden: true },
          { key: 'kind', label: t('lv.kind'), type: 'select', width: 220, required: true,
            options: ADJUSTMENT_KINDS.map((k) => ({ value: k, label: t(`lv.adjKinds.${k}`) })), render: (_v, r) => String(r.kind_label ?? '') },
          { key: 'date', label: t('ord.date'), type: 'date', width: 110, required: true },
          { key: 'work_year_from', label: t('lv.tab.workYearStart'), type: 'date', width: 150, extra: t('lv.tab.workYearStartHint') },
          { key: 'days', label: t('lv.tab.adjDays'), type: 'number', width: 100, required: true, render: (v) => fmtDays(v as string) },
          { key: 'note', label: t('org.notes'), render: (v, r) => {
            const o = r.order as { label: string } | null
            return o ? `${String(v ?? '')} ${t('lv.tab.byOrder', { label: o.label })}`.trim() : String(v ?? '')
          } },
        ]} />}
      {hasPerm('leave.view') && <div>
        <Typography.Text strong>{t('lv.tabs.requests')}</Typography.Text>
        <div style={{ marginTop: 6 }}><RequestsTab employee={employee} /></div>
      </div>}
      {hasPerm('sick_leave.view') && <div>
        <Typography.Text strong>{t('menu.sickLeave')}</Typography.Text>
        <div style={{ marginTop: 6 }}><SickLeavePage employee={employee} /></div>
      </div>}
    </Space>
  )
}

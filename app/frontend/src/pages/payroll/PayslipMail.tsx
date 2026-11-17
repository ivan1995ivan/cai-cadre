import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Modal, Progress, Space, Table, Tag, Typography, message } from 'antd'
import { MailOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'
import type { PayslipMailResult, PayslipMailSummary } from '../../api/payroll'

const STATUS_COLOR: Record<string, string> = { sent: 'green', skipped: 'default', error: 'red' }
const CHUNK = 20

/** Trimiterea fluturașilor îndreptării pe e-mail: cine îi poate primi, apoi trimiterea pe bucăți, cu progresul și rezultatul
 *  fiecăruia. */
export default function PayslipMail({ paymentId, onClose }: { paymentId: number; onClose: () => void }) {
  const { t } = useTranslation()
  const { data, loading, reload } = useFetch<PayslipMailSummary>(`/payroll/payments/${paymentId}/payslip-mail/`)
  const [selected, setSelected] = useState<number[] | null>(null)
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null)
  const [results, setResults] = useState<Record<number, PayslipMailResult>>({})
  const ready = (data?.rows ?? []).filter((r) => !r.problem).map((r) => r.employee)
  const chosen = selected ?? ready
  const send = async () => {
    const ids = [...chosen]
    setProgress({ done: 0, total: ids.length })
    for (let i = 0; i < ids.length; i += CHUNK) {
      try {
        const r = await api.post<{ results: PayslipMailResult[] }>(`/payroll/payments/${paymentId}/payslip-mail/`, { employees: ids.slice(i, i + CHUNK) })
        setResults((cur) => ({ ...cur, ...Object.fromEntries(r.data.results.map((x) => [x.employee, x])) }))
      } catch (e) {
        message.error(errorText(e))
        break
      }
      setProgress({ done: Math.min(i + CHUNK, ids.length), total: ids.length })
    }
    reload()
  }
  const sentNow = Object.values(results).filter((x) => x.status === 'sent').length
  return (
    <Modal open title={t('pay.mailTitle')} onCancel={onClose} width="min(900px, 96vw)"
      footer={<Space>
        <Button onClick={onClose}>{t('common.close')}</Button>
        <Button type="primary" icon={<MailOutlined />} disabled={!data?.smtp || !chosen.length || (!!progress && progress.done < progress.total)}
          onClick={send}>{t('pay.mailSend', { count: chosen.length })}</Button>
      </Space>}>
      {data && !data.smtp && <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('pay.mailNoSmtp')} />}
      <Typography.Paragraph type="secondary">{t('pay.mailHint')}</Typography.Paragraph>
      {progress && <Progress percent={Math.round((progress.done / Math.max(progress.total, 1)) * 100)}
        format={() => `${progress.done} / ${progress.total} · ${t('pay.mailSent', { count: sentNow })}`} style={{ marginBottom: 12 }} />}
      <Table size="small" rowKey="employee" loading={loading} dataSource={data?.rows ?? []} pagination={{ pageSize: 50, showSizeChanger: false }}
        rowSelection={{ selectedRowKeys: chosen, onChange: (keys) => setSelected(keys.map(Number)), getCheckboxProps: (r) => ({ disabled: !!r.problem }) }}
        columns={[
          { title: t('staff.fullName'), dataIndex: 'name' },
          { title: 'E-mail', dataIndex: 'email', width: 220 },
          { title: t('pay.mailStatus'), key: 'st', width: 260, render: (_: unknown, r) => {
            const now = results[r.employee]
            if (now) return <Tag color={STATUS_COLOR[now.status]}>{t(`pay.mailStatuses.${now.status}`)}{now.message ? ` — ${now.message}` : ''}</Tag>
            if (r.problem) return <Typography.Text type="warning">{r.problem}</Typography.Text>
            if (r.last) return <Typography.Text type="secondary">{t(`pay.mailStatuses.${r.last.status}`)} {dayjs(r.last.sent_at).format('DD.MM.YYYY HH:mm')}</Typography.Text>
            return null
          } },
        ]} />
    </Modal>
  )
}

import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Checkbox, Modal, Space, Statistic, Table, Typography, Upload, message } from 'antd'
import { DownloadOutlined, FileExcelOutlined, InboxOutlined } from '@ant-design/icons'

import { api, errorText } from '../api/client'
import type { ImportResult } from '../api/org'

/**
 * Importul din Excel, în doi pași: se încarcă fișierul și se vede rezultatul încercării (ce se adaugă, ce se actualizează,
 * erorile pe rânduri), apoi „Importă” scrie totul într-o tranzacție. Șablonul (antetul + exemplu) se descarcă de aici.
 */
export default function ExcelImport({ code, url = '/org/import/', extra = {}, label, onDone, allowCreateOccupations, children }: {
  code: string
  url?: string
  extra?: Record<string, string | number>
  label?: string
  onDone?: () => void
  allowCreateOccupations?: boolean
  children?: ReactNode
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [createOcc, setCreateOcc] = useState(false)

  const send = async (dryRun: boolean, f = file) => {
    if (!f) return
    const form = new FormData()
    form.append('file', f)
    form.append('dry_run', dryRun ? '1' : '0')
    if (createOcc) form.append('create_occupations', '1')
    Object.entries(extra).forEach(([k, v]) => form.append(k, String(v)))
    setBusy(true)
    try {
      const r = await api.post<ImportResult>(`${url}${code}/`, form)
      setResult(r.data)
      if (r.data.saved) {
        message.success(t('excel.done', { created: r.data.created, updated: r.data.updated }))
        onDone?.()
        setOpen(false)
        setResult(null)
        setFile(null)
      }
    } catch (e) {
      message.error(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const download = async () => {
    try {
      const r = await api.get(`${url}${code}/template/`, { responseType: 'blob' })
      const href = URL.createObjectURL(r.data as Blob)
      const a = document.createElement('a')
      a.href = href
      a.download = `sablon-${code}.xlsx`
      a.click()
      URL.revokeObjectURL(href)
    } catch (e) {
      message.error(errorText(e))
    }
  }

  return (
    <>
      <Button icon={<FileExcelOutlined />} onClick={() => setOpen(true)}>{label ?? t('excel.import')}</Button>
      <Modal open={open} width={760} title={label ?? t('excel.import')} onCancel={() => { setOpen(false); setResult(null); setFile(null) }}
        footer={[
          <Button key="tpl" icon={<DownloadOutlined />} onClick={download}>{t('excel.template')}</Button>,
          <Button key="cancel" onClick={() => setOpen(false)}>{t('common.cancel')}</Button>,
          <Button key="go" type="primary" disabled={!result?.ok || !file} loading={busy} onClick={() => send(false)}>
            {t('excel.confirm')}
          </Button>,
        ]}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>{t('excel.hint')}</Typography.Paragraph>
          {children}
          {allowCreateOccupations && (
            <Checkbox checked={createOcc} onChange={(e) => { setCreateOcc(e.target.checked); setResult(null) }}>
              {t('excel.createOccupations')}
            </Checkbox>
          )}
          <Upload.Dragger accept=".xlsx" maxCount={1} showUploadList={false}
            beforeUpload={(f) => { setFile(f); setResult(null); send(true, f); return false }}>
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p>{file ? file.name : t('excel.drop')}</p>
          </Upload.Dragger>
          {result && (
            <>
              {result.detail && <Alert type="error" showIcon title={result.detail} />}
              <Space size="large">
                <Statistic title={t('excel.rows')} value={result.rows} />
                <Statistic title={t('excel.created')} value={result.created} />
                <Statistic title={t('excel.updated')} value={result.updated} />
                <Statistic title={t('excel.errors')} value={result.errors.length}
                  styles={{ content: { color: result.errors.length ? '#cf1322' : undefined } }} />
              </Space>
              {result.ok && <Alert type="success" showIcon title={t('excel.readyToImport')} />}
              {result.errors.length > 0 && (
                <Table size="small" rowKey={(r) => `${r.row}-${r.error}`} pagination={false} scroll={{ y: 240 }}
                  dataSource={result.errors}
                  columns={[{ title: t('excel.row'), dataIndex: 'row', width: 70 }, { title: t('excel.error'), dataIndex: 'error' }]} />
              )}
            </>
          )}
        </Space>
      </Modal>
    </>
  )
}

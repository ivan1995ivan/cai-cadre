import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input, Modal, Typography } from 'antd'
import Table from './AppTable'
import type { ColumnsType } from 'antd/es/table'

import type { Paged } from '../api/client'
import { useFetch } from '../api/hooks'

/**
 * Forma de alegere din listă (ca în 1C, butonul „…” de lângă câmp): căutare, pagini, clic pe rând = alege.
 * Lista vine de pe server (`endpoint`), cu `?search=`.
 */
export default function PickerModal<T extends { id: number }>({ open, title, endpoint, params, columns, onPick, onClose }: {
  open: boolean
  title: string
  endpoint: string
  params?: Record<string, unknown>
  columns: ColumnsType<T>
  onPick: (row: T) => void
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  useEffect(() => {
    if (open) {
      setSearch('')
      setPage(1)
    }
  }, [open])
  const { data, loading } = useFetch<Paged<T>>(open ? endpoint : null, { ...params, search: search || undefined, page, page_size: 15 })
  return (
    <Modal open={open} title={title} onCancel={onClose} footer={null} width="min(1200px, 96vw)" destroyOnHidden>
      <Input.Search autoFocus allowClear placeholder={t('picker.search')} style={{ marginBottom: 12 }}
        onSearch={(v) => { setSearch(v); setPage(1) }} onChange={(e) => { if (!e.target.value) { setSearch(''); setPage(1) } }} />
      <Table<T> size="small" rowKey="id" loading={loading} dataSource={data?.results} columns={columns} scroll={{ x: 'max-content' }}
        pagination={{ current: page, total: data?.count, pageSize: 15, onChange: setPage, showSizeChanger: false }}
        onRow={(row) => ({ onClick: () => onPick(row), style: { cursor: 'pointer' } })} />
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('picker.hint')}</Typography.Text>
    </Modal>
  )
}

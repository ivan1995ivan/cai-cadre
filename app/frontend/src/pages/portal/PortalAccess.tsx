import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Descriptions, Modal, Popconfirm, Space, Tag, Typography, message } from 'antd'
import { IdcardOutlined, TeamOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import AppTable from '../../components/AppTable'
import { api, errorText } from '../../api/client'
import { useFetch } from '../../api/hooks'

interface Access { username: string; active: boolean; last_login: string | null }
interface Created { employee?: string; tab_number?: string; username: string; password: string }

/** Butonul „Cabinet” din fișa angajatului: contul de intrare în cabinet (rolul „Angajat”), parola temporară, oprirea accesului. */
export function PortalAccessButton({ employee }: { employee: number }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data, reload } = useFetch<Access>(open ? `/portal/access/${employee}/` : null)
  const [created, setCreated] = useState<Created | null>(null)
  const create = async () => {
    try {
      const r = await api.post<Created>(`/portal/access/${employee}/`)
      setCreated(r.data)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const disable = async () => {
    try {
      await api.delete(`/portal/access/${employee}/`)
      setCreated(null)
      reload()
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <>
      <Button icon={<IdcardOutlined />} onClick={() => { setCreated(null); setOpen(true) }}>{t('pt.access.button')}</Button>
      <Modal open={open} title={t('pt.access.title')} onCancel={() => setOpen(false)} footer={null} destroyOnHidden>
        <Typography.Paragraph type="secondary">{t('pt.access.hint')}</Typography.Paragraph>
        {data && <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
          <Descriptions.Item label={t('pt.access.username')}>{data.username || '—'}</Descriptions.Item>
          <Descriptions.Item label={t('pt.status')}>{data.username
            ? <Tag color={data.active ? 'green' : 'red'}>{data.active ? t('pt.access.on') : t('pt.access.off')}</Tag> : <Tag>{t('pt.access.none')}</Tag>}</Descriptions.Item>
          {data.last_login && <Descriptions.Item label={t('pt.access.lastLogin')}>{dayjs(data.last_login).format('DD.MM.YYYY HH:mm')}</Descriptions.Item>}
        </Descriptions>}
        {created && <Alert type="success" showIcon style={{ marginBottom: 12 }} title={t('pt.access.created')}
          description={<Typography.Text copyable={{ text: `${created.username} / ${created.password}` }}>
            {t('pt.access.username')}: <b>{created.username}</b> · {t('pt.access.password')}: <b>{created.password}</b></Typography.Text>} />}
        <Space>
          <Button type="primary" onClick={create}>{data?.username ? t('pt.access.newPassword') : t('pt.access.create')}</Button>
          {data?.active && <Popconfirm title={t('pt.access.offConfirm')} onConfirm={disable}><Button danger>{t('pt.access.disable')}</Button></Popconfirm>}
        </Space>
      </Modal>
    </>
  )
}

/** Lista angajaților: conturi pentru toți cei fără cont (parolele se văd o singură dată — descărcați lista în Excel). */
export function BulkAccessButton() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Created[] | null>(null)
  const run = async () => {
    try {
      const r = await api.post<Created[]>('/portal/access/bulk/')
      setRows(r.data)
    } catch (e) {
      message.error(errorText(e))
    }
  }
  return (
    <>
      <Popconfirm title={t('pt.access.bulkConfirm')} onConfirm={run}>
        <Button icon={<TeamOutlined />}>{t('pt.access.bulk')}</Button>
      </Popconfirm>
      <Modal open={rows !== null} title={t('pt.access.bulkTitle', { count: rows?.length ?? 0 })} onCancel={() => setRows(null)} footer={null}
        width={760} destroyOnHidden>
        <Alert type="warning" showIcon style={{ marginBottom: 12 }} title={t('pt.access.bulkHint')} />
        <AppTable<Created> rowKey="username" size="small" dataSource={rows ?? []} pagination={false} exportName={t('pt.access.bulkFile')}
          columns={[
            { title: t('staff.tab'), dataIndex: 'tab_number', width: 90 },
            { title: t('staff.fullName'), dataIndex: 'employee' },
            { title: t('pt.access.username'), dataIndex: 'username' },
            { title: t('pt.access.password'), dataIndex: 'password' },
          ]} />
      </Modal>
    </>
  )
}

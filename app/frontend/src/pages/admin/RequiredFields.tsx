import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Checkbox, Col, Row, Space, Tag, Typography, message } from 'antd'

import { api, errorText } from '../../api/client'
import { useApp } from '../../auth/AppContext'
import { useUnsavedGuard } from '../../components/UnsavedGuard'

interface Doc { key: string; name_ro: string; name_ru: string; when: 'save' | 'post'; fields: { name: string; label: string; label_ru?: string }[] }

/** Administrare → Setări → Câmpuri obligatorii: bife pe documente și clasificatoare. */
export default function RequiredFields() {
  const { t, i18n } = useTranslation()
  const { hasPerm } = useApp()
  const canEdit = hasPerm('settings.edit')
  const [docs, setDocs] = useState<Doc[]>([])
  const [selected, setSelected] = useState<Record<string, string[]>>({})
  const [dirty, setDirty] = useState(false)
  useUnsavedGuard(dirty && canEdit, () => save())
  useEffect(() => {
    api.get<{ docs: Doc[]; selected: Record<string, string[]> }>('/settings/required-fields/').then((r) => { setDocs(r.data.docs); setSelected(r.data.selected) })
  }, [])
  const toggle = (doc: string, field: string, on: boolean) => {
    const cur = new Set(selected[doc] ?? [])
    if (on) cur.add(field)
    else cur.delete(field)
    setSelected({ ...selected, [doc]: [...cur] })
    setDirty(true)
  }
  const save = async () => {
    try {
      const { data } = await api.put<{ selected: Record<string, string[]> }>('/settings/required-fields/', { selected })
      setSelected(data.selected)
      setDirty(false)
      message.success(t('common.saved'))
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.requiredFields')}</Typography.Title>
        {canEdit && <Button type="primary" disabled={!dirty} onClick={save}>{t('common.save')}</Button>}
      </Space>
      <Alert type="info" showIcon title={t('requiredFields.hint')} />
      <Row gutter={[16, 16]}>
        {docs.map((d) => (
          <Col key={d.key} xs={24} md={12} xl={8}>
            <Card size="small" title={<Space>{i18n.language === 'ru' ? d.name_ru : d.name_ro}
              <Tag color={d.when === 'save' ? 'blue' : 'purple'}>{t(`requiredFields.when.${d.when}`)}</Tag></Space>}>
              <Space orientation="vertical">
                {d.fields.map((f) => (
                  <Checkbox key={f.name} disabled={!canEdit} checked={(selected[d.key] ?? []).includes(f.name)}
                    onChange={(e) => toggle(d.key, f.name, e.target.checked)}>{i18n.language === 'ru' ? f.label_ru ?? f.label : f.label}</Checkbox>
                ))}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Space>
  )
}

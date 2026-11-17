import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Alert, Button, Card, Col, Input, Popconfirm, Row, Segmented, Select, Space, Tree, Typography, message } from 'antd'
import type { TreeProps } from 'antd'
import { EyeInvisibleOutlined, PlusOutlined, UndoOutlined } from '@ant-design/icons'

import { api, errorText } from '../../api/client'
import { useApp } from '../../auth/AppContext'
import { useUnsavedGuard } from '../../components/UnsavedGuard'
import {
  ALL_ITEMS, completeSections, GROUPS, hiddenItems, type MenuGroup, type MenuSection, type MenuSide, SECTION_ICONS, sectionKeys, useSectionName,
} from '../../layout/menu'

const ITEM_ICON = Object.fromEntries(ALL_ITEMS.map((i) => [i.key, i.icon]))
const POOL = 'pool'

/** Cheile arborelui: „s:sec” secțiunea, „g:sec:grupa” grupa, „i|sec|grupa|funcția” funcția dintr-o grupă (aceeași funcție
 * poate fi în mai multe grupe / secțiuni), „i|pool||funcția” la neafișate. */
const leafKey = (sec: string, group: string, k: string) => `i|${sec}|${group}|${k}`
const parseLeaf = (key: string) => {
  const [, sec, group, k] = key.split('|')
  return { sec, group: group as MenuGroup | '', k }
}

/**
 * Meniul principal: secțiunile și, în fiecare, grupele Registre / Rapoarte cu funcțiile lor (setările nu sunt aici — stau toate
 * la Administrare → Setări). Funcțiile se trag cu mouse-ul dintr-o grupă în alta (și în altă secțiune) sau se mută în ordine;
 * aceeași funcție poate sta în mai multe locuri (de ex. MUNCA-1 la Salarii și la Rapoarte) — se trage din „Funcții neafișate”
 * sau se mută. Secțiunile se
 * adaugă, se redenumesc (RO / RU), primesc iconiță și se ordonează tot prin tragere. Funcțiile care nu sunt nicăieri în meniu
 * stau la „Funcții neafișate”; o funcție trasă acolo dispare din grupa din care a fost luată (rămâne în program: favorite,
 * adresă). Cine ce vede se bifează la fiecare rol (Administrare → Setări → Roluri).
 */
export default function MenuEditor() {
  const { t } = useTranslation()
  const { hasPerm, languages } = useApp()
  const canEdit = hasPerm('settings.edit')
  const name = useSectionName()
  const [sections, setSections] = useState<MenuSection[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  useUnsavedGuard(dirty && canEdit, () => save())
  const [defaultSide, setDefaultSide] = useState<MenuSide>('top')

  const load = () => api.get<{ sections?: MenuSection[]; layout?: MenuSide }>('/settings/menu/').then((r) => {
    setSections(completeSections(r.data.sections))
    setDefaultSide(r.data.layout === 'left' ? 'left' : 'top')
    setDirty(false)
  })
  const saveSide = (v: MenuSide) => api.put('/settings/menu/', { layout: v })
    .then(() => { setDefaultSide(v); message.success(t('common.saved')) }).catch((e) => message.error(errorText(e)))
  useEffect(() => { load() }, [])
  const change = (next: MenuSection[]) => { setSections(next); setDirty(true) }

  const leaf = (sec: string, group: string, k: string) => ({ key: leafKey(sec, group, k), title: t(`menu.${k}`), icon: ITEM_ICON[k], isLeaf: true })
  const hidden = hiddenItems(sections)

  const treeData = [
    ...sections.map((s) => ({
      key: `s:${s.key}`, title: <b>{name(s)}</b>, icon: SECTION_ICONS[s.icon] ?? SECTION_ICONS.folder,
      children: GROUPS.map((g) => ({
        key: `g:${s.key}:${g}`, title: <i>{t(`menuGroups.${g}`)}</i>, selectable: false,
        children: s[g].map((k) => leaf(s.key, g, k)),
      })),
    })),
    { key: POOL, title: <b>{t('mainMenu.pool')}</b>, icon: <EyeInvisibleOutlined />, selectable: false, children: hidden.map((i) => leaf(POOL, '', i.key)) },
  ]

  const isSection = (key: string) => key.startsWith('s:')
  const isGroup = (key: string) => key.startsWith('g:')
  const isLeaf = (key: string) => key.startsWith('i|')
  const allowDrop: TreeProps['allowDrop'] = ({ dragNode, dropNode, dropPosition }) => {
    const drag = String(dragNode.key)
    const drop = String(dropNode.key)
    if (isGroup(drag) || drag === POOL) return false
    if (isSection(drag)) return isSection(drop) && dropPosition !== 0  // secțiunile doar între secțiuni
    // funcția: în grupă / secțiune (prima din Registre) / la neafișate, sau între funcții
    if (isGroup(drop) || isSection(drop) || drop === POOL) return dropPosition === 0
    return isLeaf(drop)
  }

  const onDrop: TreeProps['onDrop'] = (info) => {
    const dragKey = String(info.dragNode.key)
    const dropKey = String(info.node.key)
    const pos = info.node.pos.split('-')
    const after = info.dropPosition - Number(pos[pos.length - 1]) > 0  // după nodul țintă
    const next = sections.map((s) => ({ ...s, items: [...s.items], reports: [...s.reports] }))
    if (isSection(dragKey)) {
      const from = next.findIndex((s) => `s:${s.key}` === dragKey)
      const [moved] = next.splice(from, 1)
      let to = next.findIndex((s) => `s:${s.key}` === dropKey)
      if (after) to += 1
      next.splice(to, 0, moved)
    } else {
      const source = parseLeaf(dragKey)
      const k = source.k
      // se scoate doar din grupa de unde a fost luată (în alte locuri rămâne)
      if (source.sec !== POOL && source.group) {
        const from = next.find((s) => s.key === source.sec)
        if (from) from[source.group] = from[source.group].filter((x) => x !== k)
      }
      const put = (sec: string, group: MenuGroup, at?: number) => {
        const target = next.find((s) => s.key === sec)
        if (!target) return
        const list = target[group].filter((x) => x !== k)  // într-o grupă o funcție stă o singură dată
        list.splice(at === undefined ? 0 : Math.min(at, list.length), 0, k)
        target[group] = list
      }
      if (isGroup(dropKey)) {
        const [, secKey, g] = dropKey.split(':')
        put(secKey, g as MenuGroup)  // în grupă, prima
      } else if (isSection(dropKey)) {
        put(dropKey.slice(2), 'items')  // în secțiune: prima din Registre
      } else if (isLeaf(dropKey)) {
        const target = parseLeaf(dropKey)
        if (target.sec !== POOL && target.group) {
          const list = next.find((s) => s.key === target.sec)?.[target.group] ?? []
          const at = list.indexOf(target.k)
          put(target.sec, target.group, at < 0 ? undefined : at + (after ? 1 : 0))
        }
      }
      // pe POOL sau lângă o funcție neafișată: doar scoaterea din grupa sursă
    }
    change(next)
  }

  const save = async () => {
    try {
      const { data } = await api.put<{ sections: MenuSection[] }>('/settings/menu/', { sections })
      setSections(completeSections(data.sections))
      setDirty(false)
      message.success(t('mainMenu.saved'))
    } catch (e) {
      message.error(errorText(e))
      return false
    }
  }
  const reset = async () => {
    try {
      await api.put('/settings/menu/', { sections: null })
      await load()
      message.success(t('mainMenu.saved'))
    } catch (e) {
      message.error(errorText(e))
    }
  }
  const addSection = () => {
    let n = 1
    while (sections.some((s) => s.key === `sectiune-${n}`)) n += 1
    const key = `sectiune-${n}`
    change([...sections, { key, name_ro: t('mainMenu.newSection'), name_ru: '', icon: 'folder', items: [], reports: [] }])
    setSelected(`s:${key}`)
  }
  const current = sections.find((s) => `s:${s.key}` === selected)
  const count = current ? sectionKeys(current).length : 0
  const patchCurrent = (patch: Partial<MenuSection>) => change(sections.map((s) => (s === current ? { ...s, ...patch } : s)))

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('menu.mainMenu')}</Typography.Title>
      <Alert type="info" showIcon title={t('mainMenu.hint')} description={t('mainMenu.poolHint')} />
      <Space wrap>
        <Typography.Text>{t('acc.menuDefault')}</Typography.Text>
        <Segmented<MenuSide> value={defaultSide} disabled={!canEdit} onChange={saveSide}
          options={[{ value: 'top', label: t('acc.menuTop') }, { value: 'left', label: t('acc.menuLeft') }]} />
        <Typography.Text type="secondary">{t('acc.menuDefaultHint')}</Typography.Text>
      </Space>
      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card size="small" extra={canEdit && (
            <Space wrap>
              <Button icon={<PlusOutlined />} onClick={addSection}>{t('mainMenu.addSection')}</Button>
              <Popconfirm title={t('mainMenu.resetConfirm')} onConfirm={reset}><Button icon={<UndoOutlined />}>{t('mainMenu.reset')}</Button></Popconfirm>
              <Button type="primary" disabled={!dirty} onClick={save}>{t('common.save')}</Button>
            </Space>
          )}>
            <Tree showIcon blockNode defaultExpandAll treeData={treeData}
              draggable={canEdit ? { icon: false, nodeDraggable: (node) => !isGroup(String(node.key)) && node.key !== POOL } : false}
              key={sections.length} allowDrop={allowDrop} onDrop={onDrop}
              selectedKeys={selected ? [selected] : []} onSelect={(keys) => setSelected(keys.length ? String(keys[0]) : null)} />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card size="small" title={t('mainMenu.section')}>
            {!current ? <Typography.Text type="secondary">{t('mainMenu.pickSection')}</Typography.Text> : (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Input addonBefore="RO" disabled={!canEdit} value={current.name_ro} placeholder={t(`menuSections.${current.key}`, { defaultValue: '' })}
                  onChange={(e) => patchCurrent({ name_ro: e.target.value })} />
                {languages.includes('ru') && <Input addonBefore="RU" disabled={!canEdit} value={current.name_ru} onChange={(e) => patchCurrent({ name_ru: e.target.value })} />}
                <Select disabled={!canEdit} value={current.icon} style={{ width: '100%' }} onChange={(v) => patchCurrent({ icon: v })}
                  options={Object.entries(SECTION_ICONS).map(([k, icon]) => ({ value: k, label: <Space>{icon}{t(`mainMenu.icons.${k}`, { defaultValue: k })}</Space> }))} />
                <Typography.Text type="secondary">{t('mainMenu.items', { count })}</Typography.Text>
                {canEdit && (
                  <Popconfirm title={t('common.confirmDelete')} disabled={count > 0}
                    onConfirm={() => { change(sections.filter((s) => s !== current)); setSelected(null) }}>
                    <Button danger disabled={count > 0}>{t('mainMenu.deleteSection')}</Button>
                  </Popconfirm>
                )}
                {count > 0 && <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('mainMenu.deleteHint')}</Typography.Text>}
              </Space>
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

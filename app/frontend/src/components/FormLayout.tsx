import { Children, Fragment, cloneElement, isValidElement, useEffect, useMemo, useRef, useState, type ReactElement, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Button, Card, Checkbox, Col, Divider, Drawer, Empty, Form, Grid, Input, InputNumber, Popconfirm, Radio, Row, Select, Space, Tag, Tooltip, Tree,
  Typography, message,
} from 'antd'
import type { TreeDataNode, TreeProps } from 'antd'
import {
  AppstoreOutlined, ArrowDownOutlined, ArrowUpOutlined, ClearOutlined, ColumnWidthOutlined, DeleteOutlined, EyeInvisibleOutlined, FolderAddOutlined,
  FolderOutlined, LayoutOutlined,
} from '@ant-design/icons'

import { prefKey, useUiDefault, useUiPref } from '../api/uiPrefs'
import { useApp } from '../auth/AppContext'

/**
 * Forma aranjată de utilizator, ca „Настройка формы” din 1C (adusă din CRM acoperiș gard). Se pune în <Form> în jurul
 * câmpurilor, care rămân scrise ca până acum:
 *   <Form ...><FormLayout formKey="employee">…câmpurile…</FormLayout></Form>
 * Câmpurile (Form.Item cu `name`) se iau singure din rânduri și coloane; titlurile secțiunilor (Divider) devin grupe;
 * restul (un rând de bife, un mesaj, o componentă cu câmpurile ei) rămân blocuri întregi. Fără aranjare salvată forma
 * arată exact ca în cod. Butonul „Forma” deschide editorul: grupe orizontale / verticale, una în alta, cu titlu, chenar și
 * lățime (din 24); câmpurile se trag între grupe, se ascund (cele obligatorii nu) și primesc lățimea lor. Aranjarea e a
 * fiecăruia; administratorul o poate salva și pentru toți (cine nu și-a făcut-o pe a lui).
 */

export interface LayoutGroup {
  type: 'group'
  id: string
  title?: string
  direction: 'vertical' | 'horizontal'
  span?: number // lățimea în grupa-părinte, din 24
  border?: boolean
  children: LayoutNode[]
}
export interface LayoutField { type: 'field'; key: string; span?: number; hidden?: boolean } // hidden: ascuns de utilizator
export type LayoutNode = LayoutGroup | LayoutField

/** O bucată a formei: un câmp (Form.Item cu nume) sau un bloc (orice altceva: un rând de bife, un mesaj...). */
interface Unit { key: string; label: string; node: ReactNode; span?: number; section?: string; hidden?: boolean; required?: boolean }

type AnyProps = Record<string, unknown> & { children?: ReactNode }

const isFormItem = (el: ReactElement) => el.type === Form.Item
/** Câmpul obligatoriu (regula „required”) nu se poate ascunde: fără el forma nu s-ar mai salva. */
const isRequired = (props: AnyProps) => !!props.required
  || (Array.isArray(props.rules) && props.rules.some((r) => typeof r === 'object' && r !== null && (r as { required?: boolean }).required))
const isDivider = (el: ReactElement) => el.type === Divider
const nameOf = (props: AnyProps) => {
  const name = props.name as string | number | (string | number)[] | undefined
  if (name === undefined || name === null || name === '') return null
  return Array.isArray(name) ? name.join('.') : String(name)
}
const text = (node: unknown): string => {
  if (node === null || node === undefined || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(text).join('')
  if (isValidElement(node)) return text((node.props as AnyProps).children)
  return ''
}

/** Prima etichetă dintr-un bloc (de ex. „Aprobări” deasupra unei liste de rânduri), pentru numele lui în editor. */
function firstLabel(node: ReactNode): string {
  let out = ''
  Children.forEach(node, (child) => {
    if (out || !isValidElement(child)) return
    const props = child.props as AnyProps
    out = text(props.label) || (typeof props.children === 'function' ? '' : firstLabel(props.children))
  })
  return out
}

/** Câmpurile cu nume din interiorul unui element (oricât de adânc). */
function namedInside(node: ReactNode, out: { name: string; noStyle: boolean; label: string }[] = []) {
  Children.forEach(node, (child) => {
    if (!isValidElement(child)) return
    const props = child.props as AnyProps
    if (isFormItem(child) && nameOf(props)) {
      out.push({ name: nameOf(props)!, noStyle: !!props.noStyle, label: text(props.label) || text(props.children) })
      return
    }
    if (typeof props.children !== 'function') namedInside(props.children, out)
  })
  return out
}

/** Desface forma în bucăți, în ordinea lor: câmpurile cu nume ies din rânduri / coloane; titlurile secțiunilor
 *  (Divider) se țin minte ca grupe; restul rămân blocuri întregi. */
function extract(children: ReactNode): Unit[] {
  const units: Unit[] = []
  let section = ''
  let blocks = 0
  const walk = (node: ReactNode, span?: number) => {
    Children.forEach(node, (child) => {
      if (!isValidElement(child)) return
      const el = child as ReactElement<AnyProps>
      const props = el.props
      if (isDivider(el)) {
        section = text(props.children)
        return
      }
      if (isFormItem(el) && nameOf(props) && !props.noStyle) {
        const key = nameOf(props)!
        units.push({ key, label: text(props.label) || key, node: cloneElement(el, { key }), span, section, hidden: !!props.hidden,
          required: isRequired(props) })
        return
      }
      const inner = typeof props.children === 'function' ? [] : namedInside(props.children)
      const styledInside = inner.some((x) => !x.noStyle)
      if (el.type === Fragment || (styledInside && !isFormItem(el))) {
        // un rând / o coloană / un grup de aranjare: se intră înăuntru (lățimea coloanei trece la câmp)
        const colSpan = el.type === Col ? Number(props.md ?? props.span ?? props.lg ?? 24) : span
        walk(props.children, colSpan)
        return
      }
      // bloc întreg: câmpuri fără stil proprii (bife pe un rând), un Form.Item cu funcție, un mesaj, o componentă...
      const key = inner.length ? `block:${inner[0].name}` : `block:${blocks++}`
      const label = text(props.label) || inner.map((x) => x.label || x.name).join(', ') || firstLabel(props.children)
        || text(props.children).slice(0, 60) || `Bloc ${key.split(':')[1]}`
      // o coloană-bloc își dă lățimea grupei și intră fără învelișul ei (altfel ar fi o coloană în coloană)
      if (el.type === Col) {
        units.push({ key, label, node: <Fragment key={key}>{props.children}</Fragment>, section,
          span: Number(props.md ?? props.span ?? props.lg ?? 24) })
      } else units.push({ key, label, node: cloneElement(el, { key }), span, section })
    })
  }
  walk(children)
  return units
}

/** Așezarea implicită: câte o grupă pentru fiecare secțiune a formei, câmpurile cu lățimea coloanelor de acum. */
function defaultLayout(units: Unit[]): LayoutGroup {
  const root: LayoutGroup = { type: 'group', id: 'root', direction: 'vertical', children: [] }
  let current: LayoutGroup | null = null
  let n = 0
  for (const u of units.filter((x) => !x.hidden)) {
    if (!current || current.title !== (u.section || undefined)) {
      current = { type: 'group', id: `g${++n}`, title: u.section || undefined, direction: 'vertical', children: [] }
      root.children.push(current)
    }
    current.children.push({ type: 'field', key: u.key, span: u.span && u.span < 24 ? u.span : undefined })
  }
  return root
}

function fieldsOf(node: LayoutNode): string[] {
  return node.type === 'field' ? [node.key] : node.children.flatMap(fieldsOf)
}

/** Așezarea salvată completată: câmpurile apărute după salvare intră la sfârșit, în „Alte câmpuri”. */
function complete(layout: LayoutGroup, units: Unit[], otherTitle: string): LayoutGroup {
  const known = new Set(fieldsOf(layout))
  const missing = units.filter((u) => !known.has(u.key) && !u.hidden)
  if (!missing.length) return layout
  return { ...layout, children: [...layout.children, { type: 'group', id: 'other', title: otherTitle, direction: 'vertical',
    children: missing.map((u) => ({ type: 'field', key: u.key, span: u.span && u.span < 24 ? u.span : undefined }) as LayoutField) }] }
}

/** Câmpul se vede: există în forma de acum și nu e ascuns de utilizator (cele obligatorii se văd mereu). */
const shown = (f: LayoutField, units: Map<string, Unit>) => units.has(f.key) && (!f.hidden || !!units.get(f.key)?.required)
const visibleIn = (n: LayoutNode, units: Map<string, Unit>): boolean =>
  n.type === 'field' ? shown(n, units) : n.children.some((c) => visibleIn(c, units))

function hiddenFields(node: LayoutNode, units: Map<string, Unit>): LayoutField[] {
  if (node.type === 'field') return units.has(node.key) && !shown(node, units) ? [node] : []
  return node.children.flatMap((c) => hiddenFields(c, units))
}

function Render({ node, units, phone, parent }: { node: LayoutNode; units: Map<string, Unit>; phone: boolean; parent: 'vertical' | 'horizontal' }) {
  if (node.type === 'field') return <>{units.get(node.key)?.node ?? null}</>
  const kids = node.children.filter((c) => visibleIn(c, units))
  const auto = node.direction === 'horizontal' ? Math.max(4, Math.floor(24 / Math.max(kids.length, 1))) : 24
  // câmpurile ascunse rămân în formă (invizibile), ca valorile lor să se păstreze la salvare
  const hidden = node.id === 'root' ? hiddenFields(node, units) : []
  const body = (
    <Row gutter={16}>
      {kids.map((c) => (
        <Col key={c.type === 'field' ? c.key : c.id} xs={24} md={phone ? 24 : (c.span ?? auto)}>
          <Render node={c} units={units} phone={phone} parent={node.direction} />
        </Col>
      ))}
      {hidden.length > 0 && <div style={{ display: 'none' }}>{hidden.map((f) => units.get(f.key)?.node)}</div>}
    </Row>
  )
  if (!kids.length && node.id !== 'root') return null
  if (node.id === 'root') return body
  if (node.border) return <Card size="small" title={node.title} style={{ marginBottom: 16 }}>{body}</Card>
  return (
    <div style={{ marginBottom: parent === 'vertical' ? 4 : 0 }}>
      {node.title && <Divider titlePlacement="start" style={{ marginTop: 4 }}>{node.title}</Divider>}
      {body}
    </div>
  )
}

export default function FormLayout({ formKey, children }: { formKey: string; children: ReactNode }) {
  const { t } = useTranslation()
  const { hasPerm } = useApp()
  const phone = !Grid.useBreakpoint().md
  const key = prefKey('layout', formKey)
  const [mine, saveMine, resetMine] = useUiPref<LayoutGroup>(key)
  const [forAll, saveAll, resetAll] = useUiDefault<LayoutGroup>(key)
  const saved = mine ?? forAll
  const [draft, setDraftState] = useState<LayoutGroup | null>(null)
  const units = useMemo(() => extract(children), [children])
  const byKey = useMemo(() => new Map(units.map((u) => [u.key, u])), [units])
  const layout = draft ?? saved
  // la reașezare câmpurile se montează din nou; formele cu preserve={false} și-ar pierde valorile scrise — le ținem
  // minte înainte și le punem la loc după
  const form = Form.useFormInstance()
  const kept = useRef<Record<string, unknown> | null>(null)
  const keep = () => {
    try {
      kept.current ??= form.getFieldsValue(true)
    } catch {
      kept.current = null
    }
  }
  useEffect(() => {
    if (kept.current) {
      form.setFieldsValue(kept.current)
      kept.current = null
    }
  })
  const setDraft = (next: LayoutGroup | null) => {
    keep()
    setDraftState(next)
  }
  const canAll = hasPerm('settings.edit')

  return (
    <>
      {!phone && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: -4, marginBottom: 4 }}>
          <Tooltip title={t('formLayout.hint')}>
            <Button size="small" type="text" icon={<LayoutOutlined />}
              onClick={() => setDraft(structuredClone(complete(saved ?? defaultLayout(units), units, t('formLayout.other'))))}>
              {t('formLayout.button')}
            </Button>
          </Tooltip>
        </div>
      )}
      {layout ? (
        <>
          <Render node={complete(layout, units, t('formLayout.other'))} units={byKey} phone={phone} parent="vertical" />
          {units.filter((u) => u.hidden).map((u) => u.node)}
        </>
      ) : children}
      {draft && (
        <Designer layout={draft} units={byKey} onChange={setDraft} onClose={() => setDraft(null)} canAll={canAll} hasAll={!!forAll}
          onSave={async (scope) => {
            try {
              keep()
              if (scope === 'all') {
                await saveAll(draft)
                resetMine()  // administratorul vede ce văd toți
                message.success(t('formLayout.savedAll'))
              } else saveMine(draft)
              setDraft(null)
            } catch {
              message.error(t('formLayout.error'))
            }
          }}
          onReset={async (scope) => {
            try {
              keep()
              if (scope === 'all') await resetAll()
              resetMine()
              setDraft(null)
            } catch {
              message.error(t('formLayout.error'))
            }
          }} />
      )}
    </>
  )
}

// --- Editorul formei --------------------------------------------------------------------------------------------

function findNode(root: LayoutGroup, id: string): { node: LayoutNode; parent: LayoutGroup | null } | null {
  const idOf = (n: LayoutNode) => (n.type === 'field' ? `f:${n.key}` : n.id)
  if (idOf(root) === id) return { node: root, parent: null }
  const stack: LayoutGroup[] = [root]
  while (stack.length) {
    const g = stack.pop()!
    for (const c of g.children) {
      if (idOf(c) === id) return { node: c, parent: g }
      if (c.type === 'group') stack.push(c)
    }
  }
  return null
}

function Designer({ layout, units, onChange, onClose, onSave, onReset, canAll, hasAll }: {
  layout: LayoutGroup
  units: Map<string, Unit>
  onChange: (l: LayoutGroup) => void
  onClose: () => void
  onSave: (scope: 'mine' | 'all') => void
  onReset: (scope: 'mine' | 'all') => void
  canAll: boolean
  hasAll: boolean
}) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<string>('root')
  const update = (fn: (root: LayoutGroup) => void) => {
    const copy = structuredClone(layout)
    fn(copy)
    onChange(copy)
  }

  const toggleField = (key: string, visible: boolean) => update((root) => {
    const found = findNode(root, `f:${key}`)
    if (found && found.node.type === 'field') found.node.hidden = visible ? undefined : true
  })
  const toTree = (n: LayoutNode): TreeDataNode => n.type === 'field'
    ? { key: `f:${n.key}`, isLeaf: true, icon: <AppstoreOutlined />,
        title: (
          <span style={{ opacity: n.hidden && !units.get(n.key)?.required ? 0.55 : 1 }}>
            <Tooltip title={units.get(n.key)?.required ? t('formLayout.requiredHint') : t('formLayout.visibleHint')}>
              <Checkbox checked={!n.hidden || !!units.get(n.key)?.required} disabled={!!units.get(n.key)?.required} style={{ marginInlineEnd: 6 }}
                onClick={(e) => e.stopPropagation()} onChange={(e) => toggleField(n.key, e.target.checked)} />
            </Tooltip>
            {units.get(n.key)?.label ?? n.key}
            {units.get(n.key)?.required && <Typography.Text type="danger"> *</Typography.Text>}
            {n.span ? <Typography.Text type="secondary"> · {n.span}/24</Typography.Text> : null}
            {n.hidden && !units.get(n.key)?.required && <Tag icon={<EyeInvisibleOutlined />} style={{ marginInlineStart: 6 }}>{t('formLayout.hiddenTag')}</Tag>}
          </span>
        ) }
    : { key: n.id, icon: <FolderOutlined />,
        title: <span><b>{n.id === 'root' ? t('formLayout.form') : (n.title || t('formLayout.untitled'))}</b>
          <Typography.Text type="secondary"> · {t(`formLayout.${n.direction}`)}{n.span ? ` · ${n.span}/24` : ''}</Typography.Text></span>,
        children: n.children.map(toTree) }

  const onDrop: TreeProps['onDrop'] = (info) => {
    const dragKey = String(info.dragNode.key)
    const dropKey = String(info.node.key)
    // -1 = înaintea nodului, 1 = după el (ca în documentația antd: din calea nodului)
    const pos = String(info.node.pos).split('-')
    const relative = info.dropPosition - Number(pos[pos.length - 1])
    if (dragKey === 'root') return
    update((root) => {
      const from = findNode(root, dragKey)
      if (!from?.parent) return
      if (from.node.type === 'group' && findNode(from.node, dropKey)) return // o grupă nu intră în ea însăși
      from.parent.children = from.parent.children.filter((c) => c !== from.node)
      const target = findNode(root, dropKey)
      if (!target) return
      const into = !info.dropToGap && target.node.type === 'group'
      if (into) {
        (target.node as LayoutGroup).children.unshift(from.node)
      } else if (target.parent) {
        const list = target.parent.children
        const idx = list.indexOf(target.node)
        list.splice(relative === -1 ? idx : idx + 1, 0, from.node)
      }
    })
  }

  const sel = findNode(layout, selected)
  const addGroup = () => update((root) => {
    const target = sel && sel.node.type === 'group' ? findNode(root, selected)!.node as LayoutGroup : root
    target.children.push({ type: 'group', id: `g${Date.now()}`, title: t('formLayout.newGroup'), direction: 'horizontal', children: [] })
  })
  const removeGroup = () => update((root) => {
    const found = findNode(root, selected)
    if (!found?.parent || found.node.type !== 'group') return
    const idx = found.parent.children.indexOf(found.node)
    found.parent.children.splice(idx, 1, ...found.node.children) // conținutul urcă în grupa-părinte
    setSelected('root')
  })
  const setProp = (patch: Partial<LayoutGroup> & Partial<LayoutField>) => update((root) => {
    const found = findNode(root, selected)
    if (found) Object.assign(found.node, patch)
  })
  /** Mută elementul ales cu un loc mai sus / mai jos în grupa lui (fără mouse). */
  const shift = (step: number) => update((root) => {
    const found = findNode(root, selected)
    if (!found?.parent) return
    const list = found.parent.children
    const i = list.indexOf(found.node)
    const j = i + step
    if (j < 0 || j >= list.length) return
    ;[list[i], list[j]] = [list[j], list[i]]
  })
  /** Mută elementul ales la sfârșitul altei grupe. */
  const moveTo = (groupId: string) => update((root) => {
    const found = findNode(root, selected)
    const target = findNode(root, groupId)
    if (!found?.parent || !target || target.node.type !== 'group') return
    if (found.node.type === 'group' && findNode(found.node, groupId)) return // nu într-o grupă din ea însăși
    found.parent.children = found.parent.children.filter((c) => c !== found.node)
    target.node.children.push(found.node)
  })
  const groupOptions: { value: string; label: string }[] = []
  const collect = (g: LayoutGroup, depth: number) => {
    groupOptions.push({ value: g.id, label: `${'— '.repeat(depth)}${g.id === 'root' ? t('formLayout.form') : (g.title || t('formLayout.untitled'))}` })
    g.children.forEach((c) => c.type === 'group' && collect(c, depth + 1))
  }
  collect(layout, 0)
  const hiddenCount = (function count(n: LayoutNode): number {
    return n.type === 'field' ? (n.hidden && units.has(n.key) && !units.get(n.key)?.required ? 1 : 0) : n.children.reduce((a, c) => a + count(c), 0)
  })(layout)

  return (
    <Drawer open size={560} title={t('formLayout.title')} onClose={onClose} mask={false}
      footer={(
        <Space wrap>
          <Button type="primary" onClick={() => onSave('mine')}>{t('formLayout.save')}</Button>
          {canAll && <Button onClick={() => onSave('all')}>{t('formLayout.saveAll')}</Button>}
          <Button onClick={() => onReset('mine')}>{t('formLayout.reset')}</Button>
          {canAll && hasAll && (
            <Popconfirm title={t('formLayout.resetAllConfirm')} onConfirm={() => onReset('all')}>
              <Button danger>{t('formLayout.resetAll')}</Button>
            </Popconfirm>
          )}
        </Space>
      )}>
      <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>{t('formLayout.help')}</Typography.Paragraph>
      <Space wrap style={{ marginBottom: 8 }}>
        <Button size="small" icon={<FolderAddOutlined />} onClick={addGroup}>{t('formLayout.addGroup')}</Button>
        <Button size="small" danger icon={<DeleteOutlined />} disabled={!sel || sel.node.type !== 'group' || selected === 'root'}
          onClick={removeGroup}>{t('formLayout.removeGroup')}</Button>
        <Tooltip title={t('formLayout.up')}><Button size="small" icon={<ArrowUpOutlined />} disabled={selected === 'root'} onClick={() => shift(-1)} /></Tooltip>
        <Tooltip title={t('formLayout.down')}><Button size="small" icon={<ArrowDownOutlined />} disabled={selected === 'root'} onClick={() => shift(1)} /></Tooltip>
        <Select size="small" style={{ minWidth: 190 }} placeholder={t('formLayout.moveTo')} value={null} disabled={selected === 'root'}
          options={groupOptions.filter((o) => o.value !== selected)} onChange={(v) => v && moveTo(v)} />
        {hiddenCount > 0 && <Tag icon={<EyeInvisibleOutlined />}>{t('formLayout.hiddenCount', { n: hiddenCount })}</Tag>}
      </Space>
      <Tree showIcon blockNode draggable={{ icon: false }} defaultExpandAll treeData={[toTree(layout)]} selectedKeys={[selected]}
        onSelect={(keys) => keys[0] && setSelected(String(keys[0]))} onDrop={onDrop}
        allowDrop={({ dropNode, dropPosition }) => dropPosition !== 0 || !String(dropNode.key).startsWith('f:')}
        style={{ maxHeight: '45vh', overflow: 'auto', marginBottom: 12, border: '1px solid var(--ant-color-border-secondary)', borderRadius: 6, padding: 4 }} />
      {!sel ? <Empty /> : sel.node.type === 'group' ? (
        <Card size="small" title={t('formLayout.groupProps')}>
          <Space orientation="vertical" style={{ width: '100%' }}>
            {selected !== 'root' && (
              <Input addonBefore={t('formLayout.groupTitle')} value={sel.node.title ?? ''} onChange={(e) => setProp({ title: e.target.value || undefined })} />
            )}
            <Radio.Group value={sel.node.direction} onChange={(e) => setProp({ direction: e.target.value })} optionType="button"
              options={[{ value: 'vertical', label: t('formLayout.vertical') }, { value: 'horizontal', label: t('formLayout.horizontal') }]} />
            {selected !== 'root' && <SpanInput value={sel.node.span} onChange={(v) => setProp({ span: v })} />}
            {selected !== 'root' && (
              <Checkbox checked={!!sel.node.border} onChange={(e) => setProp({ border: e.target.checked || undefined })}>{t('formLayout.border')}</Checkbox>
            )}
          </Space>
        </Card>
      ) : (
        <Card size="small" title={units.get(sel.node.key)?.label ?? sel.node.key}>
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Checkbox checked={!sel.node.hidden || !!units.get(sel.node.key)?.required} disabled={!!units.get(sel.node.key)?.required}
              onChange={(e) => setProp({ hidden: e.target.checked ? undefined : true })}>
              {units.get(sel.node.key)?.required ? t('formLayout.requiredHint') : t('formLayout.visible')}
            </Checkbox>
            <SpanInput value={sel.node.span} onChange={(v) => setProp({ span: v })} />
          </Space>
        </Card>
      )}
    </Drawer>
  )
}

function SpanInput({ value, onChange }: { value?: number; onChange: (v: number | undefined) => void }) {
  const { t } = useTranslation()
  return (
    <Space wrap>
      <ColumnWidthOutlined />
      <span>{t('formLayout.width')}</span>
      <InputNumber min={1} max={24} value={value ?? null} placeholder={t('formLayout.auto')} onChange={(v) => onChange(v ? Number(v) : undefined)} />
      <span>/ 24</span>
      {[24, 12, 8, 6].map((s) => <Button key={s} size="small" onClick={() => onChange(s)}>{s === 24 ? '1' : `1/${24 / s}`}</Button>)}
      <Tooltip title={t('formLayout.auto')}><Button size="small" type="text" icon={<ClearOutlined />} onClick={() => onChange(undefined)} /></Tooltip>
    </Space>
  )
}

/** Pentru verificări (randarea fără interfață). */
export const __formLayoutInternals = { extract, defaultLayout, complete, Render }

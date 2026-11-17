import { useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Button, Empty, Input, Modal, Space, Tooltip, Tree, TreeSelect, Typography } from 'antd'
import { EllipsisOutlined } from '@ant-design/icons'

import type { Subdivision } from '../api/org'
import { useFetch } from '../api/hooks'
import { useLocalName } from '../auth/AppContext'

interface Node { value: number; key: number; title: ReactNode; label: string; disabled?: boolean; selectable?: boolean; children?: Node[] }

/** Arborele subdiviziunilor din lista plată (câmpul `parent`): cele inactive rămân doar dacă sunt alese sau au sub ele
 *  subdiviziuni active (atunci nu se pot alege). */
export function useSubdivisionTree(keep: number[] = [], exclude: number[] = []) {
  const localName = useLocalName()
  const { data, loading } = useFetch<Subdivision[]>('/org/subdivisions/')
  const tree = useMemo(() => {
    const rows = data ?? []
    const ids = new Set(rows.map((r) => r.id))
    const byParent = new Map<number | null, Subdivision[]>()
    for (const r of rows) {
      const parent = r.parent !== null && ids.has(r.parent) ? r.parent : null
      byParent.set(parent, [...(byParent.get(parent) ?? []), r])
    }
    const build = (parent: number | null, depth = 0): Node[] => (depth > 20 ? [] : (byParent.get(parent) ?? []).flatMap((r) => {
      const children = build(r.id, depth + 1)
      const usable = (r.is_active !== false && !r.deletion_mark) || keep.includes(r.id)
      if (!usable && !children.length) return []
      const label = localName(r)
      const off = !usable || exclude.includes(r.id)
      return [{
        value: r.id, key: r.id, label, disabled: off && !keep.includes(r.id), selectable: !off,
        title: r.code ? <span>{label} <Typography.Text type="secondary">{r.code}</Typography.Text></span> : label,
        children: children.length ? children : undefined,
      }]
    }))
    return build(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, localName, keep.join(','), exclude.join(',')])
  return { tree, loading }
}

/** Nodurile care se potrivesc căutării, cu părinții lor (ca arborele să rămână întreg). */
function filterTree(nodes: Node[], q: string): Node[] {
  if (!q) return nodes
  return nodes.flatMap((n) => {
    const children = n.children ? filterTree(n.children, q) : []
    if (n.label.toLowerCase().includes(q) || children.length) return [{ ...n, children: children.length ? children : n.children }]
    return []
  })
}

/**
 * Alegerea subdiviziunii, ca în 1C: lista derulantă ca arbore (cu căutare după denumire) + butonul „…”, care deschide
 * structura instituției pe toată fereastra; clic pe subdiviziune o pune în câmp. `exclude` — subdiviziunile care nu se pot
 * alege aici (de ex. cele care au deja un document în luna aleasă).
 */
export default function SubdivisionSelect({ value, onChange, mode, allowClear = true, disabled, placeholder, style, exclude }: {
  value?: number | number[] | null
  onChange?: (value: number | number[] | null) => void
  mode?: 'multiple'
  allowClear?: boolean
  disabled?: boolean
  placeholder?: string
  style?: CSSProperties
  exclude?: number[]
}) {
  const { t } = useTranslation()
  const chosen = Array.isArray(value) ? value : value ? [value] : []
  const { tree } = useSubdivisionTree(chosen, exclude)
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const shown = useMemo(() => filterTree(tree, q.trim().toLowerCase()), [tree, q])
  const pick = (id: number) => {
    if (mode === 'multiple') onChange?.(chosen.includes(id) ? chosen : [...chosen, id])
    else onChange?.(id)
    setOpen(false)
  }
  return (
    <>
      <Space.Compact style={{ width: '100%', ...style }}>
        <TreeSelect<number | number[]> showSearch treeNodeFilterProp="label" treeDefaultExpandAll allowClear={allowClear} disabled={disabled}
          multiple={mode === 'multiple'} placeholder={placeholder} value={value ?? undefined} treeData={tree} style={{ width: '100%' }}
          popupMatchSelectWidth={false} onChange={(v) => onChange?.(v ?? null)} />
        <Tooltip title={t('subPicker.open')}>
          <Button icon={<EllipsisOutlined />} disabled={disabled} onClick={() => { setQ(''); setOpen(true) }} aria-label={t('subPicker.open')} />
        </Tooltip>
      </Space.Compact>
      <Modal open={open} onCancel={() => setOpen(false)} footer={null} width="min(720px, 96vw)" destroyOnHidden title={t('subPicker.title')}>
        <Input.Search autoFocus allowClear placeholder={t('picker.search')} style={{ marginBottom: 12 }}
          onChange={(e) => setQ(e.target.value)} onSearch={setQ} />
        <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
          {shown.length ? (
            <Tree<Node> blockNode defaultExpandAll key={q} treeData={shown} selectedKeys={chosen}
              onSelect={(_keys, info) => { if (info.node.selectable !== false) pick(Number(info.node.key)) }} />
          ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
        </div>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('subPicker.hint')}</Typography.Text>
      </Modal>
    </>
  )
}

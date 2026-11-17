import { Children, Fragment, isValidElement, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { Button, Checkbox, InputNumber, Modal, Space, Spin, Table as AntTable, Tooltip, Tree, Typography, message } from 'antd'
import type { TableColumnType, TableProps } from 'antd'
import { ArrowDownOutlined, ArrowUpOutlined, CloseOutlined, FileExcelOutlined, HolderOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { api, errorText } from '../api/client'
import { listSource } from '../api/listSources'
import { prefKey, useUiPref } from '../api/uiPrefs'
import type { RowTone } from './rowTone'

/**
 * Tabelul programului: tabelul Ant Design plus, în colțul din dreapta al antetului, două butoane —
 * „Coloanele listei” (ce coloane se văd, în ce ordine, ce lățime; aranjarea e a fiecărui utilizator) și
 * „Salvează în Excel” (coloanele vizibile, textul cum se vede; la listele cu pagini — toate paginile, cu filtrele).
 * Se folosește exact ca tabelul Ant Design; `noSettings` îl lasă fără butoane, `rowTone` colorează textul rândului după stare
 * (components/rowTone.ts).
 */

type Col = TableColumnType<object> & { children?: unknown }
/** Câmpul adăugat din obiect (sau din obiectele legate): „Clientul → Segmentul”. */
interface ExtraField { path: string; title: string; type?: string }
interface TablePref { order?: string[]; hidden?: string[]; widths?: Record<string, number>; extra?: ExtraField[] }
type Values = Record<string, Record<string, unknown>>
const EXTRA = 'x:'

function showValue(v: unknown, type?: string): string {
  if (v === null || v === undefined || v === '') return ''
  if (type === 'date') return dayjs(String(v)).format('DD.MM.YYYY')
  if (type === 'datetime') return dayjs(String(v)).format('DD.MM.YYYY HH:mm')
  if (type === 'number') return Number(v).toLocaleString('ro-RO', { maximumFractionDigits: 4 })
  return String(v)
}

/** Valorile câmpurilor adăugate pentru rândurile date (în pachete, pentru export). */
async function loadValues(url: string, ids: (string | number)[], fields: string[]): Promise<Values> {
  const out: Values = {}
  for (let i = 0; i < ids.length; i += 1000) {
    const { data } = await api.post<Values>('/list-fields/values/', { url, ids: ids.slice(i, i + 1000), fields })
    Object.assign(out, data)
  }
  return out
}

const TOOLS = '__tools'
const MAX_EXPORT = 20000

function colId(c: Col, i: number): string {
  if (c.key !== undefined && c.key !== null) return String(c.key)
  if (Array.isArray(c.dataIndex)) return c.dataIndex.join('.')
  if (c.dataIndex !== undefined && c.dataIndex !== null) return String(c.dataIndex)
  return typeof c.title === 'string' ? c.title : `#${i}`
}

/** Textul unui titlu (poate fi element React): pentru lista din setări. */
function text(node: unknown): string {
  if (node === null || node === undefined || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(text).join('')
  if (isValidElement(node)) return text((node.props as { children?: ReactNode }).children)
  return ''
}

function hash(value: string): string {
  let h = 0
  for (let i = 0; i < value.length; i++) h = (h * 31 + value.charCodeAt(i)) | 0
  return (h >>> 0).toString(36)
}

/** Ordinea coloanelor după aranjare; coloanele noi (apărute după salvare) rămân lângă vecinul lor de la început. */
function orderIds(ids: string[], pref: TablePref | undefined): string[] {
  const order = (pref?.order ?? []).filter((id) => ids.includes(id))
  ids.forEach((id, i) => {
    if (order.includes(id)) return
    const before = ids.slice(0, i).reverse().find((x) => order.includes(x))
    order.splice(before ? order.indexOf(before) + 1 : 0, 0, id)
  })
  return order
}

function arrange(columns: Col[], pref: TablePref | undefined): Col[] {
  if (!pref) return columns
  const ids = columns.map(colId)
  const byId = new Map(columns.map((c, i) => [ids[i], c]))
  const order = orderIds(ids, pref)
  const hidden = new Set(pref.hidden ?? [])
  return order.filter((id) => !hidden.has(id)).map((id) => {
    const c = byId.get(id)!
    const width = pref.widths?.[id]
    return width ? { ...c, width } : c
  })
}


/** Coloanele „număr” din listele în care rândul se deschide cu clic: textul numărului devine buton plin. */
const OPEN_COLUMNS = new Set(['number'])

function asButton(node: ReactNode): ReactNode {
  if (node === null || node === undefined || node === '' || typeof node === 'boolean') return node
  if (typeof node === 'string' || typeof node === 'number') return <span className="doc-btn">{node}</span>
  if (isValidElement(node) && node.type === Fragment) {
    const parts = Children.toArray((node.props as { children?: ReactNode }).children)
    if (parts.length && (typeof parts[0] === 'string' || typeof parts[0] === 'number')) {
      return <>{<span className="doc-btn">{parts[0]}</span>}{parts.slice(1)}</>
    }
  }
  return node
}

function withOpenButtons<T extends object>(columns: Col[], onRow: TableProps<T>['onRow']): Col[] {
  if (!onRow) return columns
  return columns.map((c, i) => {
    if (!OPEN_COLUMNS.has(colId(c, i)) || c.children) return c
    const render = c.render
    return { ...c, render: (value: unknown, record: object, index: number) => asButton(render ? (render(value, record, index) as ReactNode) : (value as ReactNode)) }
  })
}

function AppTable<T extends object>(props: TableProps<T> & {
  noSettings?: boolean; exportName?: string; fieldsUrl?: string; rowTone?: (record: T) => RowTone | undefined
}) {
  const { noSettings, exportName, fieldsUrl: fieldsUrlProp, rowTone, ...tableProps } = props
  const { t } = useTranslation()
  const location = useLocation()
  const baseColumns = useMemo(() => withOpenButtons<T>((tableProps.columns ?? []) as Col[], tableProps.onRow), [tableProps.columns, tableProps.onRow])
  const enabled = !noSettings && baseColumns.length >= 3
  const baseIds = baseColumns.map(colId)
  const key = enabled ? prefKey('table', location.pathname.replace(/\/\d+(?=\/|$)/g, '/id'), hash(baseIds.join('|'))) : null
  const [pref, save, reset] = useUiPref<TablePref>(key)
  const [open, setOpen] = useState(false)
  // coloanele din câmpurile obiectului: lista se recunoaște după adresa de unde vin rândurile (sau fieldsUrl)
  const fieldsUrl = fieldsUrlProp ?? listSource(tableProps.dataSource)?.url
  const extra = useMemo(() => (enabled && fieldsUrl ? pref?.extra ?? [] : []), [enabled, fieldsUrl, pref?.extra])
  const [values, setValues] = useState<Values>({})
  const rowId = (r: T) => (r as { id?: string | number }).id
  useEffect(() => {
    const rows = (tableProps.dataSource ?? []) as T[]
    const wanted = rows.map(rowId).filter((x): x is string | number => x !== undefined && x !== null)
    if (!extra.length || !fieldsUrl || !wanted.length) return
    loadValues(fieldsUrl, wanted, extra.map((x) => x.path)).then((v) => setValues((cur) => ({ ...cur, ...v }))).catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableProps.dataSource, fieldsUrl, extra])
  const columns = useMemo(() => [...baseColumns, ...extra.map((x): Col => ({
    key: `${EXTRA}${x.path}`, title: x.title, ellipsis: true,
    render: (_: unknown, r: object) => showValue(values[String((r as { id?: unknown }).id)]?.[x.path], x.type),
  }))], [baseColumns, extra, values])
  const ids = columns.map(colId)
  const [exportRows, setExportRows] = useState<T[] | null>(null)
  const [exporting, setExporting] = useState(false)
  const hiddenRef = useRef<HTMLDivElement>(null)

  // coloanele marcate `defaultHidden` (date sensibile, detalii) sunt ascunse până când utilizatorul își aranjează tabelul
  const defaultHidden = useMemo(() => columns.filter((c) => (c as { defaultHidden?: boolean }).defaultHidden).map(colId), [columns])
  const effPref = useMemo(() => pref ?? (defaultHidden.length ? { hidden: defaultHidden } : undefined), [pref, defaultHidden])
  const visible = useMemo(() => arrange(columns, effPref), [columns, effPref])

  const startExport = async () => {
    const rows = (tableProps.dataSource ?? []) as T[]
    const source = listSource(tableProps.dataSource)
    setExporting(true)
    try {
      let all = [...rows]
      if (source && source.count > rows.length) {  // lista cu pagini: toate paginile, cu aceleași filtre
        if (source.count > MAX_EXPORT) message.warning(t('listTools.tooMany', { count: source.count, max: MAX_EXPORT }))
        all = []
        for (let page = 1; all.length < Math.min(source.count, MAX_EXPORT); page++) {
          const { data } = await api.get<{ results: T[] }>(source.url, { params: { ...source.params, page, page_size: 500 } })
          if (!data.results?.length) break
          all.push(...data.results)
        }
      }
      if (!all.length) {
        message.info(t('listTools.empty'))
        setExporting(false)
        return
      }
      if (extra.length && fieldsUrl) {  // câmpurile adăugate: valorile și pentru celelalte pagini
        const more = await loadValues(fieldsUrl, all.slice(0, MAX_EXPORT).map(rowId).filter((x): x is string | number => x !== undefined && x !== null),
          extra.map((x) => x.path))
        setValues((cur) => ({ ...cur, ...more }))
      }
      setExportRows(all.slice(0, MAX_EXPORT))  // se desenează ascuns, apoi se citește textul celulelor (efectul de mai jos)
    } catch (e) {
      message.error(errorText(e))
      setExporting(false)
    }
  }

  useEffect(() => {
    if (!exportRows || !hiddenRef.current) return
    const root = hiddenRef.current
    const head = root.querySelectorAll('thead tr:last-child th')
    const titles = Array.from(head).map((th) => (th as HTMLElement).innerText.trim())
    const rows = Array.from(root.querySelectorAll('tbody tr.ant-table-row')).map((tr) =>
      Array.from(tr.querySelectorAll(':scope > td')).map((td) => (td as HTMLElement).innerText.trim()))
    const widths = visible.map((c) => (typeof c.width === 'number' ? c.width : null))
    // fără coloanele de butoane (fără titlu și goale peste tot)
    const keep = titles.map((x, i) => !!x || rows.some((r) => !!r[i]))
    const title = exportName || document.querySelector('h1, h2, h3, h4')?.textContent?.trim() || t('listTools.excel')
    api.post('/export/xlsx/', {
      title, columns: titles.map((x, i) => ({ title: x, width: widths[i] })).filter((_, i) => keep[i]),
      rows: rows.map((r) => r.filter((_, i) => keep[i])),
    }, { responseType: 'blob' })
      .then((r) => {
        const url = URL.createObjectURL(r.data as Blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${title.replace(/[\\/:*?"<>|]+/g, '-')}.xlsx`
        a.click()
        setTimeout(() => URL.revokeObjectURL(url), 5000)
      })
      .catch((e) => message.error(errorText(e)))
      .finally(() => {
        setExportRows(null)
        setExporting(false)
      })
  }, [exportRows, visible, exportName, t])

  const tools: Col = {
    key: TOOLS, width: 72, align: 'right', fixed: tableProps.scroll?.x ? 'right' : undefined,
    title: (
      <Space size={0}>
        <Tooltip title={t('listTools.settings')}>
          <Button type="text" size="small" icon={<SettingOutlined />} onClick={() => setOpen(true)} />
        </Tooltip>
        <Tooltip title={t('listTools.excel')}>
          <Button type="text" size="small" icon={<FileExcelOutlined />} loading={exporting} onClick={startExport} />
        </Tooltip>
      </Space>
    ),
    render: () => null,
  }

  // obiectul marcat pentru ștergere se arată tăiat și gri (clasa row-marked din styles.css), fără culoarea stării; altfel starea
  // documentului — culoarea textului (row-work albastru, row-done verde)
  const rowClassName = (record: T, index: number, indent: number) => {
    const own = typeof tableProps.rowClassName === 'function' ? tableProps.rowClassName(record, index, indent) : tableProps.rowClassName ?? ''
    const tone = rowTone?.(record)
    const state = (record as { deletion_mark?: boolean }).deletion_mark ? 'row-marked' : tone && `row-${tone}`
    return [own, state].filter(Boolean).join(' ')
  }

  if (!enabled) return <AntTable<T> {...tableProps} rowClassName={rowClassName} columns={baseColumns as TableProps<T>['columns']} />
  return (
    <>
      <AntTable<T> {...tableProps} rowClassName={rowClassName} columns={[...visible, tools] as TableProps<T>['columns']} />
      {open && (
        <ColumnsDialog columns={columns} ids={ids} pref={effPref} onChange={save} onReset={reset} onClose={() => setOpen(false)}
          fieldsUrl={fieldsUrl} />
      )}
      {exportRows && (
        <div ref={hiddenRef} aria-hidden style={{ position: 'fixed', left: -100000, top: 0, width: 2000, visibility: 'hidden' }}>
          <AntTable<T> rowKey={tableProps.rowKey} dataSource={exportRows} columns={visible as TableProps<T>['columns']}
            pagination={false} size="small" />
        </div>
      )}
    </>
  )
}

function ColumnsDialog({ columns, ids, pref, onChange, onReset, onClose, fieldsUrl }: {
  columns: Col[]
  ids: string[]
  pref: TablePref | undefined
  onChange: (p: TablePref) => void
  onReset: () => void
  onClose: () => void
  fieldsUrl?: string
}) {
  const { t } = useTranslation()
  const [picking, setPicking] = useState(false)
  const extra = pref?.extra ?? []
  const titles = new Map(columns.map((c, i) => [ids[i], text(typeof c.title === 'function' ? '' : c.title) || ids[i]]))
  const order = orderIds(ids, pref)
  const hidden = new Set(pref?.hidden ?? [])
  const widths = pref?.widths ?? {}
  const [drag, setDrag] = useState<string | null>(null)

  const update = (patch: Partial<TablePref>) => onChange({ order, hidden: [...hidden], widths, extra, ...patch })
  const addField = (f: ExtraField) => {
    if (!extra.some((x) => x.path === f.path)) update({ extra: [...extra, f], order: [...order, `${EXTRA}${f.path}`] })
    setPicking(false)
  }
  const removeField = (id: string) => update({ extra: extra.filter((x) => `${EXTRA}${x.path}` !== id), order: order.filter((x) => x !== id) })
  const move = (id: string, to: number) => {
    const next = order.filter((x) => x !== id)
    next.splice(Math.max(0, Math.min(to, next.length)), 0, id)
    update({ order: next })
  }

  return (
    <Modal open onCancel={onClose} title={t('listTools.settings')} width={560}
      footer={[
        <Button key="reset" onClick={() => onReset()}>{t('listTools.reset')}</Button>,
        <Button key="done" type="primary" onClick={onClose}>{t('listTools.done')}</Button>,
      ]}>
      <Typography.Paragraph type="secondary">{t('listTools.hint')}</Typography.Paragraph>
      <div>
        {order.map((id, i) => (
          <div key={id} draggable onDragStart={() => setDrag(id)} onDragOver={(e) => e.preventDefault()}
            onDrop={() => { if (drag && drag !== id) move(drag, order.indexOf(id)); setDrag(null) }}
            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px', borderRadius: 6,
              background: drag === id ? 'rgba(127,127,127,0.15)' : undefined, cursor: 'grab' }}>
            <Tooltip title={t('listTools.drag')}><HolderOutlined style={{ opacity: 0.5 }} /></Tooltip>
            <Checkbox checked={!hidden.has(id)}
              onChange={(e) => {
                const next = new Set(hidden)
                if (e.target.checked) next.delete(id)
                else next.add(id)
                if (next.size < order.length) update({ hidden: [...next] })  // măcar o coloană rămâne
              }} />
            <span style={{ flex: 1 }}>{titles.get(id)}</span>
            <InputNumber size="small" min={40} max={800} placeholder={t('listTools.auto')} value={widths[id] ?? null}
              style={{ width: 90 }} onChange={(v) => {
                const next = { ...widths }
                if (v) next[id] = Number(v)
                else delete next[id]
                update({ widths: next })
              }} />
            <Button size="small" type="text" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => move(id, i - 1)} />
            <Button size="small" type="text" icon={<ArrowDownOutlined />} disabled={i === order.length - 1} onClick={() => move(id, i + 1)} />
            {id.startsWith(EXTRA) ? (
              <Tooltip title={t('listTools.removeField')}><Button size="small" type="text" danger icon={<CloseOutlined />} onClick={() => removeField(id)} /></Tooltip>
            ) : <span style={{ width: 24 }} />}
          </div>
        ))}
      </div>
      {fieldsUrl && (
        <Button icon={<PlusOutlined />} style={{ marginTop: 8 }} onClick={() => setPicking(true)}>{t('listTools.addField')}</Button>
      )}
      {picking && fieldsUrl && <FieldPicker url={fieldsUrl} taken={extra.map((x) => x.path)} onPick={addField} onClose={() => setPicking(false)} />}
    </Modal>
  )
}

interface FieldInfo { path: string; title: string; type: string; leaf: boolean; attribute?: boolean }
interface FieldNode { key: string; title: string; isLeaf: boolean; info: FieldInfo; children?: FieldNode[] }

/** Arborele câmpurilor listei (ca „Добавить поля” din 1C): obiectele legate se deschid la clic pe săgeată;
 * clic pe denumire — câmpul (sau obiectul însuși, ca text) devine coloană. */
function FieldPicker({ url, taken, onPick, onClose }: {
  url: string; taken: string[]; onPick: (f: ExtraField) => void; onClose: () => void
}) {
  const { t } = useTranslation()
  const [nodes, setNodes] = useState<FieldNode[] | null>(null)
  const titles = useRef<Record<string, string>>({})
  const toNodes = (items: FieldInfo[], parent: string): FieldNode[] => items.map((f) => {
    titles.current[f.path] = parent ? `${parent} → ${f.title}` : f.title
    return { key: f.path, title: f.title, isLeaf: f.type !== 'object' || f.leaf, info: f }
  })
  useEffect(() => {
    api.get<FieldInfo[]>('/list-fields/', { params: { url } }).then((r) => setNodes(toNodes(r.data, ''))).catch((e) => { message.error(errorText(e)); setNodes([]) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url])
  const attach = (list: FieldNode[], key: string, children: FieldNode[]): FieldNode[] => list.map((n) => (
    n.key === key ? { ...n, children } : n.children ? { ...n, children: attach(n.children, key, children) } : n))
  const load = async (key: string) => {
    const { data } = await api.get<FieldInfo[]>('/list-fields/', { params: { url, path: key } })
    setNodes((cur) => attach(cur ?? [], key, toNodes(data, titles.current[key] ?? '')))
  }
  return (
    <Modal open onCancel={onClose} footer={null} width={520} title={t('listTools.addField')}>
      <Typography.Paragraph type="secondary">{t('listTools.addFieldHint')}</Typography.Paragraph>
      {nodes === null ? <Spin /> : (
        <div style={{ maxHeight: 480, overflow: 'auto' }}>
          <Tree<FieldNode> treeData={nodes} loadData={(n) => load(String(n.key))} blockNode
            titleRender={(n) => (
              <span style={{ opacity: taken.includes(n.info.path) ? 0.45 : 1 }}>
                {n.title}{n.info.type === 'object' && <Typography.Text type="secondary"> …</Typography.Text>}
              </span>
            )}
            onSelect={(_, e) => {
              const f = e.node.info
              if (!taken.includes(f.path)) onPick({ path: f.path, title: titles.current[f.path] ?? f.title, type: f.type })
            }} />
        </div>
      )}
    </Modal>
  )
}

AppTable.Summary = AntTable.Summary
AppTable.SELECTION_COLUMN = AntTable.SELECTION_COLUMN
AppTable.EXPAND_COLUMN = AntTable.EXPAND_COLUMN

export default AppTable

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { CheckOutlined } from '@ant-design/icons'

/**
 * Bara de meniu a unui program de birou (Fișier / Cadre / … / Ajutor): meniurile se deschid în jos, cu submeniuri,
 * separatoare și scurtăturile în dreapta. Din tastatură, ca în Windows:
 * - **Alt** (apăsat și lăsat singur) alege bara: ←/→ mută între meniuri, ↓ / Enter deschide; **Alt+litera subliniată**
 *   deschide direct meniul;
 * - în meniu: ↑/↓ mută, → intră în submeniu (sau trece la meniul următor), ← iese din submeniu (sau trece la cel dinainte),
 *   Enter alege, **Esc** închide submeniul, apoi meniul, apoi bara; Home / End — primul / ultimul rând.
 * Cât bara e aleasă, Esc nu închide fereastra deschisă (windowKeys vede `.dk-menubar:focus-within`).
 */

export type MenuEntry =
  | { kind: 'item'; key: string; label: string; icon?: ReactNode; shortcut?: string; disabled?: boolean; checked?: boolean; onSelect: () => void }
  | { kind: 'sub'; key: string; label: string; icon?: ReactNode; items: MenuEntry[]; disabled?: boolean }
  | { kind: 'sep'; key: string }

export interface MenuDef { key: string; label: string; items: MenuEntry[]; current?: boolean }

const selectable = (e: MenuEntry | undefined) => !!e && e.kind !== 'sep' && !e.disabled && (e.kind !== 'sub' || e.items.length > 0)

function step(items: MenuEntry[], from: number, dir: 1 | -1): number {
  const n = items.length
  for (let k = 1; k <= n; k++) {
    const i = (((from + dir * k) % n) + n) % n
    if (selectable(items[i])) return i
  }
  return -1
}

const firstSelectable = (items: MenuEntry[]) => step(items, -1, 1)
const lastSelectable = (items: MenuEntry[]) => step(items, 0, -1)

/** Litera fără diacritice (Î → I, Ș → S), pentru Alt+litera. */
const plain = (ch: string) => ch.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase()

/** Litera de acces a fiecărui meniu: prima literă latină din denumire pe care n-o are alt meniu dinainte. */
function mnemonics(labels: string[]): { index: number; letter: string }[] {
  const used = new Set<string>()
  return labels.map((label) => {
    for (let i = 0; i < label.length; i++) {
      const letter = plain(label[i])
      if (/^[A-Z]$/.test(letter) && !used.has(letter)) {
        used.add(letter)
        return { index: i, letter }
      }
    }
    return { index: -1, letter: '' }
  })
}

function Label({ text, at, show }: { text: string; at: number; show: boolean }) {
  if (at < 0) return <>{text}</>
  return <>{text.slice(0, at)}<span className={show ? 'dk-mnemonic is-shown' : 'dk-mnemonic'}>{text[at]}</span>{text.slice(at + 1)}</>
}

/** Lista unui meniu (și, în ea, submeniul rândului ales). `path` — rândurile alese, câte unul pe nivel, de la acest nivel. */
function Popup({ items, path, level, onHot, onPick, className }: {
  items: MenuEntry[]
  path: number[]
  level: number
  onHot: (level: number, index: number) => void
  onPick: (entry: MenuEntry, level: number, index: number) => void
  className: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [flip, setFlip] = useState(false)
  // lista care nu încape în dreapta ecranului se mută spre stânga (submeniul se deschide în stânga rândului)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.removeProperty('--dk-shift')
    const rect = el.getBoundingClientRect()
    if (level > 0) setFlip(rect.right > window.innerWidth - 4)
    else if (rect.right > window.innerWidth - 4) el.style.setProperty('--dk-shift', `${Math.ceil(window.innerWidth - 4 - rect.right)}px`)
  }, [level, items])
  const hot = path[0]
  return (
    <div ref={ref} role="menu" className={`${className}${flip ? ' is-flipped' : ''}`} onMouseDown={(e) => e.preventDefault()}>
      {items.map((entry, i) => {
        if (entry.kind === 'sep') return <div key={entry.key} className="dk-menu-sep" role="separator" />
        const disabled = !selectable(entry)
        const isHot = i === hot
        return (
          <div key={entry.key} role={entry.kind === 'item' && entry.checked !== undefined ? 'menuitemcheckbox' : 'menuitem'}
            aria-checked={entry.kind === 'item' && entry.checked !== undefined ? entry.checked : undefined}
            aria-disabled={disabled || undefined} aria-haspopup={entry.kind === 'sub' || undefined}
            className={`dk-menu-item${isHot ? ' is-hot' : ''}${disabled ? ' is-disabled' : ''}`}
            onMouseEnter={() => onHot(level, i)} onClick={() => { if (!disabled) onPick(entry, level, i) }}>
            <span className="dk-menu-icon">{entry.kind === 'item' && entry.checked ? <CheckOutlined /> : entry.icon}</span>
            <span className="dk-menu-label">{entry.label}</span>
            <span className="dk-menu-key">{entry.kind === 'item' ? entry.shortcut : ''}</span>
            <span className="dk-menu-arrow">{entry.kind === 'sub' ? '▸' : ''}</span>
            {entry.kind === 'sub' && isHot && !disabled && (
              <Popup items={entry.items} path={path.slice(1)} level={level + 1} onHot={onHot} onPick={onPick} className="dk-menu-popup dk-submenu" />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function MenuBar({ menus, label }: { menus: MenuDef[]; label: string }) {
  const root = useRef<HTMLDivElement>(null)
  const titles = useRef<(HTMLButtonElement | null)[]>([])
  const prevFocus = useRef<HTMLElement | null>(null)
  /** meniul deschis (null — niciunul) */
  const [open, setOpen] = useState<number | null>(null)
  /** rândurile alese în meniul deschis, câte unul pe nivel */
  const [path, setPath] = useState<number[]>([])
  /** bara e aleasă din tastatură (Alt), fără meniu deschis: meniul cu „focus” */
  const [focusIdx, setFocusIdx] = useState<number | null>(null)
  /** literele de acces se văd (s-a lucrat din tastatură) */
  const [keys, setKeys] = useState(false)
  const keysOf = useMemo(() => mnemonics(menus.map((m) => m.label)), [menus])
  const state = useRef({ open, path, focusIdx, menus })
  state.current = { open, path, focusIdx, menus }

  const active = open !== null || focusIdx !== null

  const enter = useCallback(() => {
    if (root.current && !root.current.contains(document.activeElement)) {
      prevFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
      root.current.focus({ preventScroll: true })
    }
  }, [])

  /** Iese din bară: închide meniul și întoarce cursorul unde era (câmpul din formă). */
  const leave = useCallback(() => {
    setOpen(null)
    setPath([])
    setFocusIdx(null)
    setKeys(false)
    const back = prevFocus.current
    prevFocus.current = null
    if (back && back.isConnected) back.focus({ preventScroll: true })
    else if (root.current?.contains(document.activeElement)) (document.activeElement as HTMLElement).blur()
  }, [])

  const openMenu = useCallback((i: number, highlightFirst: boolean) => {
    const items = state.current.menus[i]?.items ?? []
    enter()
    setOpen(i)
    setFocusIdx(null)
    setPath(highlightFirst ? [firstSelectable(items)].filter((x) => x >= 0) : [])
  }, [enter])

  const pick = useCallback((entry: MenuEntry, level: number, index: number) => {
    if (entry.kind === 'sub') {
      setPath((p) => [...p.slice(0, level), index, firstSelectable(entry.items)].filter((x) => x >= 0))
      return
    }
    if (entry.kind !== 'item' || entry.disabled) return
    leave()
    entry.onSelect()
  }, [leave])

  // Alt singur (apăsat și lăsat fără altă tastă) alege bara; Alt+litera deschide meniul cu acea literă
  useEffect(() => {
    let armed = false
    const down = (e: KeyboardEvent) => {
      if (e.key === 'Alt') {
        armed = !e.repeat && !e.ctrlKey && !e.metaKey && !e.shiftKey
        return
      }
      armed = false
      if (!e.altKey || e.ctrlKey || e.metaKey || e.getModifierState?.('AltGraph') || !/^Key[A-Z]$/.test(e.code)) return
      const i = keysOf.findIndex((k) => k.letter === e.code.slice(3))
      if (i < 0) return
      e.preventDefault()
      e.stopPropagation()
      setKeys(true)
      openMenu(i, true)
    }
    const up = (e: KeyboardEvent) => {
      if (e.key !== 'Alt' || !armed) return
      armed = false
      e.preventDefault()
      const { open: o, focusIdx: f, menus: list } = state.current
      if (o !== null || f !== null) leave()
      else if (list.length) {
        enter()
        setKeys(true)
        setFocusIdx(0)
      }
    }
    const blurWindow = () => { armed = false }
    window.addEventListener('keydown', down, true)
    window.addEventListener('keyup', up, true)
    window.addEventListener('blur', blurWindow)
    return () => {
      window.removeEventListener('keydown', down, true)
      window.removeEventListener('keyup', up, true)
      window.removeEventListener('blur', blurWindow)
    }
  }, [keysOf, openMenu, leave, enter])

  // clic în afara barei închide meniul
  useEffect(() => {
    if (!active) return
    const onDown = (e: MouseEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) {
        prevFocus.current = null
        setOpen(null)
        setPath([])
        setFocusIdx(null)
        setKeys(false)
      }
    }
    document.addEventListener('mousedown', onDown, true)
    return () => document.removeEventListener('mousedown', onDown, true)
  }, [active])

  const onKeyDown = (e: React.KeyboardEvent) => {
    const n = menus.length
    if (!n) return
    const handled = () => { e.preventDefault(); e.stopPropagation() }
    setKeys(true)
    if (open === null) {
      const at = focusIdx ?? 0
      if (e.key === 'ArrowRight') { handled(); setFocusIdx((at + 1) % n) }
      else if (e.key === 'ArrowLeft') { handled(); setFocusIdx((at + n - 1) % n) }
      else if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') { handled(); openMenu(at, true) }
      else if (e.key === 'Escape' || e.key === 'Tab') { handled(); leave() }
      else if (/^[a-zA-Z]$/.test(e.key)) {
        const i = keysOf.findIndex((k) => k.letter === e.key.toUpperCase())
        if (i >= 0) { handled(); openMenu(i, true) }
      }
      return
    }
    // listele de pe drum: meniul deschis, apoi submeniurile rândurilor alese
    const lists: MenuEntry[][] = [menus[open].items]
    for (let l = 0; l < path.length - 1; l++) {
      const entry = lists[l][path[l]]
      if (entry?.kind !== 'sub') break
      lists.push(entry.items)
    }
    const level = Math.max(0, Math.min(path.length, lists.length) - 1)
    const items = lists[level]
    const cur = path[level] ?? -1
    const curEntry = items[cur]
    const setAt = (i: number) => setPath((p) => [...p.slice(0, level), i].filter((x) => x >= 0))
    switch (e.key) {
      case 'ArrowDown': handled(); setAt(step(items, cur, 1)); break
      case 'ArrowUp': handled(); setAt(cur < 0 ? lastSelectable(items) : step(items, cur, -1)); break
      case 'Home': handled(); setAt(firstSelectable(items)); break
      case 'End': handled(); setAt(lastSelectable(items)); break
      case 'ArrowRight':
        handled()
        if (curEntry?.kind === 'sub' && selectable(curEntry)) pick(curEntry, level, cur)
        else openMenu((open + 1) % n, true)
        break
      case 'ArrowLeft':
        handled()
        if (path.length > 1) setPath((p) => p.slice(0, -1))
        else openMenu((open + n - 1) % n, true)
        break
      case 'Enter':
      case ' ':
        handled()
        if (curEntry && selectable(curEntry)) pick(curEntry, level, cur)
        break
      case 'Escape':
        handled()
        if (path.length > 1) setPath((p) => p.slice(0, -1))
        else { setOpen(null); setPath([]); setFocusIdx(open) }
        break
      case 'Tab': handled(); leave(); break
      default:
        // litera: primul rând (după cel ales) care începe cu ea
        if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
          const letter = plain(e.key)
          for (let k = 1; k <= items.length; k++) {
            const i = (cur + k) % items.length
            const it = items[i]
            if (selectable(it) && it.kind !== 'sep' && plain(it.label.charAt(0)) === letter) { handled(); setAt(i); break }
          }
        }
    }
  }

  return (
    <div ref={root} className={`dk-menubar${active ? ' is-active' : ''}`} role="menubar" aria-label={label} tabIndex={-1}
      onKeyDown={onKeyDown}
      onBlur={(e) => {
        if (!root.current?.contains(e.relatedTarget as Node | null)) {
          setOpen(null); setPath([]); setFocusIdx(null); setKeys(false); prevFocus.current = null
        }
      }}>
      {menus.map((m, i) => (
        <div key={m.key} className="dk-menu-slot">
          <button type="button" tabIndex={-1} ref={(el) => { titles.current[i] = el }} role="menuitem" aria-haspopup="menu" aria-expanded={open === i}
            className={`dk-menu-title${open === i ? ' is-open' : ''}${focusIdx === i ? ' is-hot' : ''}${m.current ? ' is-current' : ''}`}
            onMouseDown={(e) => {
              e.preventDefault()
              if (open === i) leave()
              else openMenu(i, false)
            }}
            onMouseEnter={() => { if (open !== null && open !== i) openMenu(i, false) }}>
            <Label text={m.label} at={keysOf[i]?.index ?? -1} show={keys} />
          </button>
          {open === i && (
            <Popup items={m.items} path={path} level={0} className="dk-menu-popup"
              onHot={(level, index) => setPath((p) => [...p.slice(0, level), index])} onPick={pick} />
          )}
        </div>
      ))}
    </div>
  )
}

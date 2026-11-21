import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Modal, Typography } from 'antd'

import { useTabs } from './tabs'

const HOME = '/'

/** Ce e deschis peste pagină și își ia singur Esc-ul: o fereastră, un sertar, o listă derulantă, un calendar, un meniu. */
const OVERLAYS = [
  '.ant-modal-wrap:not([style*="display: none"])', '.ant-drawer-open', '.ant-select-dropdown:not(.ant-select-dropdown-hidden)',
  '.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)', '.ant-dropdown:not(.ant-dropdown-hidden)', '.ant-popover:not(.ant-popover-hidden)',
  '.ant-image-preview-wrap', '.ant-tour',
  // bara de meniu a aspectului clasic de birou, cât e aleasă din tastatură (Alt) sau are un meniu deschis
  '.dk-menubar:focus-within', '.dk-menu-popup',
].join(',')

/** „Ferestrele deschise” deschise din altă parte (bara de unelte, meniul Ferestre). */
const showListeners = new Set<() => void>()
export function showOpenWindows() {
  showListeners.forEach((l) => l())
}

function overlayOpen() {
  return Array.from(document.querySelectorAll<HTMLElement>(OVERLAYS)).some((el) => el.offsetParent !== null || el.getClientRects().length > 0)
}

/**
 * Tastele ferestrelor, ca în 1C:
 * - **Esc** închide pagina deschisă (forma sau lista) și fila ei de jos; cu modificări nesalvate întreabă întâi
 *   „Salvați modificările?” (UnsavedGuard). Cât e deschisă o fereastră, o listă derulantă sau un calendar, Esc le închide
 *   pe ele, nu pagina.
 * - **Alt+`** deschide lista „Ferestrele deschise”: săgețile sau Alt+` mută, Enter deschide, cifra 1–9 deschide direct,
 *   Esc închide lista.
 */
export default function WindowKeys() {
  const { t } = useTranslation()
  const { tabs, close } = useTabs()
  const location = useLocation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [sel, setSel] = useState(0)
  const items = [{ path: HOME, title: t('tabs.home') }, ...tabs]
  const current = location.pathname === HOME ? 0 : Math.max(0, items.findIndex((x) => x.path.split('?')[0] === location.pathname))
  // ultimele valori pentru ascultătorul de taste (pus o singură dată)
  const state = useRef({ open, sel, items, current })
  state.current = { open, sel, items, current }

  useEffect(() => {
    const show = () => {
      const { current: here, items: list } = state.current
      setSel((here + 1) % list.length)
      setOpen(true)
    }
    showListeners.add(show)
    return () => { showListeners.delete(show) }
  }, [])

  useEffect(() => {
    const go = (i: number) => {
      const item = state.current.items[i]
      setOpen(false)
      if (item && i !== state.current.current) navigate(item.path)
    }
    const onKey = (e: KeyboardEvent) => {
      const { open: isOpen, sel: at, items: list, current: here } = state.current
      if (e.altKey && e.code === 'Backquote') {
        e.preventDefault()
        if (isOpen) setSel((at + (e.shiftKey ? list.length - 1 : 1)) % list.length)
        else if (!overlayOpen()) {
          setSel((here + 1) % list.length)
          setOpen(true)
        }
        return
      }
      if (isOpen) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault()
          setSel((at + (e.key === 'ArrowDown' ? 1 : list.length - 1)) % list.length)
        } else if (e.key === 'Enter') {
          e.preventDefault()
          go(at)
        } else if (/^[1-9]$/.test(e.key) && Number(e.key) <= list.length) {
          e.preventDefault()
          go(Number(e.key) - 1)
        } else if (e.key === 'Escape') {
          e.preventDefault()
          e.stopPropagation()
          setOpen(false)
        }
        return
      }
      if (e.key === 'Escape' && !e.defaultPrevented && !e.repeat && !overlayOpen() && here > 0) {
        e.preventDefault()
        close(list[here].path)
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [navigate, close])

  return (
    <Modal open={open} title={t('tabs.windows')} footer={null} onCancel={() => setOpen(false)} keyboard={false} width={420} destroyOnHidden
      styles={{ body: { maxHeight: '60vh', overflowY: 'auto', padding: 0 } }}>
      <div role="listbox" aria-label={t('tabs.windows')}>
        {items.map((x, i) => (
          <div key={x.path} role="option" aria-selected={i === sel} onMouseMove={() => { if (i !== sel) setSel(i) }}
            onClick={() => { setOpen(false); if (i !== current) navigate(x.path) }}
            ref={(el) => { if (el && i === sel) el.scrollIntoView({ block: 'nearest' }) }}
            style={{
              display: 'flex', gap: 12, padding: '7px 12px', cursor: 'pointer', borderRadius: 6,
              background: i === sel ? 'var(--ant-color-warning-bg)' : undefined,
              color: i === sel ? 'var(--ant-color-warning-text)' : undefined, fontWeight: i === current ? 600 : 500,
            }}>
            <span style={{ width: 16, textAlign: 'right', color: 'var(--ant-color-text-tertiary)' }}>{i < 9 ? i + 1 : ''}</span>
            <span>{x.title}</span>
          </div>
        ))}
      </div>
      <Typography.Paragraph type="secondary" style={{ fontSize: 12, margin: '12px 12px 4px' }}>{t('tabs.windowsHint')}</Typography.Paragraph>
    </Modal>
  )
}

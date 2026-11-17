import { forwardRef, useImperativeHandle, useRef } from 'react'

export interface PrintFrameHandle {
  /** Tipărește ce se vede; cu `html` — întâi pune în cadru acest HTML (documentul final) și tipărește după încărcare. */
  print: (html?: string) => void
}

/**
 * Afișează HTML-ul unei forme de tipar. iframe-ul e izolat (sandbox fără scripturi), dar aceeași
 * origine permite ca butonul „Tipărește” din aplicație să deschidă dialogul de tipar al browserului.
 */
const PrintFrame = forwardRef<PrintFrameHandle, { html: string; height?: number | string }>(
  ({ html, height = 600 }, ref) => {
    const frame = useRef<HTMLIFrameElement>(null)
    useImperativeHandle(ref, () => ({
      print: (next?: string) => {
        const el = frame.current
        const go = () => {
          const win = el?.contentWindow
          if (win) {
            win.focus()
            win.print()
          }
        }
        if (el && next !== undefined && el.srcdoc !== next) {
          // documentul final se tipărește dintr-un cadru ascuns, ca previzualizarea (cadrul React) să rămână neatinsă
          const hidden = document.createElement('iframe')
          hidden.setAttribute('sandbox', 'allow-same-origin allow-modals')
          hidden.style.cssText = 'position:fixed;width:0;height:0;border:0;visibility:hidden'
          hidden.addEventListener('load', () => {
            hidden.contentWindow?.focus()
            hidden.contentWindow?.print()
            setTimeout(() => hidden.remove(), 1000)
          }, { once: true })
          hidden.srcdoc = next
          document.body.appendChild(hidden)
        } else go()
      },
    }))
    return (
      <iframe
        ref={frame}
        title="print"
        sandbox="allow-same-origin allow-modals"
        srcDoc={html}
        style={{ width: '100%', height, border: '1px solid var(--ant-color-border)', borderRadius: 8, background: '#fff' }}
      />
    )
  },
)

export default PrintFrame

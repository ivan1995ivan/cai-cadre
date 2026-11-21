import { useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useBlocker } from 'react-router-dom'
import { App, Button, Space } from 'antd'

import { PageScopeContext } from '../api/pageScope'
import { useTabs } from '../layout/tabs'

/**
 * „Salvați modificările?” (ca în 1C) când se pleacă din forma cu modificări nesalvate — Esc, ✕, altă filă, meniul,
 * înapoi: Da — se salvează și se pleacă (dacă salvarea nu reușește, se rămâne în formă), Nu — se pleacă fără ele,
 * Anulare (sau Esc) — se rămâne. La închiderea sau reîncărcarea paginii browserul își pune întrebarea lui.
 * Hook-ul nu randează nimic: fereastra o deschide singur. În aspectul clasic de birou se salvează și cu „Salvează” din
 * bara de unelte (Ctrl+S), vezi api/pageScope. `save` a salvat dacă nu întoarce `false` și nu aruncă (de ex.
 * un câmp obligatoriu gol). Un singur gardian pe pagină.
 */
export function useUnsavedGuard(dirty: boolean, save: () => Promise<unknown>) {
  const { t } = useTranslation()
  const { keepClosing } = useTabs()
  const { modal } = App.useApp()
  const blocker = useBlocker(({ currentLocation, nextLocation }) => dirty && currentLocation.pathname !== nextLocation.pathname)
  const saveRef = useRef(save)
  saveRef.current = save

  // „Salvează” din bara de unelte și Ctrl+S (aspectul clasic de birou) fac ce face „Da” din întrebare
  const scope = useContext(PageScopeContext)
  const guardId = useRef<number | null>(null)
  useEffect(() => {
    if (!scope) return
    const id = scope.addGuard({ dirty: false, save: () => saveRef.current() })
    guardId.current = id
    return () => {
      scope.removeGuard(id)
      guardId.current = null
    }
  }, [scope])
  useEffect(() => {
    if (scope && guardId.current !== null) scope.updateGuard(guardId.current, { dirty, save: () => saveRef.current() })
  }, [scope, dirty])

  useEffect(() => {
    if (!dirty) return
    const ask = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', ask)
    return () => window.removeEventListener('beforeunload', ask)
  }, [dirty])

  useEffect(() => {
    if (blocker.state !== 'blocked') return
    let done = false
    const finish = (go: boolean) => {
      if (done) return
      done = true
      dialog.destroy()
      if (go) blocker.proceed?.()
      else {
        keepClosing()
        blocker.reset?.()
      }
    }
    const yes = async () => {
      let ok = false
      try {
        ok = (await saveRef.current()) !== false
      } catch {
        ok = false
      }
      finish(ok)
    }
    const dialog = modal.confirm({
      title: t('unsaved.title'), content: t('unsaved.text'), closable: true, maskClosable: false, keyboard: true,
      onCancel: () => finish(false),
      footer: <GuardButtons yes={t('unsaved.yes')} no={t('unsaved.no')} cancel={t('unsaved.cancel')}
        onYes={yes} onNo={() => finish(true)} onCancel={() => finish(false)} />,
    })
    return () => {
      done = true
      dialog.destroy()
    }
  }, [blocker.state]) // eslint-disable-line react-hooks/exhaustive-deps
}

function GuardButtons({ yes, no, cancel, onYes, onNo, onCancel }: {
  yes: string; no: string; cancel: string; onYes: () => Promise<void>; onNo: () => void; onCancel: () => void
}) {
  const [saving, setSaving] = useState(false)
  return (
    <Space style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
      <Button type="primary" loading={saving} autoFocus onClick={async () => {
        setSaving(true)
        try {
          await onYes()
        } finally {
          setSaving(false)
        }
      }}>{yes}</Button>
      <Button disabled={saving} onClick={onNo}>{no}</Button>
      <Button disabled={saving} onClick={onCancel}>{cancel}</Button>
    </Space>
  )
}

/**
 * Gardianul unei pagini cu „Salvează”: `touch` la orice schimbare (Form `onValuesChange`), `clean` după încărcare sau
 * salvare; plecarea cu modificări întreabă „Salvați modificările?” (Da salvează cu `save`). `enabled` — doar cine poate
 * schimba.
 */
export function useEditGuard(save: () => Promise<unknown>, enabled = true) {
  const [dirty, setDirty] = useState(false)
  const touch = useCallback(() => setDirty(true), [])
  const clean = useCallback(() => setDirty(false), [])
  useUnsavedGuard(dirty && enabled, async () => {
    const ok = (await save()) !== false
    if (ok) setDirty(false)
    return ok
  })
  return { dirty, touch, clean }
}

// Fișierele private (fotografiile, scanările actelor, semnătura, ștampila): serverul le dă doar prin API, cu sesiunea
// utilizatorului (antetul Authorization), nu prin /media/. Adresa vine de la server relativă la /api (cu `?v=` după fișier).
import { useEffect, useState } from 'react'

import { api } from './client'

const INLINE = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp', 'image/gif']

/** Adresa locală (blob:) a fișierului privat, pentru <img> / <Avatar>; undefined cât se încarcă sau fără fișier. */
export function usePrivateUrl(path: string | null | undefined) {
  const [url, setUrl] = useState<string>()
  useEffect(() => {
    if (!path) { setUrl(undefined); return undefined }
    let alive = true
    let made: string | undefined
    api.get(path, { responseType: 'blob' })
      .then((r) => { if (alive) { made = URL.createObjectURL(r.data as Blob); setUrl(made) } })
      .catch(() => { if (alive) setUrl(undefined) })
    return () => { alive = false; if (made) URL.revokeObjectURL(made) }
  }, [path])
  return url
}

/** Deschide fișierul privat într-o filă nouă (PDF, imagine); alt tip de fișier se descarcă. Fila se deschide înaintea cererii,
 *  ca browserul să n-o blocheze. */
export async function openPrivate(path: string) {
  const tab = window.open('', '_blank')
  try {
    const r = await api.get(path, { responseType: 'blob' })
    const blob = r.data as Blob
    const url = URL.createObjectURL(blob)
    if (tab && INLINE.includes(blob.type)) {
      tab.location.href = url
    } else {
      tab?.close()
      const name = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(String(r.headers['content-disposition'] ?? ''))?.[1]
      const a = document.createElement('a')
      a.href = url
      a.download = name ? decodeURIComponent(name) : 'fisier'
      a.click()
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch (e) {
    tab?.close()
    throw e
  }
}

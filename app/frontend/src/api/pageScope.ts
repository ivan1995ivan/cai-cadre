import { createContext } from 'react'

/**
 * Ce știe bara de unelte (aspectul „Clasic de birou”) despre fereastra activă, din mecanismele comune ale paginilor, fără
 * ca paginile să fie rescrise:
 * - **formele cu „Salvați modificările?”** (useUnsavedGuard / useEditGuard) își spun aici dacă au modificări nesalvate și
 *   cum se salvează — butonul „Salvează” (și Ctrl+S) face exact ce face „Da” din întrebare;
 * - **datele încărcate cu useFetch** își dau aici reîncărcarea — „Reîmprospătează” le cere din nou de la server.
 * Stă în jurul paginii (Outlet); ce e în afara ei (meniul, notificările) nu intră.
 */
export interface PageGuard { dirty: boolean; save: () => Promise<unknown> }

export interface PageScopeSnapshot {
  /** o formă a paginii are modificări nesalvate */
  dirty: boolean
  /** câte încărcări de date (useFetch) are pagina */
  loaders: number
}

export class PageScope {
  private guards = new Map<number, PageGuard>()
  private loaders = new Set<() => unknown>()
  private listeners = new Set<() => void>()
  private snap: PageScopeSnapshot = { dirty: false, loaders: 0 }
  private seq = 0

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => { this.listeners.delete(listener) }
  }

  snapshot = () => this.snap

  private emit() {
    const dirty = [...this.guards.values()].some((g) => g.dirty)
    const loaders = this.loaders.size
    if (dirty !== this.snap.dirty || loaders !== this.snap.loaders) {
      this.snap = { dirty, loaders }
      this.listeners.forEach((l) => l())
    }
  }

  /** Gardianul unei forme; întoarce cheia lui (pentru actualizare și scoatere). */
  addGuard(guard: PageGuard) {
    const id = ++this.seq
    this.guards.set(id, guard)
    this.emit()
    return id
  }

  updateGuard(id: number, guard: PageGuard) {
    if (!this.guards.has(id)) return
    this.guards.set(id, guard)
    this.emit()
  }

  removeGuard(id: number) {
    this.guards.delete(id)
    this.emit()
  }

  addLoader(reload: () => unknown) {
    this.loaders.add(reload)
    this.emit()
    return () => {
      this.loaders.delete(reload)
      this.emit()
    }
  }

  /** Salvează formele cu modificări; `false` — salvarea n-a reușit (forma își arată singură greșelile). */
  async save(): Promise<boolean> {
    let ok = true
    for (const g of [...this.guards.values()].filter((x) => x.dirty)) {
      try {
        if ((await g.save()) === false) ok = false
      } catch {
        ok = false
      }
    }
    return ok
  }

  /** Cere din nou datele paginii de la server. */
  reload() {
    this.loaders.forEach((reload) => reload())
  }
}

export const PageScopeContext = createContext<PageScope | null>(null)

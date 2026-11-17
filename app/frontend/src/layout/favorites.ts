import { useCallback } from 'react'
import { message } from 'antd'

import { api, errorText } from '../api/client'
import { useApp } from '../auth/AppContext'

export interface Favorite { path: string; key: string; title: string }

/** Favoritele utilizatorului (stânga jos): funcții din meniu sau pagini anume; se țin pe utilizator, pe server. */
export function useFavorites() {
  const { me, reloadMe } = useApp()
  const favorites: Favorite[] = me?.favorites ?? []
  const isFavorite = useCallback((path: string) => favorites.some((f) => f.path === path.split('?')[0]), [favorites])
  const toggle = useCallback(async (fav: Favorite) => {
    const next = favorites.some((f) => f.path === fav.path) ? favorites.filter((f) => f.path !== fav.path) : [...favorites, fav]
    try {
      await api.patch('/auth/me/', { favorites: next })
      await reloadMe()
    } catch (e) {
      message.error(errorText(e))
    }
  }, [favorites, reloadMe])
  return { favorites, isFavorite, toggle }
}

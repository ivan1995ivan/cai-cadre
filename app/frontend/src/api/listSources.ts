/**
 * De unde vine o listă paginată: rezultatele primite de useFetch → adresa și filtrele lor. Exportul în Excel al
 * tabelului cere, după ele, toate paginile (nu doar cea afișată), cu aceleași filtre.
 */
export interface ListSource { url: string; params: Record<string, unknown>; count: number }

const sources = new WeakMap<object, ListSource>()

export function rememberList(data: unknown, url: string, params: Record<string, unknown>) {
  const paged = data as { results?: unknown; count?: unknown } | null
  if (paged && Array.isArray(paged.results) && typeof paged.count === 'number') {
    sources.set(paged.results, { url, params, count: paged.count })
  }
}

export function listSource(rows: unknown): ListSource | undefined {
  return rows && typeof rows === 'object' ? sources.get(rows as object) : undefined
}

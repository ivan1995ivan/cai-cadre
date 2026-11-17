// Tipurile generale ale interfeței (dicționare, utilizatori, forme de tipar). Modulele de cadre au fișierele lor în api/.

export interface Dict {
  id: number
  code: string
  name_ro: string
  name_ru: string
  name_en?: string
  sort: number
  is_active: boolean
  color?: string
}

export interface UserLookup {
  id: number
  name: string
  username: string
  is_manager?: boolean
}

export interface PrintColumn {
  field: string
  title_ro: string
  title_ru: string
  width: number | null
  align: '' | 'left' | 'center' | 'right'
  factor: number | null
  decimals: number | null
}

export interface PrintTemplate {
  id: number
  doc_type: string
  code: string
  name: string
  body: string
  css: string
  orientation: 'portrait' | 'landscape'
  default_options: Record<string, boolean>
  texts: { ro?: Record<string, string>; ru?: Record<string, string>; en?: Record<string, string> }
  style: { font_size?: 'small' | 'normal' | 'large'; show_logo?: boolean }
  text_fields: { key: string; label: string; ro: string; ru: string; multiline: boolean }[]
  columns?: PrintColumn[]
  placeholders?: string[]
  is_default: boolean
  is_active: boolean
  is_system: boolean
  modified: boolean
  updated_at: string
}

import { useTranslation } from 'react-i18next'
import { theme } from 'antd'

import { PRODUCT } from '../product'

const BRAND = '#534ab7'
const BRAND_ON_DARK = '#a39cf0'

/** Ștampila dezvoltatorului: sigla integrații și „Dezvoltat de integrații”, cu legătura spre site; `iconOnly` = doar sigla
 *  (meniul strâns). */
export default function DevelopedBy({ size = 'default', iconOnly = false }: { size?: 'small' | 'default'; iconOnly?: boolean }) {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const bg = token.colorBgContainer
  const dark = bg.startsWith('#') && parseInt(bg.slice(1, 3), 16) < 128
  const icon = size === 'small' ? 26 : 36
  const title = `${t('about.developedBy')} integrații · ${PRODUCT.website}`
  if (iconOnly) {
    return (
      <a href={PRODUCT.url} target="_blank" rel="noreferrer" title={title} style={{ display: 'inline-block' }}>
        <img src="/integratii.svg" alt="integrații" width={icon} height={icon} style={{ display: 'block', borderRadius: icon / 4.5 }} />
      </a>
    )
  }
  return (
    <a href={PRODUCT.url} target="_blank" rel="noreferrer" title={title}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: size === 'small' ? 8 : 10, padding: size === 'small' ? '4px 12px 4px 4px' : '6px 16px 6px 6px',
        border: `1.5px solid ${dark ? BRAND_ON_DARK : BRAND}`, borderRadius: icon / 2 + 8, textDecoration: 'none', lineHeight: 1.1,
      }}>
      <img src="/integratii.svg" alt="" width={icon} height={icon} style={{ display: 'block', borderRadius: icon / 4.5 }} />
      <span style={{ textAlign: 'left' }}>
        <span style={{ display: 'block', fontSize: size === 'small' ? 10 : 11, color: token.colorTextSecondary, letterSpacing: 0.3 }}>
          {t('about.developedBy')}
        </span>
        <span style={{ display: 'block', fontSize: size === 'small' ? 15 : 19, fontWeight: 600, color: dark ? BRAND_ON_DARK : BRAND }}>
          integrații
        </span>
      </span>
    </a>
  )
}

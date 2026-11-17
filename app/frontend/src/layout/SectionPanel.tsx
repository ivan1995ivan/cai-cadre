import { Fragment } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useParams } from 'react-router-dom'
import { ArrowRightOutlined } from '@ant-design/icons'

import { navLabel, type NavItem } from './nav'
import { panelPath, useMainMenuState, useSectionPanel } from './menu'

/** Un bloc al panoului: banda de titlu (gri închis, text alb) și conținutul. */
function Block({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`fn-block ${className ?? ''}`}>
      <h2 className="fn-block-title">{title}</h2>
      <div className="fn-block-body">{children}</div>
    </section>
  )
}

/** Lista de legături a unui bloc de jos (Registre / Clasificatoare / Rapoarte). */
function Links({ items }: { items: NavItem[] }) {
  const { t } = useTranslation()
  return (
    <ul className="fn-links">
      {items.map((i) => (
        <li key={i.path}><Link to={i.path} className="fn-link"><span className="fn-link-icon">{i.icon}</span>{navLabel(t, i)}</Link></li>
      ))}
    </ul>
  )
}

/**
 * Panoul funcțiilor unei secțiuni, ca în 1C: sus documentele blocului (Schema de lucru) ca iconițe mari, cu săgeată între
 * documentul de bază și cel făcut din el; jos Registrele, Clasificatoarele și Rapoartele blocului. Se vede doar ce are
 * utilizatorul în meniu (drepturile și bifele rolului). Administrare rămâne cum e în meniu: lista funcțiilor ei.
 */
export default function SectionPanel() {
  const { t } = useTranslation()
  const { key } = useParams()
  const { sections, ready } = useMainMenuState()
  const section = sections.find((s) => s.key === key)
  const panel = useSectionPanel(section)
  // secțiunea pe care rolul n-o are (sau una ștearsă din meniu): prima secțiune a utilizatorului
  if (!section || !panel) return ready && sections.length ? <Navigate to={panelPath(sections[0].key)} replace /> : null

  const topTitle = panel.plain ? section.label : t(`fnPanel.${panel.top}`)
  return (
    <div className="fn-panel">
      <div className="fn-head">
        <span className="fn-head-icon">{section.iconNode}</span>
        <h1>{section.label}</h1>
      </div>
      {panel.plain ? (
        <Block title={topTitle}><Links items={panel.registers} /></Block>
      ) : (
        <>
          {panel.tiles.length > 0 && (
            <Block title={topTitle} className="fn-scheme">
              <div className="fn-tiles">
                {panel.tiles.map((item, n) => (
                  <Fragment key={item.path}>
                    <Link to={item.path} className="fn-tile">
                      <span className="fn-tile-icon">{item.icon}</span>
                      <span className="fn-tile-label">{navLabel(t, item)}</span>
                    </Link>
                    {n < panel.tiles.length - 1 && (
                      <span className={`fn-flow ${panel.linked[n] ? 'is-linked' : ''}`} aria-hidden>
                        {panel.linked[n] && <ArrowRightOutlined />}
                      </span>
                    )}
                  </Fragment>
                ))}
              </div>
            </Block>
          )}
          <div className="fn-columns">
            {panel.registers.length > 0 && <Block title={t('fnPanel.registers')}><Links items={panel.registers} /></Block>}
            {panel.classifiers.length > 0 && <Block title={t('fnPanel.classifiers')}><Links items={panel.classifiers} /></Block>}
            {panel.reports.length > 0 && <Block title={t('fnPanel.reports')}><Links items={panel.reports} /></Block>}
          </div>
        </>
      )}
    </div>
  )
}

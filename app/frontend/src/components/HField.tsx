import type { ReactNode } from 'react'
import { Col } from 'antd'

/**
 * Un câmp din antetul documentului ca în formele 1C: eticheta la stânga („Factura de ieşire nr.:”), valoarea sau
 * controlul la dreapta, pe rânduri. Pentru antetele care nu sunt <Form> (factura, ruta).
 */
export default function HField({ label, children, md = 6, xs = 24 }: { label: ReactNode; children: ReactNode; md?: number; xs?: number }) {
  return (
    <Col xs={xs} md={md}>
      <div className="hfield">
        <span className="hfield-label">{label}:</span>
        <div className="hfield-control">{children}</div>
      </div>
    </Col>
  )
}

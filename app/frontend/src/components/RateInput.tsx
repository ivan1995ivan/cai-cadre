import { InputNumber, type InputNumberProps } from 'antd'

/**
 * Norma se scrie și se arată în procente (100%, 50%, 25%); pe server rămâne în unități (1 / 0,5 / 0,25), ca în statele
 * de personal. Pe Form.Item: `{...rateProps}` și ca intrare `<RateInput />`.
 */
export const rateProps = {
  getValueProps: (v: unknown) => ({ value: v === null || v === undefined || v === '' ? undefined : Math.round(Number(v) * 10000) / 100 }),
  normalize: (v: number | null) => (v === null || v === undefined ? v : Math.round(v * 100) / 10000),
}

export function RateInput(props: InputNumberProps<number>) {
  return <InputNumber<number> min={1} max={150} step={25} suffix="%" style={{ width: '100%' }} {...props} />
}

export const fmtRate = (v: string | number | null | undefined) =>
  v === null || v === undefined || v === '' ? '' : `${(Number(v) * 100).toLocaleString('ro-MD', { maximumFractionDigits: 2 })}%`

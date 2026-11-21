/**
 * Culoarea textului din rândurile registrelor, după stare (ca în CRM acoperiș gard): albastru — documentul e în lucru,
 * verde — e procesat (încheiat), negru — în rest (ciornă, depus și neatins încă, anulat, respins, retras). Eticheta colorată
 * a stării rămâne în coloana ei; rândul marcat pentru ștergere rămâne gri și tăiat.
 */
export type RowTone = 'work' | 'done'

const tone = (work: string[], done: string[]) => (status: string | null | undefined): RowTone | undefined =>
  (status && done.includes(status) ? 'done' : status && work.includes(status) ? 'work' : undefined)

/** Stările fiecărui registru: [în lucru] → albastru, [procesat] → verde. */
export const ROW_TONE = {
  order: tone([], ['signed']),
  staffList: tone([], ['approved']),
  employeeRequest: tone(['in_work'], ['done']),
  leaveRequest: tone(['approved'], ['ordered']),
  leaveSchedule: tone(['submitted'], ['approved']),
  monthDoc: tone(['submitted'], ['approved', 'closed']), // graficul lunar se încheie cu „Aprobat”, pontajul — cu „Închis”
  payroll: tone(['checked'], ['approved']),
  payment: tone(['approved'], ['paid']),
}

// CAI CADRE 1.5.0: salary in two documents — the calculation (accruals, deductions, CAS) and the payment order (CNAM, the
// exemption and income tax, withheld at payment); “Save changes?” when leaving a form.
export default {
  common: { closeForm: 'Close' },
  unsaved: {
    title: 'Save changes?', text: 'The form has changed and is not saved.',
    yes: 'Yes', no: 'No', cancel: 'Cancel',
  },
  menu: { payrollPayments: 'Payment orders' },
  pay: {
    heading: 'Payroll calculation no. {{number}} of {{date}}', month: 'Month', net: 'Remaining (before tax)',
    approveConfirm: 'An approved calculation no longer changes; its amounts enter the average pay and the payment order. Approve?',
    addItemHint: 'The row survives recalculation; CAS is recomputed automatically. Income tax and CNAM are withheld at payment.',
    corrected: 'Corrected',
    correctHint: 'A manual amount replaces the calculated amount of the same type (salary, allowance, CAS); a type without automatic calculation (one-off bonus, deduction) is added. Income tax and CNAM are not in the calculation — they are withheld in the payment order and corrected there.',
    legend: 'Each row is an employment (main, second job, contract); sick pay and bonuses go to the main one. Expand a row for accruals and deductions. Income tax, CNAM and the exemption are not here: they are withheld at payment, in the payment order made from the approved calculation.',
    toPayment: 'Payment order', toPaymentHint: 'The salary payment order based on this calculation: its employees, with CNAM, the exemption and income tax withheld at payment.',
    paymentRef: 'Payment order no. {{number}} of {{date}}',
    type: { autos: { income_tax: 'Income tax (at payment)', cnam: 'CNAM (at payment)' } },
  },
  pp: {
    tabs: { payments: 'Payment orders' },
    new: 'New payment order', heading: 'Payment order no. {{number}} of {{date}}',
    base: 'Based on calculation', onBalance: 'On balance — the rest of the month from all approved calculations', onBalanceShort: 'on balance',
    baseLabel: 'Calculation no. {{number}} · {{month}}.{{year}}', baseRef: 'Based on: {{label}}',
    baseHint: 'The approved calculation: only its employees, at most its amount. On balance — everything still due for the month, from all approved calculations.',
    advanceNoBase: 'An advance is not based on a calculation.', monthFromBase: 'The month of the base calculation.',
    refillHint: 'On save, a different base, kind, month or method fills the rows again.',
    reopenConfirm: 'The payment order returns to draft. Continue?',
    owed: 'Calculated (gross − deductions)',
    emptyHint: 'There are no payment orders for the chosen month. “New payment order” — the advance (during the month) or the salary (based on the approved calculation or on balance).',
    newHint: 'Advance: the percentage from the constants × base salary × rate of the main job. Salary: gross from the calculation minus what was already paid in the month. CNAM, the exemption and tax are computed on the whole month’s income minus what was already withheld. Card — employees with an IBAN on file; the rest — cash.',
    debtsHint: 'At the end of the chosen month, before tax: gross of approved calculations minus other deductions, minus gross paid (salary and advance). Negative — overpaid.',
    advanceLegend: 'From the advance, 9% CNAM and 12% tax on the rest are withheld. In the salary payment order the month’s taxes are computed on the whole income, with the exemption, minus what was withheld from the advance.',
    salaryLegend: 'Gross comes from the calculation (the base one or, on balance, all approved calculations of the month) minus what was already paid. CNAM, the month’s exemption and tax — on all income paid in the month, minus what was already withheld. They can be corrected in draft; once paid they enter the annual card, IPC21 and IALS21.',
  },
  tax: {
    ipcHint: 'Monthly return (by the 25th of the next month). Table 1: income paid in the month and the tax and CNAM withheld — from paid payment orders. Table 2: the CAS base per person — from the month’s approved calculations. The electronic return is filled from them.',
    ialsHint: 'Annual information note (by 25 January): income paid in the year, exemptions with the request code, CNAM and tax withheld, per person — from paid payment orders.',
  },
}

// CAI CADRE — Stage 4b (part 2): salary payment and reporting.
export default {
  print: { docTypes: { payment_sheet: 'Payment sheet', bank_list: 'Bank list', annual_card: 'Annual personal income card' } },
  pp: {
    tabs: { payments: 'Payment sheets', debts: 'Salary debts' },
    new: 'New payment', kind: 'What is paid', kinds: { salary: 'Salary', advance: 'Advance' }, method: 'Method',
    methods: { all: 'Card and cash', card: 'Card (bank)', cash: 'Cash (cash desk)' }, count: 'People', card: 'By card', cash: 'Cash',
    total: 'Total', paidOn: 'Paid on', owed: 'Calculated (net + advance)', paidSum: 'Paid', debt: 'Debt',
    emptyHint: 'There are no payments for the chosen month. “New payment” — the advance (during the month) or the salary (from the approved calculation).',
    newHint: 'Advance: the percentage from the constants × base salary × rate of the main job. Salary: net pay from the month’s approved calculations minus what was already paid. Card — employees with an IBAN on file; the rest — cash.',
    debtsHint: 'At the end of the chosen month: net pay of approved calculations (with withheld advances) minus everything paid. Negative — overpaid.',
    heading: '{{kind}} no. {{number}} — {{month}} {{year}}', refill: 'Fill again', refillConfirm: 'Amounts are recalculated; manual corrections are lost. Continue?',
    pay: 'Mark as paid', printSheet: 'Payment sheet', bankList: 'Bank list', bankFile: 'Bank file (CSV)',
    reference: 'Payment document', referenceHint: 'Payment order (card) or cash disbursement order (cash).',
    advanceLegend: 'An approved advance is deducted automatically in the salary calculation of its month (“Advance paid” row).',
    salaryLegend: 'Amounts come from the month’s approved calculations (net, after advance and deductions). They can be corrected in draft; once paid they count as paid in the debts.',
    annualCard: 'Annual personal income card (annex 8)',
  },
  tax: {
    export: 'Export to Excel', missingIdnp: '{{count}} people without IDNP — fill it in the file before filing.',
    category: 'Insured person category code', source: 'Income source code', event: 'Event', deadline: 'Deadline',
    cols: { income: 'Income', cas: 'Social insurance', cnam: 'Health insurance', tax: 'Tax withheld', exemption: 'Exemptions' },
    ipcHint: 'Monthly return (by the 25th of the next month): from the month’s approved calculations, per person. The export has table 1 (totals) and table 2 (persons); the electronic return is filled from it.',
    ialsHint: 'Annual information note (by 25 January): the year’s income, exemptions with the request code, health insurance and tax withheld, per person.',
    irmHint: 'Hirings, changes and terminations from signed orders (types marked “IRM19” in the dictionary); filed with CNAS within 10 working days — overdue deadlines in red.',
    categoryHint: 'The code from annex 3 to the Ministry of Finance order (check on every change); applied to everyone.',
    sourceHint: 'Usually SAL (salary).',
  },
}

// CAI CADRE 1.5.1: payslips from the payment order; Esc closes the page, Alt+` — open windows.
export default {
  print: {
    docTypes: { certificate_salary: 'Salary certificate (for the bank)' },
    options: { show_idnp: 'With IDNP', show_salary: 'With salary', show_photo: 'With photo', show_family: 'With family', show_military: 'With military record', show_periods: 'With work periods', group_by_subdivision: 'Grouped by subdivision', show_phone: 'With phone', show_rate: 'With rate', show_fund: 'With payroll fund', show_categories: 'With categories' },
  },
  common: { closeForm: 'Close (Esc)' },
  tabs: {
    windows: 'Open windows',
    windowsHint: 'Arrows or Alt+` move, Enter opens, digit 1–9 opens directly, Esc closes the list.',
  },
  staff: {
    print: { certificate_salary: 'Salary certificate (for the bank)' },
    salaryPeriod: 'Period', salaryLastMonths: 'Last {{count}} months', salaryRange: 'Range of months…',
    purposeBankHint: 'e.g. BC “Moldindconbank” SA, for a loan',
  },
  ord: {
    title: 'Title', preamble: 'Preamble',
    numberDate: 'No. and date', seqAuto: 'auto', of: 'of', legalBases: 'Legal grounds',
    legalBasesHint: 'One or more; the preamble is composed from them.', signer: 'Signed by',
  },
  org: { legalBases: 'Default legal grounds' },
  rep: { search: 'Search reports (name, description)', none: 'No reports found.' },
  online: {
    live: 'Live', introLive: 'Online = the program open in the last {{minutes}} minutes. Updates itself every 10 seconds (last at {{at}}).',
    headerHint: 'Who is online now', you: 'you', minutesAgo: '{{count}} min ago', allSessions: 'All sessions →',
  },
  pay: { mailOnlyApproved: 'Payslips are sent from an approved or paid payment order' },
}

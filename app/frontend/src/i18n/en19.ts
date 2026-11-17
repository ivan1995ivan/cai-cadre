// CAI CADRE 1.2: manual corrections in the payroll and in payments (tax withheld on payment), payslips as PDF and by
// e-mail, payroll book.
export default {
  menu: { repSalaryBook: 'Payroll book' },
  pay: {
    correct: 'Correct the amount', editManual: 'Change the correction', correctFor: '{{name}} — correction: {{item}}', corrected: 'Corrected; taxes recalculated',
    correctHint: 'A manual amount replaces the calculated amount of the same type (salary, allowance, income tax, CNAM, CAS); a type without automatic calculation (one-off bonus, deduction) is added. Income tax and CNAM are recalculated from the corrected amounts unless you correct them too.',
    restore: 'Back to the calculated amount', restoreConfirm: 'Delete the correction and go back to the calculated amount?',
    slipsPdf: 'Payslips as PDF', mailSlips: 'E-mail the payslips', mailOnlyApproved: 'Payslips are sent from an approved payroll',
    mailTitle: 'Payslips by e-mail',
    mailHint: 'Every employee receives a ZIP archive with their payslip as PDF. The archive password: the last 5 digits of the personal code (IDNP). Employees without an e-mail or IDNP cannot be selected.',
    mailNoSmtp: 'E-mail is not configured: Administration → Settings → Mail (e-mail) for notifications and payslips (SMTP server).',
    mailSend: 'Send ({{count}})', mailSent: 'sent: {{count}}', mailStatus: 'Status',
    mailStatuses: { sent: 'Sent', skipped: 'Not sent', error: 'Error' },
  },
  pp: {
    toPay: 'To pay', manualHint: 'Corrected manually',
    advanceLegend: 'Tax is withheld on payment: from the advance — CNAM 9 % and income tax 12 % of the rest; the monthly exemption is applied when the salary is paid. Correct the gross (taxes follow), the net (gross is found) or the taxes directly.',
    salaryLegend: 'Amounts come from the month’s approved payrolls: income, exemption, CNAM and income tax minus what was already withheld from the advance. They can be corrected in draft; IPC21 (table 1) and the annual card follow the payment dates.',
  },
}

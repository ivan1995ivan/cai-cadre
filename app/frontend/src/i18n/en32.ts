// S5b: time without production (downtime, technical unemployment, piece-rate guarantee), hazardous allowance, aggregate
// working time accounting, meal vouchers.
export default {
  menu: { mealVouchers: 'Meal vouchers' },
  desk: { tab: { mealVouchers: 'Vouchers {{number}}' } },
  pay: {
    type: {
      autos: {
        idle: 'Downtime (St days × hourly salary × % by cause)', tech_unemployment: 'Technical unemployment (Șt days × hourly salary × %)',
        piece_guarantee: 'Piece rate: guarantee when the norm is not met (LC art. 161)',
        harmful: 'Hazardous conditions allowance (from department / post)',
        meal_voucher: 'Meal vouchers: part above the tax-free value', meal_voucher_offset: 'Meal vouchers given in kind (deduction)',
      },
    },
  },
  lv: { kinds: { idle: 'Downtime', tech_unemployment: 'Technical unemployment' } },
  rep: { absence: { idle: 'Downtime', tech_unemployment: 'Technical unemployment' } },
  ht: { set: { kinds: { idle: 'Downtime', tech_unemployment: 'Technical unemployment' } } },
  org: {
    harmfulPct: 'Hazardous allowance, %',
    harmfulPctHint: 'Hazardous conditions allowance from the collective agreement (LC art. 139): % of the hourly salary × hours worked here. Between department and post the higher percent applies; a personal NOCIV row replaces it. Paid only when “Hazardous conditions” is ticked.',
  },
  wt: {
    sch: {
      accountingMonths: 'Reference period, months',
      accountingHint: 'Aggregate working time accounting (LC art. 99): 1 — monthly; 2–12 — hours are compared with the norm of the whole period and overtime is paid in its last month. In the middle months the salary is paid for the month norm without absence days.',
      accountingValue: '{{n}} months', accountingMonthly: 'monthly',
      accountingStart: 'First period starts with month', accountingStartHint: 'Empty — January. E.g. a quarter: 3 months from January (January–March, April–June…).',
    },
  },
  ord: {
    p: {
      idleCause: 'Cause of the downtime', idleCauseHint: 'LC art. 80¹: the employer’s fault — in full; nobody’s fault — at least 2/3 of the base salary, not below the hourly minimum wage; the employee’s fault — unpaid.',
      idleCauses: { employer: 'The employer’s fault', nobody: 'Neither the employer’s nor the employee’s fault', worker: 'The employee’s fault' },
      idlePct: 'Pay, % of the base salary', idlePctHint: 'Empty — the legal percent by cause (Pay constants). A higher percent — from the collective agreement.',
      techPctHint: 'Empty — 50 % (LC art. 80, at least 50 % of the base salary). A higher percent — from the collective agreement.',
      idleHint: 'On signing, the period days with a planned shift show in the timesheet as St (downtime) / Șt (technical unemployment) with the planned hours; rest days and holidays stay as they are. Payroll pays their hours by cause and percent.',
    },
    addSubdivision: 'All employees of a department…', addSubdivisionBtn: 'Add the department',
    addSubdivisionHint: 'One point for each employee active on the order date, with the parameters of the first point.',
    addedFromSubdivision: '{{count}} employees were added.',
    copyParams: 'To all points', copyParamsConfirm: 'The same parameters (period, cause, percent) for all points of the order? Each one keeps their employment.',
    paramsCopied: 'Parameters were set on {{count}} points.',
  },
  prod: {
    rep: {
      shortfall: 'Norm not met (LC art. 161)',
      shortfallHint: 'The employer’s fault — at least the average pay for the hours worked; nobody’s fault — at least 2/3 of the grade rate. The difference up to the piece-rate earnings is paid (GARANT type); hours worked are needed on every work.',
      shortfalls: { none: 'Norm met / the worker’s fault', employer: 'The employer’s fault', nobody: 'Neither the employer’s nor the worker’s fault' },
    },
  },
  mv: {
    title: 'Meal voucher list', new: 'New list', create: 'Create and fill from the timesheet',
    hint: 'Meal vouchers for the month worked (Law 166/2017, GD 227/2018): a day worked — one voucher; shift work — day hours ÷ 8 + night-shift hours ÷ 7. Approved — the part above the tax-free value goes into the payroll of the month of its date.',
    date: 'Transfer date', dateHint: 'The taxable part goes into the payroll of this date’s month.',
    period: 'Month worked', periodHint: 'Vouchers are counted from this month’s timesheet (usually the previous one).',
    subdivision: 'Department', subdivisionHint: 'Empty — the whole company.', allCompany: 'Whole company',
    status: { draft: 'Draft', approved: 'Approved' },
    people: 'Employees', count: 'Vouchers', amount: 'Amount, lei', taxable: 'Taxable part', employee: 'Employee',
    days: 'Days worked', shiftHours: 'In shifts (day / night)', shiftHoursValue: '{{day}} h / {{night}} h', how: 'How it was counted',
    manual: 'manual', resetCount: 'Back to the number counted from the timesheet', total: 'Total',
    value: 'Voucher face value, lei', valueHint: 'From the manager’s order; tax-free — {{cap}} lei, above — taxable benefit (TC art. 19 let. a¹)).',
    rulesHint: 'The number is counted from the timesheet of the month worked (only days with hours). Shift work — a shift work schedule or the department roster; a shift is a night shift when at least half its hours are at night. The result is rounded (GD 227/2018 p. 12). Each person gets vouchers once, on the main employment; service contracts — none.',
    fill: 'Fill from the timesheet', filled: 'The list was filled from the timesheet.',
    approve: 'Approve', approveConfirm: 'Approve the list? The taxable part goes into the payroll of the month of its date.', approved: 'The list is approved.',
    unapprove: 'Cancel approval', unapproveConfirm: 'Cancel the approval? The taxable part leaves payroll (recalculate the month).', unapproved: 'The approval is cancelled.',
    approvedHint: 'The list is approved: the part above the tax-free value is in the payroll of the month of its date (TICHET), with its deduction (TICHETN) — the vouchers are already on the card.',
    problems: 'To fix before approval',
  },
}

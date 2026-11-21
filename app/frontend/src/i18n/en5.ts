// CAI CADRE — Stage 4 (part 2): working time.
export default {
  menu: { rosters: 'Shift schedule' },
  print: { docTypes: { roster: 'Shift schedule' } },
  wt: {
    off: 'off', rosters: 'Department shift schedule',
    weekdays: { mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun' },
    cycleHint: 'Shifts in a row, e.g. Z12, N12, off, off',
    tabs: { schedules: 'Work schedules', shifts: 'Shifts', calendar: 'Production calendar' },
    shift: {
      name: 'Name', hours: 'Hours', night: 'Of which at night', start: 'Starts at', color: 'Colour',
      hint: 'The shift code goes into schedules and timesheets: “8” (8-hour day), Z12 / N12 (12-hour day and night shifts). Night hours: 22:00–06:00 (LC art. 103).',
    },
    sch: {
      name: 'Name', kind: 'Type', kinds: { week: 'Weekly (5 / 6 days)', cycle: 'Shift cycle' }, weeklyHours: 'Hours per week',
      week: 'Shifts by weekday', cycle: 'Cycle shifts', cycleExtra: 'For shift cycles: repeats from “cycle starts on” (or from the assignment date).',
      cycleStart: 'Cycle starts on', holidaysOff: 'Holidays off', jobs: 'Assigned',
      hint: 'The schedule is assigned to each employment (employee file → Employments). Without one: 5 days a week with the position’s hours (40 / 35 / 30 h) × rate. A weekly schedule scales with the rate (0.5 rate → 4 hours a day); a shift cycle does not.',
    },
    cal: {
      working: 'Working day', hoursLess: 'Fewer hours (shortened day)', note: 'Grounds (government decision)', month: 'Month',
      calendarDays: 'Calendar days', workingDays: 'Working days', holidays: 'Holidays', overrides: 'Transferred, declared off or shortened days',
      hint: 'Monthly hour norms for the 40-, 35- and 30-hour week. Holidays come from the Labour Code (calculated automatically each year, with Easter); days transferred by the Government are added below.',
    },
    set: {
      minRest: 'Minimum rest between shifts (hours)', minRestHint: 'The shift schedule warns when fewer hours separate the end of a shift from the start of the next. For shifts from the classifier at least twice the previous shift is required anyway (LC art. 101); two shifts in a row always warn.',
      maxNights: 'Night shifts per month (maximum)', maxNightsHint: 'Warning when an employee has more shifts with night hours in a month. 0 — no limit.',
    },
    doc: {
      new: 'New for the chosen month', newAll: 'Create for all departments', createdAll: 'Created: {{count}}.', export: 'Export for 1C Payroll (Excel)',
      emptyHint: 'There are no documents for the chosen month. “New” — for one department; “Create for all departments” — one per department.',
      lines: 'Employees (employments)', newHint: 'The department’s employments are added automatically with shifts from their work schedules.',
      filled: 'Filled.', addMissing: 'Add missing employments', submit: 'Send to HR',
      submitConfirm: 'After sending, only HR can change the document. Send?', approve: 'Approve',
      reopen: 'Reopen', reopenConfirm: 'The document goes back to draft. Continue?',
    },
    ro: {
      heading: 'Roster {{month}} {{year}} — {{subdivision}}', fill: 'Rebuild from work schedules',
      fillConfirm: 'Shifts set by hand are replaced with those from the work schedules. Continue?',
      hours: 'Hours', norm: 'Norm', night: 'Night', nights: 'Nights',
      warnRest: '{{name}}: day {{day}} — only {{rest}} hours of rest between shifts (at least {{need}} required).',
      warnConsecutive: '{{name}}: day {{day}} — two shifts in a row without rest (LC art. 101).', warnAbsence: '{{name}}: day {{day}} — shift on an absence day ({{code}}).',
      warnNorm: '{{name}}: {{hours}} hours planned, monthly norm {{norm}}.', warnNights: '{{name}}: {{nights}} night shifts, maximum {{max}}.',
      legend: 'Click a cell to choose the shift or “off”. Absences from the file (leave, sick leave, travel) show their code and are not scheduled. Hours over the norm, two shifts in a row and short rest appear above under “To check”. Employees must be told the shift schedule in advance (LC art. 101).',
    },
    ts: {
      heading: 'Timesheet {{month}} {{year}} — {{subdivision}}', refill: 'Recalculate', reset: 'Recalculate all',
      resetConfirm: 'Manually entered cells are lost too. Continue?', close: 'Close the timesheet',
      closeConfirm: 'A closed timesheet no longer changes and goes to payroll. Close?', days: 'Days', holiday: 'Hol.', absences: 'Absences',
      cellEmpty: '— (empty)', cellTitle: '{{name}} — {{day}}', cellCode: 'Shift or absence code', cellHours: 'Hours worked', cellNight: 'Of which at night',
      cellHint: 'A shift sets its hours; hours typed here take priority. A notation (A — absence, R — rest day, Sn — public holiday, Șt — technical unemployment, St — idle time, Dt — secondment...) — without hours. Manually entered cells survive recalculation (underlined).',
      legend: 'Cell: hours worked (night hours below) or the notation of the timesheet model in Collective Convention no. 17/2020 (R — rest day, Sn — public holiday, C — paid leave, Cm — sick leave...). Filled from the shift schedule (or the work schedule), leave, sick leave, travel and suspensions. Click a cell to correct it by hand.',
    },
    job: {
      schedule: 'Work schedule', from: 'from {{date}}', offset: 'offset {{days}} days', none: 'not set (5 days with the position’s hours)', change: 'Change',
      offsetLabel: 'Cycle offset (days)', offsetHint: 'For teams: the second team starts the cycle one day later, etc.',
      hint: 'The previous schedule stays in the history until the new date.',
    },
    codes: {
      R: 'Rest days', Sn: 'Public holidays', Ls: 'Days off with pay', C: 'Paid leave',
      Cn: 'Unpaid leave', Cs: 'Study leave', Cm: 'Sick leave', Cc: 'Maternity, childcare or paternity leave',
      D: 'Business trip', Sp: 'Contract suspended', 'Șt': 'Technical unemployment', St: 'Idle time', Dt: 'Secondment', A: 'Absence', F: 'Vocational training',
    },
  },
}

// CAI CADRE — occupational health and safety (medical exams under GD 1025/2016, safety briefings under Law 186/2008) and
// military records (optional module).
export default {
  staff: { tabs: { health: 'Health and safety' } },
  constants: { military_enabled: 'Military records module',
    military_enabledHint: 'Optional: keeping military records of reservists is no longer mandatory for companies (Law 112/2023). Off: the register, the employee file tab, the reports and the military classifiers are hidden.' },
  al: { kinds: { medical_exam_due: 'Periodic medical exam', briefing_due: 'Safety briefing' } },
  hl: {
    tabs: { due: 'Deadlines', exams: 'Medical exams', briefings: 'Safety briefings', rules: 'Exam periodicity' },
    allWhat: 'Exam or briefing', horizon: 'Days ahead', printList: 'List for occupational medicine', settings: 'Frequency',
    examOrder: 'Order sending to the exam ({{count}})', whatCol: 'What', last: 'Last', due: 'Due',
    dueHint: 'Overdue: {{overdue}} · missing: {{missing}} · soon: {{due}}. The next date is filled from the frequency when left empty.',
    what: { exam: 'Medical exam', briefing: 'Safety briefing' },
    status: { overdue: 'Overdue', missing: 'Missing', due: 'Due' },
    examMonths: 'Periodic medical exam — by default every (months)',
    examMonthsHint: 'For positions and units without a rule on the “Exam periodicity” tab.',
    briefingMonths: 'Periodic safety briefing — every (months)',
    horizonDays: 'Show deadlines (days) ahead',
    nextHint: 'Empty = computed from the frequency.',
    rulesHint: 'The periodic medical exam frequency by the risk factors of the workplace (risk assessment, GD 1025/2016). The most precise '
      + 'rule wins: position and unit, then position, then unit (with its sub-units); no rule — the default frequency. 0 months — the '
      + 'position needs no periodic exam (not shown as “missing”). A change applies to exams recorded from now on.',
    rule: { occupation: 'Position', subdivision: 'Unit', months: 'Frequency (months)', monthsHint: '0 = no periodic exam',
      none: 'no periodic exam', note: 'Risk factors / basis' },
    examKinds: { preliminary: 'On hiring', periodic: 'Periodic', extraordinary: 'Extraordinary', return: 'On return to work' },
    conclusions: { fit: 'Fit', restricted: 'Fit with restrictions', temporary: 'Temporarily unfit', unfit: 'Unfit' },
    briefingKinds: { introductory: 'Introductory', initial: 'Initial at workplace', periodic: 'Periodic', unplanned: 'Unplanned', targeted: 'Targeted' },
    f: {
      kind: 'Type', kind_label: 'Type', date: 'Date', next_date: 'Next date', institution: 'Medical institution', conclusion: 'Conclusion',
      restrictions: 'Restrictions', document: 'Document', note: 'Notes', instructor: 'Instructor', topic: 'Topic',
    },
  },
  mil: {
    tabs: { military_register: 'Register', military_missing: 'No record', military_changes: 'Monthly changes', military_recruits: 'Recruits' },
  },
}

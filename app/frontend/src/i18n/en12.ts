// CAI CADRE — Stage 6, part 2: occupational health and military records.
export default {
  staff: { tabs: { health: 'Health' } },
  al: { kinds: { medical_exam_due: 'Periodic medical exam', briefing_due: 'Safety briefing', vaccination_due: 'Vaccination (next dose)' } },
  hl: {
    tabs: { due: 'Deadlines', exams: 'Medical exams', vaccinations: 'Vaccinations', briefings: 'Safety briefings' },
    allWhat: 'Exam, briefing, vaccine', horizon: 'Days ahead', printList: 'List for occupational medicine', settings: 'Frequency',
    examOrder: 'Order sending to the exam ({{count}})', whatCol: 'What', last: 'Last', due: 'Due',
    dueHint: 'Overdue: {{overdue}} · missing: {{missing}} · soon: {{due}}. The next date is filled from the frequency when left empty.',
    what: { exam: 'Medical exam', briefing: 'Safety briefing', vaccine: 'Vaccination' },
    status: { overdue: 'Overdue', missing: 'Missing', due: 'Due' },
    examMonths: 'Periodic medical exam — every (months)', briefingMonths: 'Periodic safety briefing — every (months)',
    horizonDays: 'Show deadlines (days) ahead',
    vaccineHint: 'Revaccination and mandatory vaccines for medical staff are set in Administration → Settings → Vaccines (extra: months, required).',
    nextHint: 'Empty = computed from the frequency.',
    examKinds: { preliminary: 'On hiring', periodic: 'Periodic', extraordinary: 'Extraordinary', return: 'On return to work' },
    conclusions: { fit: 'Fit', restricted: 'Fit with restrictions', temporary: 'Temporarily unfit', unfit: 'Unfit' },
    briefingKinds: { introductory: 'Introductory', initial: 'Initial at workplace', periodic: 'Periodic', unplanned: 'Unplanned', targeted: 'Targeted' },
    f: {
      kind: 'Type', kind_label: 'Type', date: 'Date', next_date: 'Next date', institution: 'Medical institution', conclusion: 'Conclusion',
      restrictions: 'Restrictions', document: 'Document', note: 'Notes', vaccine: 'Vaccine', vaccine_name: 'Vaccine',
      dose: 'Dose', series: 'Lot', refused: 'Written refusal', instructor: 'Instructor', topic: 'Topic',
    },
  },
  mil: {
    tabs: { military_register: 'Register', military_missing: 'No record', military_changes: 'Monthly changes', military_recruits: 'Recruits' },
  },
}

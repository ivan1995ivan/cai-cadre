// CAI CADRE — Etapa 6, partea 2: sănătatea în muncă și evidența militară.
export default {
  staff: { tabs: { health: 'Sănătate' } },
  al: { kinds: { medical_exam_due: 'Examenul medical periodic', briefing_due: 'Instructajul SSM', vaccination_due: 'Vaccinarea (doza următoare)' } },
  hl: {
    tabs: { due: 'Termenele', exams: 'Examenele medicale', vaccinations: 'Vaccinările', briefings: 'Instructajul SSM' },
    allWhat: 'Examen, instructaj, vaccin', horizon: 'Zile înainte', printList: 'Lista pentru medicina muncii', settings: 'Periodicitatea',
    examOrder: 'Ordinul de trimitere la examen ({{count}})', whatCol: 'Ce', last: 'Ultima dată', due: 'Termenul',
    dueHint: 'Depășite: {{overdue}} · fără înregistrare: {{missing}} · în curând: {{due}}. Termenul următor se completează singur din periodicitate, dacă nu-l scrieți.',
    what: { exam: 'Examenul medical', briefing: 'Instructajul SSM', vaccine: 'Vaccinarea' },
    status: { overdue: 'Depășit', missing: 'Lipsește', due: 'Urmează' },
    examMonths: 'Examenul medical periodic — o dată la (luni)', briefingMonths: 'Instructajul periodic SSM — o dată la (luni)',
    horizonDays: 'Arată termenele cu câte zile înainte',
    vaccineHint: 'Revaccinarea și vaccinurile obligatorii pentru personalul medical se setează în Administrare → Setări → Vaccinuri (extra: months, required).',
    nextHint: 'Gol = se calculează din periodicitate.',
    examKinds: { preliminary: 'La angajare', periodic: 'Periodic', extraordinary: 'Suplimentar', return: 'La reluarea activității' },
    conclusions: { fit: 'Apt', restricted: 'Apt condiționat', temporary: 'Inapt temporar', unfit: 'Inapt' },
    briefingKinds: { introductory: 'Introductiv general', initial: 'Primar la locul de muncă', periodic: 'Periodic', unplanned: 'Neplanificat', targeted: 'Special' },
    f: {
      kind: 'Tipul', kind_label: 'Tipul', date: 'Data', next_date: 'Următorul termen', institution: 'Instituția medicală', conclusion: 'Concluzia',
      restrictions: 'Restricții / recomandări', document: 'Fișa / certificatul', note: 'Observații', vaccine: 'Vaccinul', vaccine_name: 'Vaccinul',
      dose: 'Doza', series: 'Seria / lotul', refused: 'Refuz în scris', instructor: 'A instruit', topic: 'Tematica',
    },
  },
  mil: {
    tabs: { military_register: 'Registrul', military_missing: 'Fără fișă', military_changes: 'Modificările lunii', military_recruits: 'Recruții' },
  },
}

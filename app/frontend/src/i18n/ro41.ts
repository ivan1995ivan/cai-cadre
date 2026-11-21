// CAI CADRE — sănătatea și securitatea în muncă (examenele medicale HG 1025/2016, instructajul SSM Legea 186/2008) și evidența
// militară (modul opțional).
export default {
  staff: { tabs: { health: 'Sănătate și SSM' } },
  constants: { military_enabled: 'Modulul Evidența militară',
    military_enabledHint: 'Opțional: evidența militară a rezerviștilor nu mai e obligatorie pentru agenții economici (Legea 112/2023). Oprit: registrul, fila din dosar, rapoartele și clasificatoarele militare nu apar.' },
  al: { kinds: { medical_exam_due: 'Examenul medical periodic', briefing_due: 'Instructajul SSM' } },
  hl: {
    tabs: { due: 'Termenele', exams: 'Examenele medicale', briefings: 'Instructajul SSM', rules: 'Periodicitatea examenului' },
    allWhat: 'Examen sau instructaj', horizon: 'Zile înainte', printList: 'Lista pentru medicina muncii', settings: 'Periodicitatea',
    examOrder: 'Ordinul de trimitere la examen ({{count}})', whatCol: 'Ce', last: 'Ultima dată', due: 'Termenul',
    dueHint: 'Depășite: {{overdue}} · fără înregistrare: {{missing}} · în curând: {{due}}. Termenul următor se completează singur din periodicitate, dacă nu-l scrieți.',
    what: { exam: 'Examenul medical', briefing: 'Instructajul SSM' },
    status: { overdue: 'Depășit', missing: 'Lipsește', due: 'Urmează' },
    examMonths: 'Examenul medical periodic — implicit o dată la (luni)',
    examMonthsHint: 'Pentru funcțiile și subdiviziunile fără regulă în fila „Periodicitatea examenului”.',
    briefingMonths: 'Instructajul periodic SSM — o dată la (luni)',
    horizonDays: 'Arată termenele cu câte zile înainte',
    nextHint: 'Gol = se calculează din periodicitate.',
    rulesHint: 'Periodicitatea examenului medical periodic după factorii de risc ai locului de muncă (evaluarea riscurilor, HG 1025/2016). '
      + 'Cea mai precisă regulă câștigă: funcția și subdiviziunea, apoi funcția, apoi subdiviziunea (cu cele subordonate); fără regulă — '
      + 'periodicitatea implicită. 0 luni — funcția nu cere examen periodic (nu apare ca „lipsă”). Schimbarea se aplică examenelor înregistrate de acum.',
    rule: { occupation: 'Funcția', subdivision: 'Subdiviziunea', months: 'Periodicitatea (luni)', monthsHint: '0 = fără examen periodic',
      none: 'fără examen periodic', note: 'Factorii de risc / temeiul' },
    examKinds: { preliminary: 'La angajare', periodic: 'Periodic', extraordinary: 'Suplimentar', return: 'La reluarea activității' },
    conclusions: { fit: 'Apt', restricted: 'Apt condiționat', temporary: 'Inapt temporar', unfit: 'Inapt' },
    briefingKinds: { introductory: 'Introductiv general', initial: 'Primar la locul de muncă', periodic: 'Periodic', unplanned: 'Neplanificat', targeted: 'Special' },
    f: {
      kind: 'Tipul', kind_label: 'Tipul', date: 'Data', next_date: 'Următorul termen', institution: 'Instituția medicală', conclusion: 'Concluzia',
      restrictions: 'Restricții / recomandări', document: 'Fișa / certificatul', note: 'Observații', instructor: 'A instruit', topic: 'Tematica',
    },
  },
  mil: {
    tabs: { military_register: 'Registrul', military_missing: 'Fără fișă', military_changes: 'Modificările lunii', military_recruits: 'Recruții' },
  },
}

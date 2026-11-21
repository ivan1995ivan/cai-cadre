// CAI CADRE — Etapa 4 (partea 2): timpul de muncă.
export default {
  menu: { rosters: 'Graficul de ture' },
  print: { docTypes: { roster: 'Graficul de ture' } },
  wt: {
    off: 'liber', rosters: 'Graficul de ture al subdiviziunii',
    weekdays: { mon: 'Luni', tue: 'Marți', wed: 'Miercuri', thu: 'Joi', fri: 'Vineri', sat: 'Sâmbătă', sun: 'Duminică' },
    cycleHint: 'Turele la rând, de ex. Z12, N12, liber, liber',
    tabs: { schedules: 'Grafice de lucru', shifts: 'Ture', calendar: 'Calendarul de producție' },
    shift: {
      name: 'Denumirea', hours: 'Ore', night: 'Din ele noaptea', start: 'Începe la', color: 'Culoarea',
      hint: 'Codul turei se pune în grafice și în pontaj: „8” (zi de 8 ore), Z12 / N12 (ture de 12 ore, de zi și de noapte). Orele de noapte: între 22:00 și 06:00 (CM art. 103).',
    },
    sch: {
      name: 'Denumirea', kind: 'Tipul', kinds: { week: 'Săptămânal (5 / 6 zile)', cycle: 'Pe ture (ciclic)' }, weeklyHours: 'Ore pe săptămână',
      week: 'Turele pe zilele săptămânii', cycle: 'Turele ciclului', cycleExtra: 'Pentru graficele pe ture: se repetă de la „ciclul începe la” (sau de la data punerii pe raport).',
      cycleStart: 'Ciclul începe la', holidaysOff: 'Sărbătorile libere', jobs: 'Raporturi',
      hint: 'Graficul se pune pe fiecare raport de muncă (fișa angajatului → Raporturi de muncă). Fără grafic: 5 zile pe săptămână cu orele funcției (40 / 35 / 30 h) înmulțite cu norma. Graficul săptămânal se micșorează după normă (0,5 normă → 4 ore pe zi); cel pe ture nu.',
    },
    cal: {
      working: 'Zi lucrătoare', hoursLess: 'Ore mai puține (zi scurtată)', note: 'Temeiul (hotărârea Guvernului)', month: 'Luna',
      calendarDays: 'Zile calendaristice', workingDays: 'Zile lucrătoare', holidays: 'Sărbători', overrides: 'Zile transferate, declarate libere sau scurtate',
      hint: 'Norma de ore pe lună pentru săptămâna de 40, 35 și 30 de ore. Sărbătorile vin din Codul muncii (se calculează singure pe fiecare an, cu Paștele); zilele transferate de Guvern se adaugă mai jos.',
    },
    set: {
      minRest: 'Odihna minimă între ture (ore)', minRestHint: 'Graficul de ture avertizează când între sfârșitul unei ture și începutul următoarei sunt mai puține ore. Pentru turele din clasificator se cere oricum cel puțin dublul turei anterioare (CM art. 101); două ture la rând — avertisment întotdeauna.',
      maxNights: 'Ture de noapte pe lună (maximum)', maxNightsHint: 'Avertisment când un angajat are mai multe ture cu ore de noapte într-o lună. 0 — fără limită.',
    },
    doc: {
      new: 'Nou pe luna aleasă', newAll: 'Fă pentru toate secțiile', createdAll: 'Create: {{count}}.', export: 'Export pentru 1C Salariu (Excel)',
      emptyHint: 'Pentru luna aleasă nu există documente. „Nou” — pentru o secție; „Fă pentru toate secțiile” — câte unul pe fiecare subdiviziune.',
      lines: 'Angajați (raporturi)', newHint: 'Raporturile de muncă ale secției se adaugă singure, cu turele din graficele lor de lucru.',
      filled: 'Completat.', addMissing: 'Adaugă raporturile lipsă', submit: 'Transmite la resurse umane',
      submitConfirm: 'După transmitere documentul îl schimbă doar resursele umane. Transmiteți?', approve: 'Aprobă',
      reopen: 'Redeschide', reopenConfirm: 'Documentul revine la ciornă. Continuați?',
    },
    ro: {
      heading: 'Graficul {{month}} {{year}} — {{subdivision}}', fill: 'Refă din graficele de lucru',
      fillConfirm: 'Turele puse de mână se înlocuiesc cu cele din graficele de lucru ale raporturilor. Continuați?',
      hours: 'Ore', norm: 'Norma', night: 'Noapte', nights: 'Nopți',
      warnRest: '{{name}}: ziua {{day}} — odihnă de doar {{rest}} ore între ture (trebuie cel puțin {{need}}).',
      warnConsecutive: '{{name}}: ziua {{day}} — două ture la rând, fără odihnă (CM art. 101).', warnAbsence: '{{name}}: ziua {{day}} — tură pusă într-o zi de absență ({{code}}).',
      warnNorm: '{{name}}: {{hours}} ore planificate, norma lunii {{norm}}.', warnNights: '{{name}}: {{nights}} ture de noapte, maximum {{max}}.',
      legend: 'Clic pe celulă — alegeți tura sau „liber”. Absențele din dosar (concedii, boală, deplasări) apar cu codul lor și nu se pun în grafic. Orele peste normă, două ture la rând și odihna prea scurtă apar sus, la „De verificat”. Graficul de ture se aduce la cunoștința angajaților din timp (CM art. 101).',
    },
    ts: {
      heading: 'Tabela de pontaj {{month}} {{year}} — {{subdivision}}', refill: 'Recalculează', reset: 'Recalculează tot',
      resetConfirm: 'Se pierd și celulele scrise de mână. Continuați?', close: 'Închide tabela',
      closeConfirm: 'Tabela închisă nu se mai schimbă și pleacă la salarizare. Închideți?', days: 'Zile', holiday: 'Sărb.', absences: 'Absențe',
      cellEmpty: '— (gol)', cellTitle: '{{name}} — {{day}}', cellCode: 'Tura sau codul absenței', cellHours: 'Ore lucrate', cellNight: 'Din ele noaptea',
      cellHint: 'Tura pune orele ei; orele scrise aici au prioritate. Notația (A — absențe, R — repaus, Sn — sărbătoare, Șt — șomaj tehnic, St — staționare, Dt — detașare...) — fără ore. Celulele scrise de mână rămân la recalculare (subliniate).',
      legend: 'Celula: orele lucrate (dedesubt — orele de noapte) sau notația, după modelul tabelului de pontaj din Convenția colectivă nr. 17/2020 (R — repaus, Sn — sărbătoare, C — concediu plătit, Cm — concediu medical...). Se completează din graficul de ture (sau din graficul de lucru al raportului), din concedii, foi de boală, deplasări și suspendări. Clic pe celulă — corectare de mână.',
    },
    job: {
      schedule: 'Graficul de lucru', from: 'din {{date}}', offset: 'decalaj {{days}} zile', none: 'nu e pus (5 zile cu orele funcției)', change: 'Schimbă',
      offsetLabel: 'Decalajul în ciclu (zile)', offsetHint: 'Pentru echipe: echipa a doua pornește ciclul cu o zi mai târziu etc.',
      hint: 'Graficul vechi rămâne în istoric până la data nouă.',
    },
    codes: {
      R: 'Zile de repaus (odihnă)', Sn: 'Zile de sărbătoare nelucrătoare', Ls: 'Zile libere cu menținerea salariului', C: 'Concediu plătit',
      Cn: 'Concediu neplătit', Cs: 'Concediu de studii', Cm: 'Concediu medical', Cc: 'Concediu de maternitate, pentru îngrijirea copilului, paternal',
      D: 'Deplasare', Sp: 'Suspendarea CIM', 'Șt': 'Șomaj tehnic', St: 'Staționare', Dt: 'Detașare', A: 'Absențe', F: 'Formare profesională',
    },
  },
}

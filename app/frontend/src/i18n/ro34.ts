// CAI CADRE — Etapa 4 (partea 2): timpul de muncă.
export default {
  menu: { rosters: 'Graficul lunar (gărzi)' },
  print: { docTypes: { roster: 'Graficul lunar de lucru (ture)' } },
  wt: {
    off: 'liber', rosters: 'Graficul lunar al secției (ture, gărzi)',
    weekdays: { mon: 'Luni', tue: 'Marți', wed: 'Miercuri', thu: 'Joi', fri: 'Vineri', sat: 'Sâmbătă', sun: 'Duminică' },
    cycleHint: 'Turele la rând, de ex. Z12, N12, liber, liber',
    tabs: { schedules: 'Grafice de lucru', shifts: 'Ture', calendar: 'Calendarul de producție' },
    shift: {
      name: 'Denumirea', hours: 'Ore', night: 'Din ele noaptea', start: 'Începe la', duty: 'Gardă', color: 'Culoarea',
      hint: 'Codul turei se pune în grafice și în pontaj: „8” (zi de 8 ore), Z12 / N12 (ture de 12 ore), G24 (gardă). Orele de noapte: între 22:00 și 06:00.',
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
      minRest: 'Odihna minimă între ture (ore)', minRestHint: 'Graficul lunar avertizează când între sfârșitul unei ture și începutul următoarei sunt mai puține ore. 0 — fără verificare.',
      maxDuties: 'Gărzi pe lună (maximum)', maxDutiesHint: 'Avertisment când un angajat are mai multe gărzi într-o lună. 0 — fără limită.',
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
      hours: 'Ore', norm: 'Norma', night: 'Noapte', duties: 'Gărzi',
      warnRest: '{{name}}: ziua {{day}} — odihnă de doar {{rest}} ore între ture.', warnAbsence: '{{name}}: ziua {{day}} — tură pusă într-o zi de absență ({{code}}).',
      warnNorm: '{{name}}: {{hours}} ore planificate, norma lunii {{norm}}.', warnDuties: '{{name}}: {{duties}} gărzi, maximum {{max}}.',
      legend: 'Clic pe celulă — alegeți tura sau „liber”. Absențele din dosar (concedii, boală, deplasări) apar cu codul lor și nu se pun în grafic. Orele peste normă și odihna prea scurtă apar sus, la „De verificat”.',
    },
    ts: {
      heading: 'Tabela de pontaj {{month}} {{year}} — {{subdivision}}', refill: 'Recalculează', reset: 'Recalculează tot',
      resetConfirm: 'Se pierd și celulele scrise de mână. Continuați?', close: 'Închide tabela',
      closeConfirm: 'Tabela închisă nu se mai schimbă și pleacă la salarizare. Închideți?', days: 'Zile', holiday: 'Sărb.', absences: 'Absențe',
      cellEmpty: '— (gol)', cellTitle: '{{name}} — {{day}}', cellCode: 'Tura sau codul absenței', cellHours: 'Ore lucrate', cellNight: 'Din ele noaptea',
      cellHint: 'Tura pune orele ei; orele scrise aici au prioritate. Codul de absență (A — nemotivat, IN — învoire, CO, CM...) — fără ore. Celulele scrise de mână rămân la recalculare (subliniate).',
      legend: 'Celula: orele lucrate (dedesubt — orele de noapte) sau codul absenței. Se completează din graficul lunar al secției (sau din graficul de lucru al raportului), din concedii, foi de boală, deplasări și suspendări. Clic pe celulă — corectare de mână.',
    },
    job: {
      schedule: 'Graficul de lucru', from: 'din {{date}}', offset: 'decalaj {{days}} zile', none: 'nu e pus (5 zile cu orele funcției)', change: 'Schimbă',
      offsetLabel: 'Decalajul în ciclu (zile)', offsetHint: 'Pentru echipe: echipa a doua pornește ciclul cu o zi mai târziu etc.',
      hint: 'Graficul vechi rămâne în istoric până la data nouă.',
    },
    codes: {
      CO: 'Concediu de odihnă anual', CA: 'Concediu suplimentar', CFP: 'Concediu fără plată', CMT: 'Concediu de maternitate', CP: 'Concediu paternal',
      CIC: 'Îngrijirea copilului (parțial plătit)', CICN: 'Îngrijirea copilului (neplătit)', CS: 'Concediu de studii', ZL: 'Zile libere plătite',
      D: 'Deplasare', F: 'Perfecționare / EMC', CM: 'Concediu medical', S: 'CIM suspendat', A: 'Absență nemotivată', IN: 'Învoire',
    },
  },
}

// S2: cifrele și regulile salariului 2026 — cererea de scutire cu persoanele întreținute, salariul minim, baza minimă CAS.
export default {
  pay: {
    ex: {
      hint: 'Codul fiscal, art. 33–35: scutirea personală (P) sau majorată (M), pentru soț / soție (Sm — doar soțul din categoriile art. 33 alin. (2), fără scutirea lui; „S” e abrogată din 2021), pentru persoanele întreținute (N; H — cu dizabilitate din copilărie, severă sau accentuată). Cererea nu se reînnoiește anual: se aplică din luna următoare depunerii, până la o cerere nouă (la orice schimbare — în 10 zile). Lunar: suma anuală / 12, cel mult venitul lunii.',
      dateFrom: 'Se aplică din',
    },
    ex2: {
      number: 'Nr. de înregistrare', dateTo: 'Valabilă până la', dateFromHint: 'Gol — din luna următoare depunerii.',
      dateToHint: 'Gol — până la o cerere nouă (cererea nouă o închide singură pe cea veche).',
      majorCategory: 'Categoria scutirii majorate (M)', majorHint: 'Codul fiscal, art. 33 alin. (2): litera categoriei.', majorDocument: 'Documentul pentru M',
      category: 'art. 33 alin. (2) lit. {{c}})', spouseMajor: 'Scutirea pentru soț / soție (Sm)',
      spouseMajorHint: 'Doar dacă soțul / soția e din categoriile art. 33 alin. (2) și nu-și folosește propria scutire (CF art. 34 alin. (2)).',
      spouseName: 'Soțul / soția (numele, prenumele)', spouseCategory: 'Categoria soțului / soției', spouseDocument: 'Documentul soțului / soției',
      waiver: 'Renunțarea la P / M — data cererii', waiverHint: 'Venitul anual peste 360 000 lei: P / M nu se mai acordă din luna următoare cererii; lunile trecute nu se recalculează.',
      needsReview: 'De verificat', codeNow: 'Codul luna aceasta',
      fromFamily: 'Din „Familia”', birthDate: 'Data nașterii', rightFrom: 'Dreptul de la', rightTo: 'Dreptul până la',
      document: 'Documentul (certificatul de naștere...)', incomeOk: 'Venitul ≤ 12 400 lei / an',
      dependentsHint: 'Scutirea pentru o persoană se aplică din luna următoare apariției dreptului (CF art. 35 alin. (4)). Fratele / sora — doar cu dizabilitate.',
      rel: { child: 'Copil', parent: 'Părinte', sibling: 'Frate / soră', other: 'Altă persoană' },
      dis: { none: 'Fără dizabilitate (N)', childhood: 'Din copilărie (H)', severe: 'Severă (H)', accentuated: 'Accentuată (H)', medium: 'Medie (N)' },
    },
    type: { autos: { sick_accident: 'Accident de muncă: zilele angajatorului', min_wage: 'Completare până la salariul minim', cas_min: 'CAS pe diferența până la baza minimă' } },
    const: { check: 'de verificat' },
  },
  wt: { ts: { overtimeSplit: 'Suplimentare: {{first}} h (primele 2 ore / zi) + {{next}} h (următoarele); sărbători / repaus: {{inNorm}} h în normă + {{over}} h peste normă' } },
  al: { kinds: { min_wage: 'Salariul sub salariul minim', exemption_limit: 'Venitul aproape de plafonul scutirii (360 000 lei)' } },
}

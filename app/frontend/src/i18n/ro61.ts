// S5b: timpul fără producție (staționarea, șomajul tehnic, garanția acordului), sporul vătămător, evidența globală,
// tichetele de masă.
export default {
  menu: { mealVouchers: 'Tichete de masă' },
  desk: { tab: { mealVouchers: 'Tichetele {{number}}' } },
  pay: {
    type: {
      autos: {
        idle: 'Staționarea (zilele St × salariul pe oră × % după cauză)', tech_unemployment: 'Șomajul tehnic (zilele Șt × salariul pe oră × %)',
        piece_guarantee: 'Acord: garanția la neîndeplinirea normei (CM art. 161)',
        harmful: 'Sporul pentru condiții vătămătoare (din subdiviziune / funcție)',
        meal_voucher: 'Tichetele de masă: partea peste valoarea neimpozabilă', meal_voucher_offset: 'Tichetele de masă acordate în natură (reținere)',
      },
    },
  },
  lv: { kinds: { idle: 'Staționare', tech_unemployment: 'Șomaj tehnic' } },
  rep: { absence: { idle: 'Staționare', tech_unemployment: 'Șomaj tehnic' } },
  ht: { set: { kinds: { idle: 'Staționare', tech_unemployment: 'Șomaj tehnic' } } },
  org: {
    harmfulPct: 'Sporul vătămător, %',
    harmfulPctHint: 'Sporul pentru condiții vătămătoare din contractul colectiv (CM art. 139): % din salariul de bază pe oră × orele lucrate aici. Între subdiviziune și funcție se ia procentul mai mare; rândul personal NOCIV îl înlocuiește. Se plătește doar când „Condiții vătămătoare” e bifat.',
  },
  wt: {
    sch: {
      accountingMonths: 'Perioada de calcul, luni',
      accountingHint: 'Evidența globală a timpului de muncă (CM art. 99): 1 — evidența lunară; 2–12 — orele se compară cu norma întregii perioade, iar suplimentarele se plătesc în ultima ei lună. În lunile din mijloc salariul se plătește pentru norma lunii fără zilele de absență.',
      accountingValue: '{{n}} luni', accountingMonthly: 'lunară',
      accountingStart: 'Prima perioadă începe cu luna', accountingStartHint: 'Gol — ianuarie. De exemplu, trimestrul: 3 luni din ianuarie (ianuarie–martie, aprilie–iunie…).',
    },
  },
  ord: {
    p: {
      idleCause: 'Cauza staționării', idleCauseHint: 'CM art. 80¹: din vina angajatorului — integral; fără vina părților — cel puțin 2/3 din salariul de bază, dar nu sub salariul minim pe oră; din vina salariatului — nu se plătește.',
      idleCauses: { employer: 'Din vina angajatorului', nobody: 'Fără vina angajatorului și a salariatului', worker: 'Din vina salariatului' },
      idlePct: 'Plata, % din salariul de bază', idlePctHint: 'Gol — procentul legal după cauză (Constantele salarizării). Un procent mai mare — din contractul colectiv.',
      techPctHint: 'Gol — 50 % (CM art. 80, cel puțin 50 % din salariul de bază). Un procent mai mare — din contractul colectiv.',
      idleHint: 'La semnare zilele cu tură planificată din perioadă apar în pontaj ca St (staționare) / Șt (șomaj tehnic), cu orele planificate; zilele de repaus și sărbătorile rămân ale lor. Salariul plătește orele lor după cauză și procent.',
    },
    addSubdivision: 'Toți angajații subdiviziunii…', addSubdivisionBtn: 'Adaugă subdiviziunea',
    addSubdivisionHint: 'Câte un punct pentru fiecare angajat activ la data ordinului, cu parametrii primului punct.',
    addedFromSubdivision: 'Au fost adăugați {{count}} angajați.',
    copyParams: 'La toate punctele', copyParamsConfirm: 'Aceiași parametri (perioada, cauza, procentul) la toate punctele ordinului? Raportul de muncă al fiecăruia rămâne.',
    paramsCopied: 'Parametrii au fost puși la {{count}} puncte.',
  },
  prod: {
    rep: {
      shortfall: 'Neîndeplinirea normei (CM art. 161)',
      shortfallHint: 'Din vina angajatorului — cel puțin salariul mediu pe orele lucrate; fără vina părților — cel puțin 2/3 din tariful categoriei. Se plătește diferența până la câștigul în acord (tipul GARANT); cere orele lucrate la fiecare lucrare.',
      shortfalls: { none: 'Norma îndeplinită / din vina lucrătorului', employer: 'Din vina angajatorului', nobody: 'Fără vina angajatorului și a lucrătorului' },
    },
  },
  mv: {
    title: 'Borderoul tichetelor de masă', new: 'Borderou nou', create: 'Creează și completează din pontaj',
    hint: 'Tichetele de masă pentru luna lucrată (Legea 166/2017, HG 227/2018): o zi lucrată — un tichet; la munca în schimburi — orele de zi ÷ 8 + orele din schimburile de noapte ÷ 7. Aprobat — partea peste valoarea neimpozabilă intră în salariul lunii datei.',
    date: 'Data transferului', dateHint: 'Partea impozabilă intră în calculul salariului lunii acestei date.',
    period: 'Luna lucrată', periodHint: 'Tichetele se socotesc din pontajul acestei luni (de regulă — precedenta).',
    subdivision: 'Subdiviziunea', subdivisionHint: 'Gol — toată întreprinderea.', allCompany: 'Toată întreprinderea',
    status: { draft: 'Ciornă', approved: 'Aprobat' },
    people: 'Angajați', count: 'Tichete', amount: 'Suma, lei', taxable: 'Partea impozabilă', employee: 'Angajatul',
    days: 'Zile lucrate', shiftHours: 'În schimburi (zi / noapte)', shiftHoursValue: '{{day}} h / {{night}} h', how: 'Cum s-a socotit',
    manual: 'de mână', resetCount: 'Înapoi la numărul socotit din pontaj', total: 'Total',
    value: 'Valoarea nominală a tichetului, lei', valueHint: 'Din ordinul conducătorului; neimpozabil — {{cap}} lei, peste — facilitate impozabilă (CF art. 19 lit. a¹)).',
    rulesHint: 'Numărul se socotește din pontajul lunii lucrate (doar zilele cu ore). Munca în schimburi — graficul de lucru pe ture sau graficul de ture al subdiviziunii; un schimb e de noapte când are cel puțin jumătate din ore noaptea. Rezultatul se rotunjește (HG 227/2018 pct. 12). Fiecare persoană primește tichetele o singură dată, pe raportul de bază; prestările de servicii — nu.',
    fill: 'Completează din pontaj', filled: 'Borderoul este completat din pontaj.',
    approve: 'Aprobă', approveConfirm: 'Aprobați borderoul? Partea impozabilă intră în calculul salariului lunii datei.', approved: 'Borderoul este aprobat.',
    unapprove: 'Anulează aprobarea', unapproveConfirm: 'Anulați aprobarea? Partea impozabilă iese din salariu (recalculați luna).', unapproved: 'Aprobarea este anulată.',
    approvedHint: 'Borderoul este aprobat: partea peste valoarea neimpozabilă e în calculul salariului lunii datei (TICHET), cu reținerea ei (TICHETN) — tichetele sunt deja pe card.',
    problems: 'De corectat înainte de aprobare',
  },
}

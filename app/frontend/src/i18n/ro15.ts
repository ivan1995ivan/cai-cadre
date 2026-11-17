// Textele recunoașterii facturilor furnizorilor (fac2ra), ale planificării și ale salariilor managerilor.
const ro15 = {
  period: { from: 'De la', to: 'Până la', today: 'Azi', yesterday: 'Ieri', last7: 'Ultimele 7 zile', thisMonth: 'Luna aceasta',
    lastMonth: 'Luna trecută', thisYear: 'Anul acesta' },
  incoming: {
    title: 'Facturi primite', pullNow: 'Verifică acum', pulled_one: 'A venit o factură nouă.', pulled_few: 'Facturi noi venite: {{count}}.', pulled_other: 'Facturi noi venite: {{count}}.',
    hint: 'Facturile furnizorilor recunoscute pe factura.integratii.md vin singure aici: serverul citește cutia portalului la fiecare 30 de secunde. Pentru marfă — „Înregistrează ca intrare” (furnizorul după IDNO — dacă nu e în listă, se adaugă singur cu datele din factură; mărfurile după cod / denumire, marfa intră în stoc la înregistrare). Pentru chirie, transport, comunale, telefonie — „Servicii”: factura de servicii, fără stoc, cu articolul de cheltuială. Verificați cu hârtia și salvați; nimic nu se înregistrează singur.',
    off: 'Primirea automată nu e pornită: Administrare → Integrări → fac2ra → „Primirea automată a facturilor” (cheia API și numărul serverului de pe portal).',
    lastCheck: 'Ultima verificare: {{time}}', everyHalfMinute: 'Se verifică la fiecare 30 de secunde',
    states: { new: 'Noi', registered: 'Înregistrate', ignored: 'Ignorate', all: 'Toate' },
    search: 'Număr, furnizor, IDNO, fișier', received: 'Primită', supplier: 'Furnizorul', number: 'Nr. facturii', lines: 'Rânduri',
    total: 'Suma cu TVA', supplierUnknown: 'Furnizorul nu s-a putut adăuga singur (IDNO-ul nu are 13 cifre, pare greșit sau furnizorul e dezactivat): îl alegeți sau îl adăugați în factura de intrare.',
    needsReview: 'Portalul nu e sigur de rezultat: verificați cu hârtia înainte de salvare.',
    register: 'Înregistrează ca intrare', asServices: 'Servicii', asServicesHint: 'Factură de servicii (chirie, transport, comunale...): nu intră în stoc, fiecare rând primește articolul de cheltuială', ignore: 'Ignoră', restore: 'Readu', ignoreConfirm: 'Factura nu se va înregistra (se poate readuce din „Ignorate”). Continuați?',
  },
  fac2ra: {
    inboxTitle: 'Primirea automată a facturilor', inboxEnabled: 'Preia singur facturile',
    inboxHint: 'Serverul citește cutia de pe factura.integratii.md la fiecare 30 de secunde și pune facturile în „Facturi primite” (meniul Achiziții). Pe portal, programul acesta are nevoie de un server al lui, în modul „programul preia singur facturile”: nu folosiți același server și pentru o bază 1C, altfel își iau facturile una alteia.',
    inboxServer: 'Serverul de pe portal (numărul)', inboxServerHint: 'Id-ul serverului creat în contul factura.integratii.md. Gol = serverul implicit al cheii.',
    inboxServerDefault: 'implicit',
    title: 'fac2ra — recunoașterea facturilor primite',
    hint: 'Fotografiați factura furnizorului (sau încărcați PDF-ul) în factura de intrare: serviciul factura.integratii.md citește numărul, data, furnizorul și rândurile, iar sistemul caută furnizorul după IDNO și mărfurile după cod și denumire. Nimic nu se salvează singur — verificați cu hârtia și salvați.',
    enabled: 'Pornit', apiKey: 'Cheia API', apiKeyHint: 'Din cabinetul factura.integratii.md, secțiunea API. Se păstrează cifrată și nu ajunge în browser.',
    keySaved: 'Cheia e salvată ({{hint}}). Lăsați gol ca s-o păstrați.', clearKey: 'Șterge cheia', test: 'Probează cheia (fără cost)',
    recognize: 'Din poză / PDF', recognizeHint: 'Fotografiați factura furnizorului sau alegeți PDF-ul: datele se completează singure',
    working: 'fac2ra citește factura… (până la 90 de secunde)', done: 'Factura a fost citită: verificați datele cu hârtia',
    notMatched: 'Marfa negăsită', pick: 'Alegeți marfa', lineFromInvoice: 'Din factură', addMatched: 'Adaugă în document',
    unmatchedTitle: 'Rânduri fără marfă găsită', unmatchedHint: 'Alegeți marfa din nomenclator pentru fiecare rând; rândurile lăsate fără marfă nu intră în document.',
    supplierUnknown: 'Furnizorul din factură', replaceLines: 'Rândurile din factură se adaugă la cele existente.',
  },
}
export default ro15

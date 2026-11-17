// Textele pentru Etapa 10b: aplicația pe telefon (PWA), pozele, scanarea cu camera.
const ro9 = {
  mobile: {
    hello: 'Bună ziua, {{name}}!', home: 'Pagina de start', offline: 'Fără internet — vedeți ultimele date primite.',
    nothing: 'Pentru contul dvs. nu există ecrane pe telefon. Deschideți versiunea completă.',
    install: 'Instalează aplicația pe telefon', fullVersion: 'Versiunea completă', open: 'Deschide',
    phoneBanner: 'Lucrați de pe telefon? Există o versiune simplă pentru teren.', driverAccount: 'Contul în sistem (aplicația șoferului)',
    tiles: { driver: 'Rutele mele', team: 'Comenzile echipei', visit: 'Vizită la client', warehouse: 'Terminal depozit', calculator: 'Calculator',
      shop_floor: 'Sala: colectare', shop_cash: 'Casa magazinului', shop_release: 'Eliberare de la depozit' },
    tilesHint: {
      driver: 'Opririle, adresele, livrarea cu poză și semnătură', team: 'Montaj: materiale, adresă, rapoarte cu poze',
      visit: 'Client, locație, poze, ce s-a discutat', warehouse: 'Scanare QR, plasare, mutare, inventar',
      calculator: 'Acoperiș și gard', shop_floor: 'Scanați marfa, cantitatea, eticheta cu QR pentru casă',
      shop_cash: 'Schimbul, bonurile, încasarea', shop_release: 'Scanați bonul și eliberați marfa',
    },
    driver: {
      noRoutes: 'Nu aveți rute pentru azi.', stopsLeft: '{{open}} din {{total}} de livrat', goods: '{{count}} poziții',
      maxLength: 'cea mai lungă {{m}} m', markButton: 'Livrare', partial: 'Parțial',
      reasonRequired: 'Scrieți de ce nu s-a livrat', photosHint: 'Poze (marfa descărcată, actul semnat)',
      reasons: { notHome: 'Clientul nu e acasă', refused: 'Clientul a refuzat', wrongAddress: 'Adresa greșită', noAccess: 'Nu se poate ajunge' },
    },
    team: {
      noOrders: 'Echipa nu are comenzi în lucru.', due: 'termen {{date}}', materials: 'Materialele', history: 'Istoria',
      reports: { arrived: 'Am ajuns pe obiect', started: 'Am început lucrul', finished: 'Lucrul e gata', problem: 'Problemă', note: 'Notă / poze' },
      send: 'Trimite', sent: 'Trimis managerului', problemHint: 'Ce s-a întâmplat? (lipsește marfă, alte dimensiuni...)',
      noteHint: 'Comentariu (opțional)', managerNotified: 'Managerul comenzii primește notificarea, iar raportul intră în istoria comenzii.',
    },
    visit: {
      client: 'Clientul', existing: 'Din bază', newClient: 'Client nou', clientName: 'Numele clientului',
      dedupHint: 'Dacă telefonul există deja în bază, vizita se scrie la clientul găsit.', clientRequired: 'Alegeți clientul sau scrieți numele și telefonul',
      site: 'Obiectul', address: 'Adresa obiectului', noGps: 'Locația nu este disponibilă', located: 'Locația a fost luată',
      notes: 'Ce s-a discutat', notesHint: 'Sortimentul, dorințele clientului, termene de livrare...', result: 'Rezultatul (de ex. trimit oferta mâine)',
      measure: 'Măsurări', noMeasure: 'Fără', roofType: 'Tipul acoperișului', segments: 'Laturile gardului (m), separate prin virgulă',
      gates: 'Porți', wickets: 'Portițe',
      measureHint: 'Măsurările se salvează ca schiță în calculator: în birou se alege materialul și se face oferta.',
      saved: 'Vizita a fost salvată', photosSaved: '{{count}} poze', calcSaved: 'schița de calcul {{number}}',
      openCalc: 'Deschide calculul', another: 'Încă o vizită',
    },
  },
  photos: {
    title: 'Poze', add: 'Poză', none: 'Nu sunt poze', signature: 'Semnătura', signHere: 'Semnătura clientului (cu degetul)',
    clear: 'Șterge', deleteConfirm: 'Ștergeți poza?',
  },
  maintenance: {
    backups: 'Copii de rezervă', backupNow: 'Fă o copie acum', backupDone: 'Copia de rezervă a fost făcută',
    backupsHint: 'Copia cuprinde baza de date și fișierele încărcate (poze, logo-uri). Se face singură în fiecare zi și înainte de fiecare actualizare. Păstrați copiile și pe alt calculator sau pe un disc extern (butonul de descărcare).',
    daily: 'Copie zilnică', after: 'după ora', keep: 'păstrează ultimele', kind: 'Tipul', method: 'Baza', size: 'Mărimea',
    folder: 'Dosarul copiilor', deleteConfirm: 'Ștergeți această copie?',
    reasons: { manual: 'manuală', daily: 'zilnică', upgrade: 'înainte de migrații', update: 'înainte de actualizare' },
    methods: { sqlite: 'SQLite (copie exactă)', pg_dump: 'PostgreSQL (pg_dump)', json: 'Export universal' },
    updates: 'Actualizări', lastUpdate: 'Ultima actualizare', pending: 'Versiunea {{version}} este pregătită',
    install: 'Instalează și repornește', installConfirm: 'Sistemul se oprește câteva minute pentru actualizare (se face copie de rezervă). Continuați?',
    restarting: 'Se instalează actualizarea, serverul repornește... Pagina se reîncarcă singură.',
    upload: 'Încarcă pachetul de actualizare (.zip)', uploaded: 'Pachetul a fost verificat și pregătit',
    updatesHint: 'Pachetele vin de la producător și sunt semnate: un fișier modificat sau de altă proveniență nu se acceptă. Dacă actualizarea nu reușește, sistemul revine singur la versiunea anterioară.',
    feed: 'Adresa de actualizări (de la producător)', check: 'Verifică versiunea nouă', download: 'Descarcă versiunea {{version}}',
    docker: 'Sistemul rulează în Docker: se actualizează cu imaginea nouă (docker compose pull && docker compose up -d).',
    upToDate: 'Aveți ultima versiune', rollbackKept: 'Se păstrează pentru revenire: {{versions}}',
  },
  about: { title: 'Posibilitățile sistemului', version: 'Versiunea {{version}}', menu: 'Despre program', tagline: 'Vânzări, depozit, producție, livrări și montaj', producer: 'Producătorul', website: 'Site', phone: 'Telefon', licensee: 'Utilizatorul licenței', support: 'Întrebări, instruire, implementare și dezvoltări noi — la producător, pe telefon sau pe site.', rights: 'Toate drepturile rezervate.', madeBy: 'Producător: {{producer}}', developedBy: 'Dezvoltat de' },
  scan: { camera: 'Scanează cu camera', noCamera: 'Camera nu este disponibilă. Permiteți accesul la cameră sau scrieți codul.' },
}

export default ro9

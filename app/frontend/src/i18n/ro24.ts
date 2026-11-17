// Planificarea managerilor: planul lunar de încasări, îndeplinirea la zi și raportul zilnic pe Telegram.
const ro24 = {
  planning: {
    title: 'Planificare', execution: 'Îndeplinirea planului', plans: 'Planul pe luni', report: 'Trimiterea pe Telegram',
    manager: 'Manager', total: 'Total', collected: 'Încasat', day: 'Azi', week: 'Săptămâna', month: 'Luna', plan: 'Plan',
    left: 'Rămas', work: 'Activitatea: azi / săptămâna / luna', leads: 'Clienți noi', calls: 'Apeluri', offers: 'Oferte',
    orders: 'Comenzi', clients: 'Clienții managerului', active: 'Lucrează', potential: 'Potențiali', inactive: 'Nu lucrează',
    sleeping: 'Fără comandă > 1 lună', openOffers: 'Oferte deschise',
    expected: 'Din lună au trecut {{pct}} % (rămân {{days}} zile): procentul verde ține pasul, roșu — rămâne în urmă.',
    workHint: 'Încasat — plățile clienților managerului (minus restituirile), cu TVA, în lei; săptămâna începe luni. Clienți noi — creați în perioadă; apeluri — din activități; „Fără comandă > 1 lună” — clienții activi cu ultima comandă de peste 30 de zile; oferte deschise — ciorne, la aprobare și trimise.',
    sendNow: 'Trimite acum pe Telegram', sendConfirm: 'Trimiteți raportul acestei zile pe Telegram, după setările din „Trimiterea pe Telegram”?',
    sent: 'Trimis: {{names}}', skipped: 'Nu s-a trimis (fără Telegram legat): {{names}}',
    save: 'Salvează', saved: 'Salvat', copy: 'Copiază din luna trecută', copied: 'Planuri copiate: {{count}}',
    totalPlan: 'Total plan: {{sum}} lei', previous: 'Luna trecută',
    plansHint: 'Suma de încasat de la clienții fiecărui manager în luna aleasă, cu TVA. Gol sau 0 — fără plan. În listă sunt utilizatorii cu bifa „Manager de vânzări”.',
    inactiveUser: 'dezactivat', notManager: 'nu e manager',
    noTelegram: 'Botul Telegram nu este pornit: Administrare → Integrări → Telegram.',
    enabled: 'Trimite raportul în fiecare zi', hour: 'Ora trimiterii', days: 'Zilele',
    weekdays: ['Lu', 'Ma', 'Mi', 'Jo', 'Vi', 'Sâ', 'Du'],
    managersGet: 'Managerii primesc', managers_own: 'doar rândul lor', managers_all: 'tot tabelul', managers_none: 'nimic',
    recipients: 'Primesc tot tabelul', recipientsHint: 'Directorul, supraveghetorii. Fiecare își leagă Telegram-ul din Profilul meu.',
    noChat: 'fără Telegram legat', lastRun: 'Ultima trimitere: {{date}}.',
  },
}

export default ro24

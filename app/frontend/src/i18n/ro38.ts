// CAI CADRE — Etapa 5: termene și alerte, notificările, panoul de start.
export default {
  menu: { alerts: 'Termene și alerte' },
  dashboard: {
    title: 'Panoul de start', welcome: 'Bună, {{name}}!', travel: 'În deplasare / formare azi', alertsMonth: 'Termene în 30 de zile',
    leaveRequests: 'Cereri de concediu noi', ordersDraft: 'Ordine nesemnate', unacknowledged: 'Ordine nefamiliarizate',
    units: 'Statul de funcții', approved: 'Unități aprobate', occupied: 'Ocupate', nearest: 'Termenele cele mai apropiate',
    allAlerts: 'Toate ({{count}})', noAlerts: 'Nu sunt termene apropiate.', birthdays: 'Zile de naștere (7 zile)',
  },
  al: {
    tabs: { list: 'De făcut', settings: 'Setări', email: 'E-mail' },
    today: 'azi', ago_one: 'de {{count}} zi', ago_few: 'de {{count}} zile', ago_other: 'de {{count}} zile',
    in_one: 'peste {{count}} zi', in_few: 'peste {{count}} zile', in_other: 'peste {{count}} zile',
    allKinds: 'Toate tipurile', listHint: 'Lista se formează în fiecare zi; dublu clic deschide fișa sau documentul.',
    due: 'Termenul', kind: 'Tipul', what: 'Ce trebuie făcut', enabled: 'Pornit', days: 'Zile înainte', audience: 'Cine primește',
    settingsHint: 'Câte zile înainte de termen apare alerta. Notificările (în sistem și pe e-mail) se trimit noaptea, o singură dată pentru fiecare termen.',
    retMen: 'Vârsta de pensionare — bărbați', retWomen: 'Vârsta de pensionare — femei',
    emailDigest: 'Rezumatul pe e-mail', emailDigestHint: 'Trimite un e-mail cu alertele noi celor care au adresa completată',
    runNow: 'Trimite notificările acum', sent: 'Notificări trimise: {{count}}, e-mailuri: {{emails}}.',
    aud: { hr: 'Cadre', accounting: 'Contabilitate', head: 'Șeful subdiviziunii' },
    kinds: {
      probation_end: 'Sfârșitul perioadei de probă', contract_end: 'Expirarea contractului pe termen', document_expiry: 'Expirarea actului de identitate',
      childcare_end: 'Sfârșitul concediului de îngrijire a copilului',
      maternity_end: 'Sfârșitul concediului de maternitate', leave_unused: 'Concediu nefolosit (art. 118 CM)', sanction_expiry: 'Expirarea sancțiunii disciplinare',
      retirement: 'Atingerea vârstei de pensionare', birthday: 'Zile de naștere și jubilee',
      order_unacknowledged: 'Ordin nefamiliarizat', payroll_orders: 'Ordine pentru contabilitate', leave_requests: 'Cereri de concediu de examinat',
      next_month_leave: 'Concediile din luna următoare', roster_missing: 'Graficul lunii următoare lipsește', irm19_due: 'Termenul IRM19',
    },
    smtp: {
      hint: 'Serverul de e-mail al instituției, prin care se trimit notificările. Parola se păstrează criptat.',
      enabled: 'Trimiterea pe e-mail este pornită', host: 'Serverul SMTP', port: 'Portul', username: 'Utilizatorul', password: 'Parola',
      from: 'Adresa expeditorului', testTo: 'Adresa pentru probă', test: 'Trimite proba', testOk: 'Proba a fost trimisă la {{to}}.',
    },
  },
}

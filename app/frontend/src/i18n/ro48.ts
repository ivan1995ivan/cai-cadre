// CAI CADRE 1.2: corectările de mână în calcul și la plată (impozitul reținut la achitare), fluturașii în PDF și pe e-mail,
// cartea privind salariul.
export default {
  menu: { repSalaryBook: 'Cartea privind salariul' },
  pay: {
    correct: 'Corectează suma', editManual: 'Schimbă corectarea', correctFor: '{{name}} — corectarea: {{item}}', corrected: 'Corectat; impozitele s-au refăcut',
    correctHint: 'Suma scrisă de mână înlocuiește suma calculată de același tip (salariul, un spor, impozitul, CNAM, CAS); un tip fără calcul automat (premiu unic, reținere) se adaugă. Impozitul și CNAM se refac din sumele corectate, afară de cazul când le corectați și pe ele.',
    restore: 'Revine la suma calculată', restoreConfirm: 'Ștergeți corectarea și reveniți la suma calculată?',
    slipsPdf: 'Fluturașii în PDF', mailSlips: 'Trimite fluturașii pe e-mail', mailOnlyApproved: 'Fluturașii se trimit din calculul aprobat',
    mailTitle: 'Fluturașii pe e-mail',
    mailHint: 'Fiecare angajat primește o arhivă ZIP cu fluturașul lui în PDF. Parola arhivei: ultimele 5 cifre ale codului fiscal (IDNP). Cine nu are e-mail sau IDNP în dosar nu se poate bifa.',
    mailNoSmtp: 'E-mailul nu e configurat: Administrare → Setări → Poșta (e-mail) pentru notificări și fluturași (serverul SMTP).',
    mailSend: 'Trimite ({{count}})', mailSent: 'trimise: {{count}}', mailStatus: 'Starea',
    mailStatuses: { sent: 'Trimis', skipped: 'Netrimis', error: 'Eroare' },
  },
  pp: {
    toPay: 'De plată', manualHint: 'Corectat de mână',
    advanceLegend: 'Impozitul se reține la achitare: din avans — CNAM 9 % și impozitul 12 % din rest; scutirea lunii se ia la plata salariului. Corectați brutul (se refac impozitele), netul (se află brutul) sau impozitele direct. Avansul plătit se scade singur din calculul salariului pe luna lui.',
    salaryLegend: 'Sumele vin din calculele aprobate ale lunii: venitul, scutirea, CNAM și impozitul lunii, minus ce s-a reținut deja la avans — la salariu se reține doar diferența. Se pot corecta în ciornă; IPC21 (tabelul 1) și fișa personală anexa 8 se fac după datele achitării.',
  },
}

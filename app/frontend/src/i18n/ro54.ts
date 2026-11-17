// CAI CADRE 1.5.1: fluturașii din îndreptarea spre plată; Esc închide pagina, Alt+` — ferestrele deschise.
export default {
  print: {
    docTypes: { certificate_salary: 'Adeverință privind salariul (pentru bancă)' },
    options: { show_idnp: 'Cu IDNP', show_salary: 'Cu salariul', show_photo: 'Cu fotografia', show_family: 'Cu familia', show_military: 'Cu evidența militară', show_periods: 'Cu perioadele de muncă', group_by_subdivision: 'Grupat pe subdiviziuni', show_phone: 'Cu telefonul', show_rate: 'Cu norma', show_fund: 'Cu fondul de salarizare', show_categories: 'Cu categoriile' },
  },
  common: { closeForm: 'Închide (Esc)' },
  tabs: {
    windows: 'Ferestrele deschise',
    windowsHint: 'Săgețile sau Alt+` mută, Enter deschide, cifra 1–9 deschide direct, Esc închide lista.',
  },
  staff: {
    print: { certificate_salary: 'Adeverință privind salariul (pentru bancă)' },
    salaryPeriod: 'Perioada', salaryLastMonths: 'Ultimele {{count}} luni', salaryRange: 'Interval de luni…',
    purposeBankHint: 'de ex. BC „Moldindconbank” SA, pentru credit',
  },
  ord: {
    title: 'Titlul', preamble: 'Preambulul',
    numberDate: 'Nr. și data', seqAuto: 'automat', of: 'din', legalBases: 'Temeiurile legale',
    legalBasesHint: 'Unul sau mai multe; preambulul se compune din ele.', signer: 'Semnează',
  },
  org: { legalBases: 'Temeiurile legale implicite' },
  rep: { search: 'Caută raportul (denumire, descriere)', none: 'Niciun raport găsit.' },
  online: {
    live: 'În timp real', introLive: 'Online = programul deschis în ultimele {{minutes}} minute. Se actualizează singur la 10 secunde (ultima dată la {{at}}).',
    headerHint: 'Cine e online acum', you: 'dvs.', minutesAgo: 'acum {{count}} min', allSessions: 'Toate sesiunile →',
  },
  pay: { mailOnlyApproved: 'Fluturașii se trimit din îndreptarea aprobată sau achitată' },
}

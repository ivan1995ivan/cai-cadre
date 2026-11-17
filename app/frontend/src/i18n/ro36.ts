// CAI CADRE — Etapa 4b (partea 2): plata salariului și raportările.
export default {
  print: { docTypes: { payment_sheet: 'Stat de plată', bank_list: 'Lista pentru bancă', annual_card: 'Fișa personală anuală a veniturilor' } },
  pp: {
    tabs: { payments: 'Statele de plată', debts: 'Datorii salariale' },
    new: 'Plată nouă', kind: 'Ce se plătește', kinds: { salary: 'Salariu', advance: 'Avans' }, method: 'Modalitatea',
    methods: { all: 'Card și numerar', card: 'Card (bancă)', cash: 'Numerar (casa)' }, count: 'Persoane', card: 'Pe card', cash: 'Numerar',
    total: 'Total', paidOn: 'Achitat la', owed: 'Calculat (net + avans)', paidSum: 'Achitat', debt: 'Datoria',
    emptyHint: 'Pentru luna aleasă nu există plăți. „Plată nouă” — avansul (în timpul lunii) sau salariul (din calculul aprobat).',
    newHint: 'Avansul: procentul din constante × salariul de funcție × norma raportului de bază. Salariul: netul din calculele aprobate ale lunii, minus ce s-a plătit deja. Cardul — angajații cu IBAN în dosar; ceilalți — numerar.',
    debtsHint: 'La sfârșitul lunii alese: netul calculelor aprobate (cu avansurile reținute) minus tot ce s-a achitat. Negativ — plătit în plus.',
    heading: '{{kind}} nr. {{number}} — {{month}} {{year}}', refill: 'Completează din nou', refillConfirm: 'Sumele se recalculează; corectările de mână se pierd. Continuați?',
    pay: 'Achită', printSheet: 'Stat de plată', bankList: 'Lista pentru bancă', bankFile: 'Fișierul pentru bancă (CSV)',
    reference: 'Documentul de plată', referenceHint: 'Ordinul de plată (card) sau dispoziția de casă (numerar).',
    advanceLegend: 'Avansul aprobat se scade singur din calculul salariului pe luna lui (rândul „Avans plătit”).',
    salaryLegend: 'Sumele vin din calculele aprobate ale lunii (de plată, după avans și rețineri). Se pot corecta în ciornă; după achitare intră în datorii ca achitate.',
    annualCard: 'Fișa personală anuală a veniturilor (anexa 8)',
  },
  tax: {
    export: 'Export Excel', missingIdnp: '{{count}} persoane fără IDNP — completați-l în dosar înainte de depunere.',
    category: 'Codul categoriei asiguratului', source: 'Codul sursei de venit', event: 'Evenimentul', deadline: 'Termenul',
    cols: { income: 'Venitul', cas: 'CAS calculate', cnam: 'Prime CNAM', tax: 'Impozitul reținut', exemption: 'Scutirile' },
    ipcHint: 'Darea de seamă lunară (până la 25 a lunii următoare): din calculele aprobate ale lunii, pe persoane. Exportul are tabelul 1 (total) și tabelul 2 (persoane); declarația electronică se completează din el.',
    ialsHint: 'Nota de informare anuală (până la 25 ianuarie): venitul anului, scutirile cu codul din cerere, CNAM și impozitul reținut, pe persoane.',
    irmHint: 'Angajările, modificările și încetările din ordinele semnate (tipurile marcate „IRM19” în clasificator); se depun la CNAS în 10 zile lucrătoare — termenul depășit e cu roșu.',
    categoryHint: 'Codul din anexa 3 la ordinul MF (de verificat la fiecare modificare); se pune la toate persoanele.',
    sourceHint: 'De regulă SAL (salariu).',
  },
}

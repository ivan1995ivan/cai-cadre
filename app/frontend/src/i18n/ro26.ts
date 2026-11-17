// Salariile managerilor: schemele (fix + % pe trepte după plan) și calculul lunii cu plata din casă.
const ro26 = {
  salary: {
    title: 'Salarizare', calc: 'Calculul lunii', schemes: 'Schemele de salariu',
    make: 'Calculează luna', recompute: 'Recalculează', recomputed: 'Recalculat', save: 'Salvează', saved: 'Salvat',
    approve: 'Aprobă', approveConfirm: 'Aprobați calculul? Aprobat, nu se mai recalculează și se poate plăti.',
    unapprove: 'Anulează aprobarea', unapproveConfirm: 'Anulați aprobarea? Plățile făcute rămân.',
    statuses: { draft: 'Ciornă', approved: 'Aprobat' },
    empty: 'Luna nu e calculată încă. „Calculează luna” face câte un rând pentru fiecare manager trecut într-o schemă de salariu.',
    withoutScheme: 'Fără schemă de salariu (nu intră în calcul): {{names}}',
    manager: 'Manager', total: 'Total', plan: 'Plan încasări', collected: 'Încasat', fulfil: '% plan', salesNet: 'Vânzări fără TVA',
    margin: 'Marja', costMissing: 'Rânduri de factură fără cost: {{count}} (nu intră în marjă)', fixed: 'Fix',
    collectionsBonus: 'Din încasări', marginBonus: 'Din marjă', salesBonus: 'Din vânzări', extra: 'Prime (+)',
    deductions: 'Rețineri (−)', note: 'Notă', totalCol: 'De plată', paid: 'Achitat', rest: 'Rest',
    pay: 'Plătește', paidOk: 'Plata e făcută din casă.', payments: 'Plăți', account: 'Casa / contul', date: 'Data plății',
    whom: 'Cui', payHint: 'Se plătește restul fiecăruia; plata intră în Casă și bancă (articolul Salarii), împărțită pe manageri.',
    hint: 'Încasat — plățile clienților managerului cu TVA (ca la Planificare); vânzări și marja — din facturile înregistrate ale managerului minus retururile, fără TVA. Procentul se ia după treapta atinsă de % plan (în paranteză la trecerea cu mausul). Primele, reținerile și nota rămân la recalculare.',
    newScheme: 'Schemă nouă', schemeName: 'Denumirea', inactive: 'oprită', active: 'Activă', basePcts: 'De bază: încasări / marjă / vânzări',
    tiers: 'Treptele după % din plan', managers: 'Managerii', managersHint: 'Managerul trebuie să fie într-o singură schemă activă.',
    base: 'Fixul și procentele de bază', ofCollections: '% din încasări', ofMargin: '% din marjă', ofSales: '% din vânzări fără TVA',
    tiersHint: 'De la pragul atins (% din planul de încasări) se aplică procentele treptei; sub prima treaptă sau fără plan — cele de bază.',
    fromPct: 'De la % plan', addTier: 'Adaugă treaptă', notes: 'Note', deleteScheme: 'Ștergeți schema?',
    schemesHint: 'Fiecare schemă e un grup de manageri cu același fix și aceleași procente.',
    pctsLegend: 'Procentele se arată: din încasări / din marjă / din vânzări fără TVA.',
  },
}

export default ro26

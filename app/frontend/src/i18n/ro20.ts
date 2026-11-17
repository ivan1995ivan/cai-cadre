// Textele repartizării încasărilor pe facturi și ale extraselor bancare (MAIB, Victoriabank, MICB, FinComBank, OTP, Eximbank).
const ro20 = {
  alloc: {
    title: 'Pe ce facturi merge plata', invoices: 'Facturi', choose: 'Bifează facturile', edit: 'Schimbă',
    paymentAmount: 'Suma plății', allocated: 'Repartizat pe facturi', advance: 'Rămâne avans', overAllocated: 'Ați repartizat mai mult decât suma plății',
    auto: 'Propune automat', clear: 'Debifează tot', save: 'Confirmă repartizarea',
    hint: 'Programul a propus facturile din destinația plății, apoi cele mai vechi: fiecare se închide cât permite suma, ultima poate rămâne achitată parțial. Verificați, schimbați bifele sau sumele dacă e nevoie și confirmați.',
    invoice: 'Factura', date: 'Data', dueDate: 'Scadența', total: 'Total', paidBefore: 'Achitat', due: 'Rest de plată',
    onThis: 'Din această plată', remaining: 'Rămâne pe factură', none: 'Clientul nu are facturi neachitate în această valută.',
    proposed: 'propus automat', checked: 'verificat', noInvoices: 'fără facturi (avans)', duplicate: 'deja importat',
    duplicateHint: 'Același rând a venit și cu un extras anterior; nu se înregistrează a doua oară.',
    paid: 'Achitat', rest: 'Rest', status: 'Achitare', statuses: { unpaid: 'Neachitată', partial: 'Achitată parțial', paid: 'Achitată' },
    saved: 'Repartizarea a fost salvată', bank: 'Banca', format: 'Formatul',
    statementHint: 'Încărcați extrasul exportat din banca online: MAIB, Victoriabank, MICB, FinComBank, OTP Bank, Eximbank (formatul 1C, MT940, Excel .xlsx sau CSV). Programul găsește clientul / furnizorul după IDNO și repartizează singur încasările pe facturile clientului: întâi cele din destinația plății, apoi cele mai vechi. Verificați rândurile marcate „propus automat”, schimbați bifele dacă e nevoie, apoi „Înregistrează plățile”.',
    postConfirm: 'Înregistrați rândurile potrivite ca plăți, cu repartizarea pe facturi așa cum este acum? Cele marcate „Nu se înregistrează” se sar.',
    unchecked: 'Rânduri cu repartizarea propusă automat, neverificate: {{count}}',
  },
}
export default ro20

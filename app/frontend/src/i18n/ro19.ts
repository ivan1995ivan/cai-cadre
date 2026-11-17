// Textele retrobonusului: procentul din contract, calculul pe perioadă și factura cu minus.
const ro19 = {
  retro: {
    pct: 'Retrobonus, %', base: 'Retrobonusul se calculează', bases: { net: 'Din vânzările fără TVA', gross: 'Din vânzările cu TVA' },
    basesShort: { net: 'fără TVA', gross: 'cu TVA' },
    kind: 'Vânzare / retrobonus', kinds: { sale: 'Vânzare', retro_bonus: 'Retrobonus' },
    byMonth: 'Pe lună', byRange: 'Pe interval', postNow: 'Înregistrează imediat',
    issueSelected: 'Emite facturile cu minus ({{count}})', issue: 'Emite',
    confirmTitle: 'Emiterea retrobonusului pentru {{count}} clienți',
    confirmDraft: 'Se fac facturi-ciornă cu minus, în total {{total}}. Le verificați și le înregistrați din jurnalul facturilor.',
    confirmPosted: 'Se fac și se înregistrează facturile cu minus, în total {{total}}. Datoria clienților scade imediat.',
    issued: 'Facturi emise: {{count}}', someErrors: 'Unii clienți nu au primit factura',
    hint: 'Procentul și baza (fără TVA / cu TVA) se pun în contractul clientului (fișa clientului → Contracte). Baza = facturile de vânzare înregistrate din perioadă minus retururile. Factura cu minus scade datoria clientului; în jurnalul facturilor e marcată „Retrobonus”. Pentru aceeași perioadă nu se emite de două ori.',
    contract: 'Contractul', salesNet: 'Vânzări fără TVA', salesGross: 'Vânzări cu TVA', bonusNet: 'Bonus fără TVA',
    bonusGross: 'Bonus cu TVA', issuedCol: 'Emis pentru perioadă', notIssued: 'neemis', draft: 'ciornă', total: 'Total',
  },
}
export default ro19

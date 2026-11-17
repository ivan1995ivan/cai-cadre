// CAI CADRE — limbile sistemului, notificările doar pe e-mail, alegerea din clasificator („…”).
export default {
  constants: {
    languages: 'Limbile sistemului', languagesMin: 'Bifați cel puțin o limbă.',
    languagesHint: 'Doar limbile bifate apar în comutatorul de limbă, la intrare și în profil; câmpurile „Denumire (RU / EN)” se ascund pentru limbile oprite. Cine lucra într-o limbă oprită trece pe prima limbă bifată.',
  },
  profile: {
    emailTitle: 'Notificările pe e-mail', emailOn: 'Rezumatul termenelor noi se trimite la {{email}} (dacă e-mailul e pornit în Termene și alerte).',
    emailOff: 'Scrieți adresa de e-mail în profil ca să primiți rezumatul termenelor noi.',
  },
  picker: {
    search: 'Căutare', choose: 'Alege', open: 'Deschide clasificatorul', title: 'Alegeți din clasificator',
    hint: 'Dublu clic sau „Alege” pune elementul în câmp; elementul nou se adaugă cu „Adaugă”.',
  },
}

// CAI CADRE — Etapa 8: textele administrării fără resturile CRM; secțiile utilizatorului.
export default {
  users: {
    subdivisions: 'Subdiviziunile lui',
    subdivisionsHint: 'Pentru șeful de secție, asistentul medical superior: rolurile cu „doar ale mele / subdiviziunile mele” văd angajații, concediile, graficele și rapoartele doar din aceste subdiviziuni (cu sub-subdiviziunile, la „subdiviziunile mele”).',
  },
  roles: { hiddenFieldsHint: 'Ce date sensibile nu vede acest rol (de exemplu salariul sau datele de sănătate pentru șeful de secție).' },
  localities: {
    loadHint: 'Bifați țările ale căror localități le folosiți și apăsați „Încarcă”. Debifat = localitățile țării se scot din clasificator (cele adăugate de mână rămân). Adresele scrise în dosare rămân neschimbate.',
  },
  requiredFields: {
    hint: 'Bifați ce câmpuri trebuie completate în dosarul angajatului, la acte și la studii. Se verifică la salvare: fișa cu un câmp bifat gol nu se salvează.',
  },
}

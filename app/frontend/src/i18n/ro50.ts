// CAI CADRE 1.3.0: marcarea pentru ștergere (ca în 1C) și ștergerea obiectelor marcate din Administrare.
export default {
  menu: { markedObjects: 'Ștergerea obiectelor marcate' },
  marks: {
    models: { core_Locality: 'Localitate', core_Bank: 'Bancă' },
    mark: 'Marchează pentru ștergere', unmark: 'Scoate marcajul de ștergere', short: 'marcat pentru ștergere',
    markConfirm: 'Marcați pentru ștergere? Se șterge de tot doar din Administrare, dacă nu e folosit nicăieri.',
    unmarkConfirm: 'Scoateți marcajul de ștergere?',
    banner: 'Marcat pentru ștergere: nu se mai modifică. Se șterge de tot în Administrare → Ștergerea obiectelor marcate.',
    hint: 'Aici sunt toate obiectele marcate pentru ștergere. „Verifică legăturile” arată unde mai sunt folosite; „Șterge” le '
      + 'șterge de tot doar pe cele pe care nu le folosește nimic (obiectele alese împreună se șterg în ordinea potrivită); '
      + 'celelalte rămân marcate, cu legăturile lor. Fără bife — se iau toate cele din listă. Faceți întâi o copie de rezervă.',
    allTypes: 'Toate tipurile', refresh: 'Reîmprospătează', check: 'Verifică legăturile',
    deleteAll: 'Șterge cele nefolosite', deleteSelected: 'Șterge cele bifate (nefolosite)',
    deleteConfirm: 'Ștergeți de tot obiectele nefolosite ({{count}} alese)? Operația nu se poate anula.',
    unmarkSelected: 'Scoate marcajul', unmarkSelectedConfirm: 'Scoateți marcajul de la {{count}} obiecte?',
    unmarked: 'Marcaj scos: {{count}}', deleted: 'Șterse de tot: {{count}}', checked: 'Nefolosite: {{free}}, folosite: {{used}}',
    empty: 'Nu este niciun obiect marcat pentru ștergere.',
    type: 'Tipul', object: 'Obiectul', refs: 'Unde este folosit', free: 'nefolosit — se poate șterge', used: 'folosit ({{count}})',
  },
}

// Documentele clientului (ca „Документы контрагента” din 1C) și așezarea meniului principal (sus / în stânga).
const ro27 = {
  clientDocs: {
    tab: 'Documente', document: 'Documentul', amount: 'Suma', channel: 'Casa / banca', comment: 'Comentariu',
    search: 'Număr, comentariu', groups: { offers: 'Oferte', orders: 'Comenzi', invoices: 'Facturi și avize', payments: 'Achitări',
      returns: 'Retururi', incoming: 'Facturi de intrare' },
  },
  act: {
    open: 'Deschide', edit: 'Redactează', external: 'Deschide în fereastră nouă', mail: 'Scrie un e-mail', phone: 'Sună',
    map: 'Arată pe hartă', info: 'Detalii', clear: 'Șterge', all: 'Alege toate', delete: 'Șterge', undo: 'Anulează',
  },
  acc: {
    menuTop: 'Meniu: secțiunile sus', menuLeft: 'Meniu: secțiunile în stânga',
    menuDefault: 'Așezarea meniului pentru toți:', menuDefaultHint: 'Fiecare își poate schimba așezarea din butonul cu paleta de culori (sus, dreapta).',
  },
}

export default ro27

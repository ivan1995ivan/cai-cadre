// Textele schimbului între firme (comenzi la furnizori, starea lor și facturile, prin hub).
const ro14 = {
  exchange: {
    title: 'Schimb între firme (CAI ERP)', status: 'Starea', active: 'Activ',
    hint: 'Firmele care lucrează în CAI ERP se leagă între ele: comanda la furnizor ajunge în programul furnizorului ca o comandă de client, aici se vede starea și etapele ei, iar factura furnizorului vine singură ca factură de intrare (ciornă). Programele vorbesc printr-un serviciu central, deci merge și cu programul instalat în birou.',
    hubUrl: 'Adresa serviciului de schimb', hubKey: 'Cheia de înregistrare (dacă e cerută)', connect: 'Conectează firma',
    connected: 'Firma este conectată la schimb', enabled: 'Schimbul este pornit', connectedTo: 'Conectat: {{url}}',
    lastSync: 'Ultima sincronizare', pending: '{{n}} de trimis', syncNow: 'Sincronizează acum', synced: 'Sincronizat',
    manager: 'Managerul comenzilor primite (clienți noi)', managerHint: 'administratorul',
    partners: 'Firme legate', invite: 'Dă un cod de invitație', codePlaceholder: 'Codul primit', accept: 'Leagă cu codul',
    linked: 'Firmele s-au legat', giveCode: 'Dați partenerului acest cod:', codeValid: 'Codul e valabil până la {{date}}, o singură dată.',
    noPartners: 'Nicio firmă legată încă. Dați un cod de invitație sau introduceți codul primit de la partener.',
    partner: 'Firma', asSupplier: 'Furnizorul nostru (îi trimitem comenzi)', asClient: 'Clientul nostru (ne trimite comenzi)', notSupplier: 'nu e furnizor',
    incoming: 'Comenzi primite', noIncoming: 'Nicio comandă primită prin schimb.', theirNumber: 'Nr. lor', positions: 'Poziții',
    mapProducts: 'Legați produsele', mapHint: 'Produsele nerecunoscute după codul de bare se aleg o dată; data viitoare se recunosc singure.',
    theirProduct: 'Produsul lor (cod de bare · cod)', ourProduct: 'Produsul nostru', recognized: 'recunoscut', chooseProduct: 'Alegeți produsul',
    createOrder: 'Creează comanda', reject: 'Refuză', rejectReason: 'Motivul refuzului',
    log: 'Jurnal', received: 'Primite', sent: 'Trimise', message: 'Mesajul', done: 'aplicat', notApplied: 'neaplicat', retry: 'Aplică din nou',
    applied: 'Mesajul s-a aplicat', delivered: 'predat', waiting: 'de trimis',
    kinds: {
      po_new: 'Comandă la furnizor', po_cancel: 'Comandă anulată', order_accepted: 'Comanda primită de furnizor',
      order_status: 'Starea comenzii', order_rejected: 'Comandă refuzată', invoice_posted: 'Factură', invoice_cancelled: 'Factură anulată',
    },
    willSend: 'Furnizorul {{partner}} lucrează în CAI ERP: la „Trimite”, comanda ajunge direct în programul lui.',
    atSupplier: 'La furnizor: {{partner}}', theirOrder: 'Comanda la furnizor', notYet: 'încă nu a primit-o', updated: 'Actualizat',
    stages: 'Etapele', invoices: 'Facturile furnizorului', openReceipt: 'factura de intrare', cancelledInvoice: 'anulată',
  },
  reportWindows: { name: 'Raport {{n}}', add: 'Încă o dată', tabs: 'File', side: 'Alături' },
}
export default ro14

// Textele pentru comenzile la furnizori și aprovizionarea comenzilor.
const ro10 = {
  purchases: {
    order: 'Comanda la furnizor', new: 'Comandă nouă la furnizor', search: 'Număr, furnizor, comanda clientului',
    salesOrder: 'Comanda clientului', expected: 'Livrare așteptată', positions: 'Poziții', price: 'Preț (fără TVA)',
    received: 'Primit', receipts: 'Facturi de intrare', supplierRef: 'Nr. confirmării furnizorului',
    send: 'Trimisă furnizorului', makeReceipt: 'Intrare (factura de intrare)', cancel: 'Anulează',
    cancelConfirm: 'Anulați comanda la furnizor?',
    status: { draft: 'Ciornă', sent: 'Trimisă', partial: 'Primită parțial', received: 'Primită', cancelled: 'Anulată' },
    supplyTab: 'Aprovizionare', fromOrder: 'Comandă la furnizor', create: 'Creează comanda',
    created: 'Comanda la furnizor {{number}} a fost creată',
    fromOrderHint: 'Implicit se comandă ce lipsește: nici rezervat din stoc, nici facturat, nici comandat deja. Când marfa intră (intrarea făcută din comanda la furnizor), se rezervă singură pe această comandă.',
    missing: 'Lipsește', toOrder: 'De comandat', alreadyOrdered: 'Comandat deja', modeOrder: 'Cantitatea din comandă',
    modeMissing: 'Doar ce lipsește', modeOrderHint: 'Implicit: cantitatea din comandă minus ce s-a comandat deja la furnizori. Cantitățile se pot corecta.', hasMissing: 'Unele poziții nu sunt acoperite din stoc.',
    confirmFirst: 'Confirmați comanda: atunci se rezervă ce e în stoc și se vede ce trebuie comandat.',
    supplierOrders: 'Comanda la furnizor', issuedInvoices: 'Factura emisă (← intrarea mărfii)',
  },
}

export default ro10

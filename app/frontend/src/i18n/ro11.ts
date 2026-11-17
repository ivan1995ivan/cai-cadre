// Textele Panoului de administrare.
const ro11 = {
  panel: {
    newOffer: 'Ofertă nouă', fromCalculator: 'Din calculator', newClient: 'Client nou', newOrder: 'Comandă nouă',
    ownOnly: 'Doar clienții și documentele mele',
    tabs: { calendar: 'Calendar', clients: 'Clienți', offers: 'Oferte', orders: 'Comenzile', purchases: 'Aprovizionări', products: 'Mărfuri noi', differences: 'Diferențele' },
    subs: {
      clients: { persons: 'Finali', companies: 'Corporativi' },
      offers: { all: 'Toate', open: 'Deschise' },
      orders: { current: 'Comenzile curente', partial: 'Parțial eliberate', released: 'Eliberate', reserved: 'Rezervări',
        confirmed: 'Confirmate', production_draft: 'Cu act de producere nevalidat' },
      purchases: { open: 'În așteptare', all: 'Toate' },
      differences: { pending: 'De aprobat', to_pay: 'De plătit', all: 'Toate' },
    },
    search: 'Căutare', limit: 'Se arată primele 300 de rânduri; folosiți căutarea.',
  },
}

export default ro11

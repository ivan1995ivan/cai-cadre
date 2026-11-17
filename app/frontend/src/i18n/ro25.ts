// Documentul „Setarea prețurilor”: prețurile noi ale mărfurilor (pe variante) în listele de prețuri, de la o dată.
const ro25 = {
  priceDocs: {
    title: 'Setarea prețurilor', one: 'Setarea prețurilor', new: 'Setarea prețurilor nouă',
    hint: 'Documentul cu prețurile noi ale mărfurilor în una sau mai multe liste de prețuri, valabile de la data lui. Fiecare variantă (culoare, grosime...) are prețul ei. Înregistrat, documentul scrie prețurile; istoricul rămâne, anularea înregistrării le scoate.',
    all: 'Toate', statuses: { draft: 'Ciornă', posted: 'Înregistrat' }, search: 'Număr, marfă, notă',
    number: 'Număr', date: 'Valabil de la', status: 'Starea', lists: 'Listele de prețuri', goods: 'Mărfuri', notes: 'Notă',
    author: 'Autor', validFrom: 'Prețurile valabile de la', validFromHint: 'Ofertele și comenzile de la această dată iau prețul nou.',
    chooseList: 'Alegeți lista de prețuri', addGoods: 'Adaugă mărfuri', siblings: 'cu toate variantele produsului',
    siblingsHint: 'Alegeți o culoare — se adaugă toate culorile (variantele) produsului, fiecare pe rândul ei, ca să le puneți același preț sau prețuri diferite.',
    fromCategory: 'Toată categoria…', change: 'Modifică prețurile cu %', removeSelected: 'Scoate alese ({{count}})',
    alreadyIn: 'Mărfurile sunt deja în document.', code: 'Cod', goodsName: 'Marfa (varianta)', unit: 'U.m.',
    current: 'Acum', before: 'Înainte', newPrice: 'Preț nou', copySiblings: 'Același preț la celelalte variante ale produsului',
    remove: 'Scoate rândul', save: 'Salvează', saved: 'Salvat', post: 'Înregistrează', posted: 'Prețurile sunt scrise.',
    postConfirm: 'Înregistrați? Prețurile noi intră în vigoare de la {{date}}.', unpost: 'Anulează înregistrarea',
    unpostConfirm: 'Anulați înregistrarea? Prețurile scrise de document se scot (cele de dinainte rămân în vigoare).',
    deleteConfirm: 'Ștergeți ciorna?', postedBy: 'Înregistrat de {{name}}.',
    allLists: 'Toate listele din document', from: 'De la', fromCurrent: 'prețul de acum', fromNew: 'prețul nou scris',
    percent: 'Cu cât', percentHint: 'De exemplu 5 = +5 %, −3 = −3 %', rounding: 'Rotunjire până la', rows: 'Rândurile',
    allRows: 'toate', selectedRows: 'cele alese ({{count}})',
  },
}

export default ro25

// Textele pentru unitățile de ambalare (bax, SET 5+1), datele logistice ale produsului și GOST / producător.
const ro16 = {
  packs: {
    title: 'Unități de ambalare',
    hint: 'Câte unități de bază are ambalajul. „Din care gratuite” face o promoție: SET = 6 buc, din care 1 gratuită — clientul plătește 5 buc la prețul din listă. Unitatea „implicită” se propune singură la adăugarea mărfii în ofertă sau comandă.',
    unit: 'Unitatea', name: 'Denumirea pe documente', namePlaceholder: 'de ex. SET 5+1', factor: 'Conține (unități de bază)',
    free: 'Din care gratuite', isDefault: 'Implicită la vânzare', add: 'Adaugă unitate de ambalare',
    baseUnit: 'unitatea de bază', lineUnit: 'U.M. de vânzare', packQty: 'Cantitatea', inBase: '= {{qty}} {{unit}}',
    free_note: '{{free}} gratuit',
  },
  logistics: {
    tab: 'Date logistice', manufacturer: 'Producătorul (fabrica)', gost: 'GOST / standard (SM, ТУ)',
    product: 'Produs', box: 'Bax', pallet: 'Palet', truck: 'Camion', container: 'Container',
    hint: 'Greutățile în kg, dimensiunile în cm, volumul în m³. Câmpurile se pot pune pe formele de tipar (Administrare → Forme de tipar → coloanele tabelului).',
    fields: {
      net_weight: 'Greutate (netă)', gross_weight: 'Greutate (brută)', depth: 'Adâncime', width: 'Lățime', height: 'Înălțime',
      volume: 'Volum', shelf_life_days: 'Termen valabilitate (zile)',
      box_qty: 'Bucăți', show_box: 'ShowBox', big_pallets: 'Paletare paleți mari', box_material_weight: 'Greutate material ambalare',
      box_net_weight: 'Greutate (netă)', box_gross_weight: 'Greutate (brută)', box_length: 'Lungime', box_width: 'Lățime',
      box_height: 'Înălțime', box_ean: 'EAN bax',
      pallet_boxes: 'Baxuri', pallet_rows: 'Rânduri', pallet_weight: 'Greutate palet', pallet_boxes_per_row: 'Baxuri pe rând',
      pallet_qty: 'Bucăți pe palet', pallet_net_weight: 'Greutate (netă)', pallet_gross_weight: 'Greutate (brută)',
      pallet_length: 'Lungime', pallet_width: 'Lățime', pallet_height: 'Înălțime', pallet_ean: 'EAN palet',
      truck90_pallets: 'Bucăți în 90 m³ (cu paleți)', truck90_bulk: 'Bucăți în 90 m³ (vrac)',
      truck120_pallets: 'Bucăți în 120 m³ (cu paleți)', truck120_bulk: 'Bucăți în 120 m³ (vrac)',
      container20_pallets: 'Bucăți în 20\' (cu paleți)', container20_bulk: 'Bucăți în 20\' (vrac)',
      container40_pallets: 'Bucăți în 40\' (cu paleți)', container40_bulk: 'Bucăți în 40\' (vrac)',
    },
  },
}
export default ro16

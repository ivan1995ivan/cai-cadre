// Тексты для единиц упаковки (ящик, НАБОР 5+1), логистических данных товара и ГОСТ / производителя.
const ru16 = {
  packs: {
    title: 'Единицы упаковки',
    hint: 'Сколько базовых единиц в упаковке. «Из них бесплатно» делает акцию: НАБОР = 6 шт, из них 1 бесплатно — клиент платит 5 шт по цене прайса. «По умолчанию» подставляется сама при добавлении товара в предложение или заказ.',
    unit: 'Единица', name: 'Название в документах', namePlaceholder: 'например, НАБОР 5+1', factor: 'Содержит (базовых ед.)',
    free: 'Из них бесплатно', isDefault: 'По умолчанию в продаже', add: 'Добавить единицу упаковки',
    baseUnit: 'базовая единица', lineUnit: 'Ед. продажи', packQty: 'Количество', inBase: '= {{qty}} {{unit}}',
    free_note: '{{free}} бесплатно',
  },
  logistics: {
    tab: 'Данные логистики', manufacturer: 'Производитель (завод)', gost: 'ГОСТ / стандарт (SM, ТУ)',
    product: 'Товар', box: 'Ящик', pallet: 'Паллета', truck: 'Грузовик', container: 'Контейнер',
    hint: 'Вес в кг, размеры в см, объём в м³. Поля можно вывести в печатные формы (Администрирование → Печатные формы → колонки таблицы).',
    fields: {
      net_weight: 'Вес (нетто)', gross_weight: 'Вес (брутто)', depth: 'Глубина', width: 'Ширина', height: 'Высота',
      volume: 'Объём', shelf_life_days: 'Срок годности (дней)',
      box_qty: 'Штук', show_box: 'ShowBox', big_pallets: 'Паллетирование на больших паллетах', box_material_weight: 'Вес упаковочного материала',
      box_net_weight: 'Вес (нетто)', box_gross_weight: 'Вес (брутто)', box_length: 'Длина', box_width: 'Ширина',
      box_height: 'Высота', box_ean: 'EAN ящика',
      pallet_boxes: 'Ящиков', pallet_rows: 'Рядов', pallet_weight: 'Вес паллеты', pallet_boxes_per_row: 'Ящиков в ряду',
      pallet_qty: 'Штук на паллете', pallet_net_weight: 'Вес (нетто)', pallet_gross_weight: 'Вес (брутто)',
      pallet_length: 'Длина', pallet_width: 'Ширина', pallet_height: 'Высота', pallet_ean: 'EAN паллеты',
      truck90_pallets: 'Штук в 90 м³ (с паллетами)', truck90_bulk: 'Штук в 90 м³ (навалом)',
      truck120_pallets: 'Штук в 120 м³ (с паллетами)', truck120_bulk: 'Штук в 120 м³ (навалом)',
      container20_pallets: 'Штук в 20\' (с паллетами)', container20_bulk: 'Штук в 20\' (навалом)',
      container40_pallets: 'Штук в 40\' (с паллетами)', container40_bulk: 'Штук в 40\' (навалом)',
    },
  },
}
export default ru16

// Тексты документа «Разница» (кэшбэк посреднику).
const ru12 = {
  rebates: {
    new: 'Новая разница', doc: 'Разница', search: 'Номер, клиент, посредник, заказ', buyer: 'Покупатель',
    intermediary: 'Посредник', orders: 'Заказы', difference: 'Разница', amount: 'К оплате', paid: 'Оплачено',
    status: { draft: 'Черновик', sales_approved: 'Утверждено отделом продаж', approved: 'Утверждено', paid: 'Оплачено', cancelled: 'Отменено' },
    fill: 'Заполнить по счетам', approveSales: 'Утверждено отделом продаж', approve: 'Утверждено (окончательно)',
    approveSalesConfirm: 'Подтвердить утверждение отделом продаж?', approveConfirm: 'Окончательное утверждение: после него разницу можно оплатить.',
    toDraft: 'Вернуть в черновик', pay: 'Оплатить', draftHint: 'До окончательного утверждения документ ни на что не влияет.',
    intermediaryDiscount: 'Скидка посредника', discountHint: 'Пусто = скидка посредника из его карточки.',
    paymentRate: 'Курс для оплаты', cashback: 'Кэшбэк (монтажник)', bankTransfer: 'Банковский перевод', retention: 'Удержание',
    retentionPct: 'Удержание, %', lines: 'Список', payments: 'Платёжные документы', documents: 'Документы', goods: 'Товар',
    listPrice: 'Цена', clientDiscount: 'Скидка клиента', clientPrice: 'Цена клиента', intermediaryPrice: 'Цена посредника',
    payKind: 'Как оплачено', payKinds: { cash: 'Из кассы', bank: 'Переводом', goods: 'Товаром' },
    goodsInvoice: 'Счёт, выставленный посреднику', goodsHint: 'Товар, выданный в счёт разницы: сумма засчитывается как оплата этого счёта (без денег из кассы).',
    clientTotal: 'Сумма клиента', intermediaryTotal: 'Сумма посредника', appliedPct: 'Применённая скидка посредника',
  },
}

export default ru12

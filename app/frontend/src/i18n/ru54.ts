// CAI CADRE 1.5.1: расчётные листки из ведомости на выплату; Esc закрывает страницу, Alt+` — открытые окна.
export default {
  print: {
    docTypes: { certificate_salary: 'Справка о заработной плате (для банка)' },
    options: { show_idnp: 'С IDNP', show_salary: 'С окладом', show_photo: 'С фотографией', show_family: 'С семьёй', show_military: 'С воинским учётом', show_periods: 'С периодами работы', group_by_subdivision: 'По подразделениям', show_phone: 'С телефоном', show_rate: 'Со ставкой', show_fund: 'С фондом оплаты труда', show_categories: 'С категориями' },
  },
  common: { closeForm: 'Закрыть (Esc)' },
  tabs: {
    windows: 'Открытые окна',
    windowsHint: 'Стрелки или Alt+` — выбор, Enter — открыть, цифра 1–9 — открыть сразу, Esc — закрыть список.',
  },
  staff: {
    print: { certificate_salary: 'Справка о заработной плате (для банка)' },
    salaryPeriod: 'Период', salaryLastMonths: 'Последние {{count}} мес.', salaryRange: 'Интервал месяцев…',
    purposeBankHint: 'напр. BC «Moldindconbank» SA, для кредита',
  },
  ord: {
    title: 'Заголовок', preamble: 'Преамбула',
    numberDate: '№ и дата', seqAuto: 'авто', of: 'от', legalBases: 'Правовые основания',
    legalBasesHint: 'Одно или несколько; преамбула составляется из них.', signer: 'Подписывает',
  },
  org: { legalBases: 'Правовые основания по умолчанию' },
  rep: { search: 'Поиск отчёта (название, описание)', none: 'Отчёты не найдены.' },
  online: {
    live: 'В реальном времени', introLive: 'Онлайн = программа открыта в последние {{minutes}} мин. Обновляется само каждые 10 секунд (последний раз в {{at}}).',
    headerHint: 'Кто сейчас онлайн', you: 'вы', minutesAgo: '{{count}} мин назад', allSessions: 'Все сеансы →',
  },
  pay: { mailOnlyApproved: 'Листки отправляются из утверждённой или выплаченной ведомости' },
}

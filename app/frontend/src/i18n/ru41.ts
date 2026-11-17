// CAI CADRE — Этап 6, часть 2: охрана здоровья и воинский учёт.
export default {
  staff: { tabs: { health: 'Здоровье' } },
  al: { kinds: { medical_exam_due: 'Периодический медосмотр', briefing_due: 'Инструктаж по охране труда', vaccination_due: 'Вакцинация (следующая доза)' } },
  hl: {
    tabs: { due: 'Сроки', exams: 'Медосмотры', vaccinations: 'Прививки', briefings: 'Инструктажи по ОТ' },
    allWhat: 'Медосмотр, инструктаж, прививка', horizon: 'Дней вперёд', printList: 'Список для медицины труда', settings: 'Периодичность',
    examOrder: 'Приказ о направлении на медосмотр ({{count}})', whatCol: 'Что', last: 'Последний раз', due: 'Срок',
    dueHint: 'Просрочено: {{overdue}} · нет записи: {{missing}} · скоро: {{due}}. Следующий срок заполняется сам по периодичности, если не указан.',
    what: { exam: 'Медосмотр', briefing: 'Инструктаж по ОТ', vaccine: 'Вакцинация' },
    status: { overdue: 'Просрочено', missing: 'Нет записи', due: 'Предстоит' },
    examMonths: 'Периодический медосмотр — раз в (мес.)', briefingMonths: 'Периодический инструктаж — раз в (мес.)',
    horizonDays: 'Показывать сроки за (дней)',
    vaccineHint: 'Ревакцинация и обязательные прививки для медперсонала задаются в Администрирование → Настройки → Вакцины (extra: months, required).',
    nextHint: 'Пусто = рассчитывается по периодичности.',
    examKinds: { preliminary: 'При приёме', periodic: 'Периодический', extraordinary: 'Внеочередной', return: 'При возобновлении работы' },
    conclusions: { fit: 'Годен', restricted: 'Годен с ограничениями', temporary: 'Временно не годен', unfit: 'Не годен' },
    briefingKinds: { introductory: 'Вводный', initial: 'Первичный на рабочем месте', periodic: 'Повторный', unplanned: 'Внеплановый', targeted: 'Целевой' },
    f: {
      kind: 'Вид', kind_label: 'Вид', date: 'Дата', next_date: 'Следующий срок', institution: 'Медучреждение', conclusion: 'Заключение',
      restrictions: 'Ограничения / рекомендации', document: 'Карта / справка', note: 'Примечания', vaccine: 'Вакцина', vaccine_name: 'Вакцина',
      dose: 'Доза', series: 'Серия / партия', refused: 'Письменный отказ', instructor: 'Провёл', topic: 'Тема',
    },
  },
  mil: {
    tabs: { military_register: 'Реестр', military_missing: 'Без карточки', military_changes: 'Изменения за месяц', military_recruits: 'Призывники' },
  },
}

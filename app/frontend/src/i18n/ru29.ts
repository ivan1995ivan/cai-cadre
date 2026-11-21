// CAI CADRE: меню, разделы и стартовая панель (перекрывают ключи из CAI ERP).
export default {
  menu: {
    dashboard: 'Стартовая панель', portal: 'Мой кабинет',
    org: 'Предприятие и подразделения', staffList: 'Штатное расписание', dictionaries: 'Классификаторы',
    employees: 'Сотрудники', contracts: 'Трудовые договоры',
    orders: 'Приказы', ordersRegister: 'Журнал приказов',
    leave: 'Отпуска', leaveSchedule: 'График отпусков', sickLeave: 'Больничные листы', worktime: 'Графики работы и смены',
    timesheets: 'Табели учёта времени',
    payroll: 'Расчёт зарплаты', payrollPayments: 'Выплата и перечисление', payrollSettings: 'Настройки зарплаты', taxReports: 'Отчётность (IPC21, IALS21, IRM19)',
    training: 'Обучение персонала', health: 'Охрана здоровья и труда', military: 'Воинский учёт',
    reports: 'Отчёты',
    users: 'Пользователи', online: 'Кто сейчас работает', roles: 'Роли и права', constants: 'Константы (предприятие)',
    currencies: 'Валюты', numbering: 'Нумерация документов', printTemplates: 'Печатные формы', excelImport: 'Импорт из Excel',
    audit: 'Журнал аудита', mainMenu: 'Главное меню', localities: 'Населённые пункты', banks: 'Банки',
    requiredFields: 'Обязательные поля', maintenance: 'Обслуживание', license: 'Лицензия',
  },
  menuSections: {
    principal: 'Главное', institutia: 'Предприятие', angajati: 'Сотрудники', ordine: 'Приказы', concedii: 'Отпуска и рабочее время',
    salarii: 'Зарплата', formare: 'Обучение и учёт', rapoarte: 'Отчёты', administrare: 'Администрирование', altele: 'Прочее',
  },
  dashboard: {
    title: 'Стартовая панель', welcome: 'Здравствуйте, {{name}}! Показатели предприятия появятся здесь вместе с кадровыми модулями.',
    employees: 'Работающих сотрудников', vacancies: 'Вакантных ставок', onLeave: 'В отпуске сегодня', sick: 'На больничном сегодня',
  },
}

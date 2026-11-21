// CAI CADRE: meniul, secțiunile și panoul de start (suprascriu cheile moștenite din CAI ERP).
export default {
  menu: {
    dashboard: 'Panoul de start', portal: 'Cabinetul meu',
    org: 'Instituția și subdiviziunile', staffList: 'State de personal', dictionaries: 'Clasificatoare',
    employees: 'Angajați', contracts: 'Contracte de muncă',
    orders: 'Ordine', ordersRegister: 'Registrul ordinelor',
    leave: 'Concedii', leaveSchedule: 'Graficul concediilor', sickLeave: 'Concedii medicale', worktime: 'Grafice de lucru și ture',
    timesheets: 'Tabele de pontaj',
    payroll: 'Calculul salariului', payrollPayments: 'Plata și achitarea', payrollSettings: 'Setările salariului', taxReports: 'Raportări (IPC21, IALS21, IRM19)',
    training: 'Formare și atestare', health: 'Sănătatea în muncă', military: 'Evidența militară',
    reports: 'Rapoarte',
    users: 'Utilizatori', online: 'Cine lucrează acum', roles: 'Roluri și drepturi', constants: 'Constante (instituția)',
    currencies: 'Valute', numbering: 'Numerotarea documentelor', printTemplates: 'Forme de tipar', excelImport: 'Import din Excel',
    audit: 'Jurnal de audit', mainMenu: 'Meniul principal', localities: 'Localități', banks: 'Bănci',
    requiredFields: 'Câmpuri obligatorii', maintenance: 'Întreținere', license: 'Licență',
  },
  menuSections: {
    principal: 'Principal', institutia: 'Instituția', angajati: 'Angajați', ordine: 'Ordine', concedii: 'Concedii și timp de muncă',
    salarii: 'Salarizare', formare: 'Formare și evidențe', rapoarte: 'Rapoarte', administrare: 'Administrare', altele: 'Altele',
  },
  dashboard: {
    title: 'Panoul de start', welcome: 'Bună, {{name}}! Indicatorii instituției apar aici odată cu modulele de cadre.',
    employees: 'Angajați activi', vacancies: 'Posturi vacante', onLeave: 'În concediu azi', sick: 'În concediu medical azi',
  },
}

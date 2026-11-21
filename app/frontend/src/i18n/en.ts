// CAI CADRE: English interface. Keys missing here fall back to Romanian (i18n fallbackLng); the generic screens inherited
// from CAI ERP are translated progressively, the HR modules are written in all three languages from the start.
export default {
  common: {
    notAllowed: 'You do not have access to this screen.', soon: 'Coming soon.', comingInStage: 'This module arrives in stage {{stage}} of the plan.',
    save: 'Save', cancel: 'Cancel', close: 'Close', delete: 'Delete', edit: 'Edit', add: 'Add', search: 'Search', yes: 'Yes', no: 'No',
    actions: 'Actions', name: 'Name', code: 'Code', active: 'Active', inactive: 'Inactive', export: 'Export to Excel (CSV)',
    total: 'Total: {{count}}', loading: 'Loading…', saved: 'Saved.', error: 'Error', confirmDelete: 'Delete this record?',
  },
  menu: {
    dashboard: 'Home', portal: 'My cabinet',
    org: 'Company and departments', staffList: 'Staff list', dictionaries: 'Classifiers',
    employees: 'Employees', contracts: 'Employment contracts',
    orders: 'Orders', ordersRegister: 'Orders register',
    leave: 'Leave', leaveSchedule: 'Leave schedule', sickLeave: 'Sick leave', worktime: 'Work schedules and shifts',
    timesheets: 'Timesheets',
    payroll: 'Payroll calculation', payrollPayments: 'Payment and payout', payrollSettings: 'Payroll settings', taxReports: 'Tax reports (IPC21, IALS21, IRM19)',
    training: 'Training and attestation', health: 'Occupational health', military: 'Military records',
    reports: 'Reports',
    users: 'Users', online: 'Who is online', roles: 'Roles and permissions', constants: 'Constants (company)',
    currencies: 'Currencies', numbering: 'Document numbering', printTemplates: 'Print forms', excelImport: 'Import from Excel',
    audit: 'Audit log', mainMenu: 'Main menu', localities: 'Localities', banks: 'Banks',
    requiredFields: 'Required fields', maintenance: 'Maintenance', license: 'License',
  },
  menuSections: {
    principal: 'Home', institutia: 'Company', angajati: 'Employees', ordine: 'Orders', concedii: 'Leave and working time',
    salarii: 'Payroll', formare: 'Training and records', rapoarte: 'Reports', administrare: 'Administration', altele: 'Other',
  },
  dashboard: {
    title: 'Home', welcome: 'Hello, {{name}}! The company indicators appear here together with the HR modules.',
    employees: 'Active employees', vacancies: 'Vacant positions', onLeave: 'On leave today', sick: 'On sick leave today',
  },
}

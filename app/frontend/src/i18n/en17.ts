// CAI CADRE: menu groups (Registers / Reports / Settings), reports as menu items, "Close all" in the open windows bar.
export default {
  menu: {
    repMovement: 'Staff turnover', repStructure: 'Staff structure', repSeniority: 'Seniority',
    repBirthdays: 'Birthdays and jubilees', repRetirements: 'Retirements', repVacancies: 'Vacant positions',
    repMunca1: 'Labour 1 (NBS)',
    repLeavePeriod: 'Leave and absences by period', repTimesheetSummary: 'Consolidated timesheet',
    repOrdersPayroll: 'Orders extract for accounting', repOrdersByType: 'Orders by type',
    repTrainingPeriod: 'Training by period', repTrainingExpiry: 'Expiring training certificates',
    repHealthDue: 'Occupational health and safety deadlines',
    repMilitaryRegister: 'Military record register', repMilitaryMissing: 'Without military record',
    repMilitaryChanges: 'Monthly changes for the military centre', repMilitaryRecruits: 'List of recruits',
  },
  menuGroups: { items: 'Registers', reports: 'Reports' },
  mainMenu: {
    hint: 'The menu sections and, in each, the Registers / Reports groups, as in 1C (settings are not in sections: all of them are in Administration → Settings). Drag a function into another group or section, or up / down; the same function can sit in several places. Sections move the same way; pick one to rename it or change its icon. Who sees what — the checkboxes of each role (Administration → Settings → Roles).',
    pool: 'Hidden functions',
    poolHint: 'Functions under "Hidden functions" are not in the menu (they stay in the program: favourites, address): drag them into a group to show them; a function dragged there disappears from the group it was taken from.',
  },
  tabs: { closeAll: 'Close all', closeAllHint: 'Close all open pages, only the Home page stays' },
  empPicker: {
    title: 'Choose an employee', open: 'Choose from the employee list', typeOrPick: 'Type the name / personnel no. or press …',
    search: 'Name, personnel no., IDNP', current: 'Working now', all: 'All', tab: 'No.', name: 'Name',
    occupation: 'Position', status: 'Status', hint: 'Click a row to choose.', hintMany: 'Click a row to add the employee; chosen ones are highlighted.',
    done: 'Done ({{count}})',
  },
  subPicker: { open: 'Choose from the company structure', title: 'Choose a department', hint: 'Click a department to choose.' },
}

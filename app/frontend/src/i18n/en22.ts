// CAI CADRE: all settings in one place — Administration → Settings (alphabetical, with search); the Settings group left the
// sections, and pages with settings tabs were split into separate settings.
export default {
  menu: {
    settings: 'Settings', occupations: 'Positions (CORM)', specialties: 'Specialties', legalBases: 'Legal grounds',
    orderTypes: 'Order types', workSchedules: 'Work schedules', shiftTypes: 'Shifts', productionCalendar: 'Production calendar',
    worktimeSettings: 'Rest between shifts and duties per month', leaveSettings: 'Leave records', payrollTypes: 'Calculation types',
    payrollConstants: 'Payroll constants', taxSettings: 'Tax reports: payer details',
    alertSettings: 'Deadlines and alerts: what is tracked', smtpSettings: 'Mail (e-mail) for notifications and payslips',
  },
  org: { dictKinds: { checklist: 'Hiring / leaving checklist' } },
  settingsPage: {
    hint: 'All program settings, in alphabetical order. Type part of the name to find one; Enter opens the setting when only one is left.',
    search: 'Search a setting by name', none: 'No setting with this name.',
  },
}

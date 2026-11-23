// The "Classic desktop" look: menu bar, toolbar, status bar, windows as tabs.
export default {
  themes: {
    desktop: 'Classic desktop', desktop_dark: 'Classic desktop, dark', onec: 'Like 1C (yellow)', green: 'Fresh green', turquoise: 'Turquoise',
    blue: 'Blue', dark: 'Dark', auto: 'Automatic',
  },
  profile: { companyTheme: 'Company theme ({{theme}})' },
  desk: {
    menuBar: 'Menu bar', toolbar: 'Toolbar', statusBar: 'Status bar', mobileMenu: 'Menu',
    menu: { file: 'File', windows: 'Windows', help: 'Help' },
    tab: { order: 'Order {{number}}', payroll: 'Payroll {{number}}', itemChange: 'Change {{number}}', payment: 'Payment {{number}}', productionReport: 'Report {{number}}' },
    src: { order: 'Order No. {{number}} of {{date}}', change: 'Pay item change No. {{number}} of {{date}}' },
    noFavorites: '(no favorites)', closeWindow: 'Close window', admin: 'Administrator',
    tool: {
      new: 'New', noNew: 'New — the open window has nothing to create',
      save: 'Save', noSave: 'Save — there are no unsaved changes',
      print: 'Print', noPrint: 'Print — the open window has no print form',
      excel: 'Save the list to Excel', noExcel: 'Excel — the open window has no list',
      refresh: 'Refresh the window data', noRefresh: 'Refresh — the window has no data to reload',
      refreshDirty: 'Refresh — save your changes first',
      search: 'Search in the window', noSearch: 'Search — the open window has no search field',
    },
    status: { online: 'Connected', offline: 'No connection to the server', role: 'Role' },
  },
}

// Aspectul „Clasic de birou”: bara de meniu, bara de unelte, bara de stare, ferestrele ca file.
export default {
  themes: { desktop: 'Clasic de birou', desktop_dark: 'Clasic de birou, întunecat' },
  profile: { companyTheme: 'Tema întreprinderii ({{theme}})' },
  desk: {
    menuBar: 'Bara de meniu', toolbar: 'Bara de unelte', statusBar: 'Bara de stare', mobileMenu: 'Meniul',
    menu: { file: 'Fișier', windows: 'Ferestre', help: 'Ajutor' },
    tab: { order: 'Ordinul {{number}}', payroll: 'Calculul {{number}}', itemChange: 'Modificarea {{number}}', payment: 'Îndreptarea {{number}}', productionReport: 'Raportul {{number}}' },
    src: { order: 'Ordinul nr. {{number}} din {{date}}', change: 'Modificarea acumulărilor nr. {{number}} din {{date}}' },
    noFavorites: '(nimic la favorite)', closeWindow: 'Închide fereastra', admin: 'Administrator',
    tool: {
      new: 'Nou', noNew: 'Nou — fereastra deschisă nu are ce crea',
      save: 'Salvează', noSave: 'Salvează — nu sunt modificări nesalvate',
      print: 'Tipar', noPrint: 'Tipar — fereastra deschisă nu are formă de tipar',
      excel: 'Salvează lista în Excel', noExcel: 'Excel — fereastra deschisă nu are listă',
      refresh: 'Reîmprospătează datele ferestrei', noRefresh: 'Reîmprospătează — fereastra nu are date de reîncărcat',
      refreshDirty: 'Reîmprospătează — întâi salvați modificările',
      search: 'Căutare în fereastră', noSearch: 'Căutare — fereastra deschisă nu are câmp de căutare',
    },
    status: { online: 'Conectat', offline: 'Fără legătură cu serverul', role: 'Rolul' },
  },
}

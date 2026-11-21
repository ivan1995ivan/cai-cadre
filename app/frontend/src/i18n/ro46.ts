// CAI CADRE: meniul pe grupe (Registre / Rapoarte / Setări, ca în CRM acoperiș gard), rapoartele ca funcții de meniu,
// „Închide toate” în bara ferestrelor deschise.
export default {
  menu: {
    repMovement: 'Mișcarea cadrelor', repStructure: 'Structura personalului', repSeniority: 'Vechimea în muncă',
    repBirthdays: 'Zile de naștere și jubilee', repRetirements: 'Pensionări', repVacancies: 'Posturi vacante',
    repMunca1: 'Munca 1 (BNS)',
    repLeavePeriod: 'Concediile și absențele pe perioadă', repTimesheetSummary: 'Pontajul consolidat',
    repOrdersPayroll: 'Extrasul din ordine pentru contabilitate', repOrdersByType: 'Ordinele pe tipuri',
    repTrainingPeriod: 'Formarea pe perioadă', repTrainingExpiry: 'Certificatele de formare care expiră',
    repHealthDue: 'Termenele sănătății și securității în muncă',
    repMilitaryRegister: 'Registrul evidenței militare', repMilitaryMissing: 'Fără fișă de evidență militară',
    repMilitaryChanges: 'Modificările lunii pentru centrul militar', repMilitaryRecruits: 'Lista recruților',
  },
  menuGroups: { items: 'Registre', reports: 'Rapoarte' },
  mainMenu: {
    hint: 'Secțiunile meniului și, în fiecare, grupele Registre / Rapoarte, ca în 1C (setările nu stau în secțiuni: toate sunt la Administrare → Setări). Trageți cu mouse-ul o funcție în altă grupă sau secțiune, ori mai sus / mai jos; aceeași funcție poate sta în mai multe locuri. Secțiunile se mută la fel; alegeți una ca s-o redenumiți sau să-i schimbați iconița. Cine ce vede — bifele de la fiecare rol (Administrare → Setări → Roluri).',
    pool: 'Funcții neafișate',
    poolHint: 'Funcțiile de la „Funcții neafișate” nu sunt în meniu (rămân în program: din favorite sau după adresă): trageți-le într-o grupă ca să apară; o funcție trasă acolo dispare din grupa de unde a fost luată.',
    icons: { home: 'Principal', org: 'Instituția', crm: 'Angajați', orders: 'Ordine', calendar: 'Calendar', wallet: 'Salariu', training: 'Formare', reports: 'Rapoarte', admin: 'Administrare', star: 'Stea', folder: 'Dosar' },
  },
  tabs: { closeAll: 'Închide toate', closeAllHint: 'Închide toate paginile deschise și rămâne doar Pagina de start' },
  empPicker: {
    title: 'Alegerea angajatului', open: 'Alege din lista angajaților', typeOrPick: 'Scrieți numele / nr. de tabel sau apăsați …',
    search: 'Numele, nr. de tabel, IDNP', current: 'Lucrează acum', all: 'Toți', tab: 'Nr. tabel', name: 'Numele, prenumele',
    occupation: 'Funcția', status: 'Starea', hint: 'Clic pe rând = alege.', hintMany: 'Clic pe rând adaugă angajatul; cei aleși sunt evidențiați.',
    done: 'Gata ({{count}})',
  },
  subPicker: { open: 'Alege din structura instituției', title: 'Alegerea subdiviziunii', hint: 'Clic pe subdiviziune = alege.' },
}

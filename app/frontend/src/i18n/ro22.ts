// Facturile de servicii primite (chirie, transport, comunale, telefonie): fără stoc, cu articolul de cheltuială.
const ro22 = {
  services: {
    title: 'Facturi de servicii', one: 'Factura de servicii', new: 'Factură de servicii nouă',
    hint: 'Facturile furnizorilor pentru servicii — chirie, transport, comunale, telefonie, reparații, publicitate. Nu intră în stoc: fiecare rând primește articolul de cheltuială. Înregistrată, factura devine datorie față de furnizor (cu scadența din contract), iar plata ei intră în cash flow pe articolele rândurilor. Se fac de mână, din poză / PDF sau din „Facturi primite” → „Servicii”.',
    all: 'Toate', statuses: { draft: 'Ciornă', posted: 'Înregistrată' },
    search: 'Număr, furnizor, serviciu', category: 'Articolul de cheltuială', categories: 'Articole', categoryForAll: 'Articolul pentru toate rândurile',
    lines: 'Serviciile', service: 'Serviciul', unit: 'U.m.', price: 'Prețul', vat: 'TVA', choose: 'Alegeți articolul',
    addLine: 'Adaugă rând', net: 'Fără TVA', vatSum: 'TVA', total: 'Suma cu TVA', paid: 'Plătit', rest: 'De plătit',
    pay: 'Plătește', posted: 'Factura e înregistrată: datoria față de furnizor e în „Cui plătesc”.',
    postConfirm: 'Înregistrați factura? Devine datorie față de furnizor; rândurile trebuie să aibă articolul de cheltuială.',
    unpostConfirm: 'Anulați înregistrarea? Factura iese din datorii și din cheltuieli; plățile legate rămân, ca avans la furnizor.',
    rateHint: 'Gol sau 1 = cursul BNM din ziua facturii',
    dueHint: 'Gol = data facturii + termenul din contract',
    supplierMissing: 'Furnizorul {{name}} (IDNO {{idno}}) nu e în listă: adăugați-l în Furnizori, apoi alegeți-l.',
    paymentHint: 'Plata se împarte în cash flow pe articolele facturii',
    inAccounting: 'Trecută în 1C',
  },
  accounting1c: {
    title: 'Contabilitatea 1C (Contabilitatea pentru Moldova)',
    hint: 'Prelucrarea externă „Încărcare din CAI ERP” trece în 1C facturile emise, intrările de marfă, facturile de servicii, încasările și plățile (bancă, casă) — doar când contabilul vrea: alege perioada, vede lista cu bife (ce e deja în 1C nu se bifează) și transferă ce a bifat. Terții se caută după IDNO, mărfurile după cod; ce lipsește se creează. În program fiecare factură ține minte în ce document din 1C a ajuns.',
    how: 'În 1C: Fișier → Deschide → IncarcareCAIERP.epf. În „Setări” scrieți adresa de mai jos, utilizatorul și parola din CAI ERP (utilizatorul trebuie să vadă facturile), apoi „Verifică legătura”.',
    address: 'Adresa programului', download: 'Descarcă prelucrarea (.epf)',
  },
}
export default ro22

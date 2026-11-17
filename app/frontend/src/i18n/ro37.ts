// CAI CADRE — declarațiile electronice XML (IPC21, IALS21, IRM19) după schemele SFS.
export default {
  pay: { ex: { spouseIdnp: 'IDNP-ul soțului / soției', spouseIdnpHint: 'Pentru IALS21 (col. 4), la scutirea pentru soț / soție (Sm).' } },
  tax: {
    exportXml: 'Declarația XML (SFS)', xmlHint: 'Fișierul XML după schema oficială, pentru încărcarea în SFS (e-Cabinet / declarații electronice).',
    headerMissing: 'Lipsesc datele din antetul declarației: {{list}} — completați-le în Administrare → Setări → Raportări fiscale: datele plătitorului (și IDNO în Constante).',
    missingCode: '{{count}} persoane fără codul funcției (CORM) — completați-l în Administrare → Setări → Funcții (CORM); în IPC21 e obligatoriu.',
    table1: 'Tabelul nr.1 — plăți salariale (cod 11, SAL)', table2: 'Tabelul nr.2 — evidența nominală a asiguraților',
    period: 'Perioada', occupationCode: 'Codul funcției', spouseIdnp: 'IDNP soț / soție',
    irmCategory: 'Categoria', irmCode: 'Cod raport', irmReason: 'Motivul',
    dependents: 'Persoane întreținute în anexă: {{count}}.',
    cols: { base: 'Baza de calcul CAS', sick: 'Indemnizația (boală)', P: 'P', M: 'M', Sm: 'Sm', N: 'N', H: 'H' },
    ipcHint: 'Declarația lunară (până la 25 a lunii următoare), din calculele aprobate: tabelul 1 (SAL), anexa pe CUATM, tabelul 2 pe persoane și categorii — 101 CIM, 123 cumul extern, 105 contract civil, 160 concediu de odihnă, 15311 boala plătită de angajator, 157 / 158 / 159 / 165 concediile neplătite și sociale; rândul 1.1 b) tariful 24 % (instituții medico-sanitare).',
    ialsHint: 'Nota de informare anuală (până la 25 ianuarie): venitul anului, scutirile pe coduri P / M / Sm / N / H (din cererile de scutire), CNAM și impozitul; suma de control = totalul impozitului; anexa cu persoanele întreținute.',
    irmHint: 'Înscrierile din ordinele semnate: col. 8 — 01 angajare pe nedeterminat, 05 pe determinat, 02 încetare (col. 9 motivul: 113–116), 03 suspendare, 04 reluare; col. 5–7 — 157 / 158 îngrijirea copilului, 165 concediu paternal. Se depun în 10 zile lucrătoare (termenul depășit — cu roșu).',
    set: {
      hint: 'Datele din antetul declarațiilor electronice. Denumirea, IDNO, directorul și contabilul-șef se iau din Constante.',
      cnas_code: 'Codul CNAS (al plătitorului)', cnasHint: 'Semnul convențional de înregistrare atribuit de CNAS (până la 7 cifre).',
      sfs_code: 'Codul Serviciului Fiscal de Stat', sfsHint: 'Subdiviziunea SFS care vă deservește (2 semne).',
      cuatm: 'Codul localității (CUATM)', cuatmHint: 'Codul sediului (4 semne), după clasificatorul CUATM.',
      caem: 'Codul genului principal de activitate (CAEM)', caemHint: 'Codul din patru cifre; de regulă 8610 pentru spitale.',
      email: 'E-mail de contact', phone: 'Telefon de contact', income_source: 'Codul sursei de venit',
    },
  },
}

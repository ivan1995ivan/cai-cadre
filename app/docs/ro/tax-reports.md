# Raportări (IPC21, IALS21, IRM19)

Raportările se fac din **îndreptările spre plată achitate** (venitul achitat și impozitele reținute: IPC21 tabelul 1,
IALS21), din **calculele aprobate** (baza CAS: IPC21 tabelul 2) și din **ordinele semnate** (IRM19). Fiecare are
previzualizarea pe ecran, **exportul Excel** (pentru verificare) și **declarația XML** după schema oficială a Serviciului
Fiscal de Stat, gata de încărcat în SFS. Sus apar avertismentele: date lipsă în antet, persoane fără IDNP, funcții fără cod
CORM.

**Datele plătitorului** (o dată, la pornire; *Administrare → Setări → Raportări fiscale: datele plătitorului*): codul CNAS al plătitorului, codul subdiviziunii SFS, CUATM (4 semne), e-mailul și telefonul de contact. Denumirea, IDNO, **codul CAEM**, conducătorul și contabilul-șef se iau
din [Constante](help:admin/constants).

**IPC21** (lunar, până la 25 a lunii următoare):
- tabelul 1: codul 11 „SAL” — venitul achitat în lună, impozitul și primele CNAM reținute (din îndreptările achitate în
  lună, după data achitării); codul 61 — totalul; suma de control;
- anexa la tabelul 1: impozitul din salarii pe CUATM;
- tabelul 2, pe fiecare persoană și categorie (clasificatorul CNAS): **101** CIM (inclusiv cumulul intern), **123** cumul
  extern, **105** contract civil (prestări servicii), **160** concediu de odihnă (cu indemnizația de concediu), **16011**
  concediu de studii, **16012** concediu suplimentar, **159** concediu neplătit, **157 / 158** îngrijirea copilului,
  **165** concediu paternal, **15311** indemnizația de boală plătită de angajator; perioada, tariful (24 %), codul funcției
  (CORM — obligatoriu), baza de calcul, indemnizația, CAS;
- rândul 1.1 b) „conform tarifului de 24 %” (angajatorii din sectorul privat).

**IALS21** (anual, până la 25 ianuarie): pe persoane — IDNP, IDNP-ul soțului / soției (dacă are scutirea Sm), codul sursei
(SAL), venitul achitat în an (din îndreptările achitate), scutirile pe coduri **P** (personală), **M** (majorată), **Sm** (pentru soț / soție), **N**
(întreținuți), **H** (întreținuți cu dizabilități), CNAM și impozitul; suma de control = totalul impozitului; anexa cu IDNP-urile
persoanelor întreținute. Scutirile se împart pe coduri după cererea de scutire a angajatului (fila „Salariu”): scutirea
fiecărei plăți — după scutirile valabile în luna pentru care s-a plătit (P sau M până la renunțare, Sm, fiecare întreținut
din luna următoare apariției dreptului). Anexa are codul fiscal al fiecărui întreținut la N sau la H; codul fiscal al soțului
(col. 4) — doar cu Sm. **IPC21**: baza minimă CAS (diferența până la salariul minim) intră în baza de calcul CAS a persoanei
(col. 9); indemnizația pentru accident de muncă din zilele angajatorului — categoria 15321.

**IRM19** (în 10 zile lucrătoare de la ordin): col. 8 — **01** angajare pe durată nedeterminată, **05** pe durată determinată,
**02** încetare, **03** suspendare, **04** ridicarea suspendării; col. 9 — motivul eliberării (**114** demisie, **113**
reducere, **115** încetarea CIM, **116** alte temeiuri; se poate schimba pe motiv în *Administrare → Setări → Motivele încetării CIM*, câmpul „irm19”); col. 5–7 —
**157** / **158** îngrijirea copilului, **165** concediu paternal, cu perioada. Termenul depășit apare cu roșu.

Drepturile: „Raportări fiscale” — vizualizare și export (contabilitatea are tot; inspectorul de cadre nu are).


**Regimul IT Park** (vezi [Regimul IT Park](help:payroll/it-park)): **IPC21** are bifa „Rezidentul parcurilor IT”
(`table1/it/flag1`), tabelul 1 fără salariile impozitate final, iar în tabelul 2 angajații cu CIM au venitul asigurat de
11 832 lei (categoria **162**, cu **160** / **15311** după zile, **159** doar pe toată luna neplătită; tariful și CAS 0).
**IU17** (lunar, până la 25) — fila IU17: rândurile 010 (venitul × 7 %), 020 (angajații × 30 % din salariul mediu), 030
(cel mai mare), Excel și tipar; venitul din vânzări îl scrie contabilul în *Salarizare → Impozitul unic IT Park*.
**ISAPTI17** (anual, până la 25 ianuarie) — fila ISAPTI17: salariul din regim achitat în an și lunile în regim, Excel și
tipar; tot acolo **nota anuală pentru angajat** (anexa 5, până la 1 martie). **IALS21** și **anexa 8** cuprind doar plățile
din regimul general. Pentru IU17 și ISAPTI17 nu avem schema XML oficială — se depun după Excel / tipar.

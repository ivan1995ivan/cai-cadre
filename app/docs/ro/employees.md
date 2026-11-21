# Angajați (dosarul personal)

Lista arată angajații în funcție; filtrele schimbă starea (activi, cu CIM suspendat, eliberați, arhivați), subdiviziunea
(cu sub-secțiile ei), categoria de personal și tipul angajării. Coloanele se aleg din rotița din dreapta tabelului
(IDNP, data nașterii, telefonul sunt ascunse implicit); butonul Excel exportă lista cu filtrele puse.

**Fișa scurtă**: țineți mouse-ul o clipă pe numele angajatului — apare fotografia, data nașterii și vârsta, raporturile de
muncă (funcția, subdiviziunea, norma, de când), vechimea în întreprindere, totală și în specialitate, absența de azi (concediu, boală), concediul disponibil, contactele și mărimile echipamentului. Fișa
scurtă nu se scrie în jurnalul accesului; datele sensibile se ascund după aceleași drepturi ca în dosar.

## Fișa angajatului

- **Date personale** — persoana: numele, IDNP, nașterea, cetățenia, contactele, codurile CNAM / CPAS, IBAN-ul. Fotografia
  se încarcă cu clic pe avatar. La sfârșit — **echipamentul de lucru**: mărimea îmbrăcămintei (44, 46, 48… sau S, M, L),
  a încălțămintei și înălțimea; raportul *Angajați → Rapoarte → Mărimile echipamentului de lucru* le adună pe secții, cu
  numărul de bucăți din fiecare mărime (pentru comanda halatelor și a încălțămintei). Se pot importa și din Excel.
- **Raporturi de muncă** — de bază, cumul intern / extern, suplinire, contract de prestări servicii. Fiecare are istoricul lui: ce funcție,
  secție, normă și salariu a avut din fiecare dată și prin ce ordin. *Modificare* adaugă o înregistrare în istoric (cu dată
  în viitor intră în vigoare singură); *Suspendare* / *Reluare* — pentru concediul de îngrijire a copilului, serviciul
  militar etc.; *Încetare* — eliberarea, cu motivul. Creionul este doar pentru greșeli de introducere.
- **Acte** — buletin, pașaport, diplome, certificate (cu termen de valabilitate) și scanările lor.
- **Familia**, **Studii și formare** (studiile și [formarea profesională](help:training) — cursurile, instruirile,
  certificatele cu termen), **Vechimea** (stagiul anterior + vechimea calculată: totală, în specialitate — stagiul bifat „În
  specialitate” și munca de aici —, în întreprindere), **Sănătate și SSM**, **Evidența militară** (doar cu modulul pornit,
  [Evidența militară](help:military)).
- **Salariu** (cine vede salarizarea) — [cererea de scutire](help:payroll/exemptions) cu persoanele întreținute, sporurile și
  reținerile personale, fișa personală anuală (anexa 8). Raportul de muncă cu salariul de funcție sub salariul minim pe țară
  arată avertismentul „sub salariul minim” (la calcul se adaugă completarea până la minim).
- **Angajare / eliberare** — lista de verificare: ce s-a semnat și primit la angajare, ce s-a predat la plecare.
- **Jurnalul accesului** — cine a deschis, tipărit sau exportat dosarul.

**Tipar:** fișa personală (MR-2), adeverința de la locul de muncă, adeverința de vechime și **adeverința privind
salariul (pentru bancă)** — cu numărul din seria „Adeverință” și câmpul *Se eliberează pentru* (de ex. banca). Numărul se ia
la **Tipărește**, nu la previzualizare: încercările nu consumă numere din registru.

**Adeverința privind salariul** (o tipărește cine vede salarizarea): datele angajatului (IDNP, funcția, din ce dată, felul
contractului, salariul de funcție), apoi pe fiecare lună a perioadei — calculat (brut), prima CNAM, impozitul pe venit,
alte rețineri și salariul net, cu **totalul** și **media lunară**; reținerile lunare din salariu (sindicat, pensie
alimentară, împrumut — media pe lună), scopul, textul de la sfârșit (se schimbă în șablonul de tipar), semnăturile
directorului și ale contabilului-șef, L.Ș. **Perioada** se alege jos, lângă *Se eliberează pentru*: **ultimele 3, 6 sau 12
luni** (până la ultima lună cu calcul aprobat — dacă luna trecută nu e aprobată încă, perioada are tot atâtea luni de
salariu) sau **un interval de luni** ales. Lunile fără calcul aprobat nu apar în tabel.

Datele sensibile (IDNP, acte, sănătate) le văd doar rolurile cu dreptul „Date sensibile”; salariul îl ascund rolurile
care au câmpul „Salariul” ascuns. Șeful de subdiviziune vede doar angajații subdiviziunilor lui (Întreprinderea → subdiviziunea →
utilizatorii ei).

**Mai multe raporturi de muncă:** un angajat poate lucra în mai multe secții și pe mai multe funcții deodată — de bază,
cumul intern / extern, suplinire sau **contract de prestări servicii** (contract civil: nu ocupă post în statele
de personal, nu dă drept la concediu și nu intră în vechimea în muncă). Fiecare raport are secția, funcția și **norma în
procente** (100%, 50%, 25%; în statele de personal se socotește în unități: 0,5, 0,25) și **remunerarea lui**: modalitatea
(salariu lunar, tarif orar, pe tipuri de ore, mixt), salariul sau tariful orar, **tarifele pe tipuri de ore** cu orele
garantate și **funcțiile exercitate în plus pe același contract** — cumularea funcțiilor, suplinirea, interimatul (CM art.
156), cu plata lor (% din salariul propriu sau al funcției cumulate, sumă fixă, pe ore). Cumulul (intern / extern) e raport
separat; cumularea funcțiilor nu e. Vezi *Tipuri de ore, tarife pe funcție și orele garantate*. La importul din Excel norma
se poate scrie 0,5 sau 50%; coloana „Cumularea funcțiilor (% din salariul propriu)” face înregistrarea de cumulare a
raportului.

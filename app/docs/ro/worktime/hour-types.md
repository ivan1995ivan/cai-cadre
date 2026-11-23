# Tipuri de ore, tarife pe funcție și orele garantate

*Administrare → Setări → Tipuri de ore.* Pe lângă orele standard din grafic, pontajul are **orele pe tipuri**: instruire,
examinare, zbor, rezervă, staționare, conducere… Fiecare tip are **tariful lui pe oră** pe raportul de muncă (pe funcție) și,
dacă e scris în contract, **orele garantate pe lună**. Datele se pun o singură dată — în ordin sau în fișă — și trec singure în
pontaj, în calculul salariului și în rapoarte.

## Pentru omul de la ecran

**1. Remunerarea raportului de muncă** (fișa → *Raporturi de muncă*, pe fiecare raport). Antetul raportului arată pe scurt
cum se plătește: „De bază: Pilot — salariu + tarife: ZBOR, INSTR”, „Cumulare: Instructor de zbor — 30 %”, „Cumul intern:
Examinator — tarif orar”. Dedesubt:
- **modalitatea de remunerare** (cu istoric „din data”, ca salariul):
  - *Salariu lunar* — salariul de funcție pro-rata la orele lucrate;
  - *Tarif orar* — tariful orar de bază × toate orele lucrate (suplimentarele și sărbătorile — sporul peste ora simplă);
  - *Pe tipuri de ore* — fără salariu lunar: doar orele pe tipuri × tarifele lor;
  - *Mixt* — salariul lunar plus tarifele pe tipurile de ore;
- **tarifele pe tipuri de ore**: tipul, lei pe oră, orele garantate pe lună (pot lipsi), de la / până la, sursa (ordinul);
- **funcțiile exercitate în plus pe același contract** — cumularea funcțiilor, suplinirea, interimatul (vezi mai jos).

Tarifele se plătesc doar la *Pe tipuri de ore*, *Mixt* și *În acord* (vezi *Producția: salarizarea în acord*); la celelalte modalități programul nu le primește (și nu lasă
schimbarea modalității cât timp există tarife în vigoare — opriți-le în același ordin).

**2. Ordinul.** În ordinele de angajare, de modificare a salariului / condițiilor și de cumul cu raport separat sunt câmpurile
*Modalitatea de remunerare*, *Tariful orar* și tabelul **„Tarife pe tipuri de ore”**: *adaugă* / *modifică* / *oprește*,
tipul, tariful, orele garantate, de la (gol — data ordinului) / până la, temeiul. La angajare tabelul se completează singur din
**tarifele-tip ale funcției** (clasificatorul funcțiilor, butonul cu portmoneul). La semnare rândurile intră pe raport, iar
anularea ordinului le scoate. Textul punctului le arată: „Tarife pe tipuri de ore: se stabilește tariful pentru ore de zbor —
350 lei pe oră, garantat 50 ore pe lună”.

**3. Pontajul.** Tabela are câte o coloană pentru tipurile de ore cu tarif pe raporturile din tabelă, pentru tipurile scrise
deja și pentru tipurile bifate „Coloană pentru toți”. Orele standard vin din grafic, ca înainte; **orele pe tipuri** se scriu:
- de mână — clic pe celulă: *pe zile* (dacă tipul permite) sau *total pe lună*; „Scoate orele” le șterge;
- din **Excel** — butonul „Ore pe tipuri din Excel”: nr. de tabel, raportul de muncă (doar la angajații cu mai multe
  raporturi în tabelă: funcția, „Cumul intern” sau numărul raportului), codul tipului, ziua (gol — total pe lună), orele;
  întâi se încearcă (se văd rândurile cu erori), apoi se importă.

Celula arată orele efective, iar dedesubt garanția: „gar. 40,91” sau, când garanția trece peste orele efective, „→ 40,91
(gar.)”. Treceți cu mouse-ul — **garantat / zile disponibile / efectiv / de plată** și explicația. Orele pe tipuri rămân la
„Recalculează” și la „Recalculează tot”. Tiparul și exportul Excel au coloanele tipurilor (efective, garantate, de plată) și
foaia „Ore pe tipuri” pe zile.

**4. Orele garantate sunt un minim plătit.** Se plătesc **max(orele efective, orele garantate)**:
- garantat 50, efectiv 34 → se plătesc **50**;
- garantat 50, efectiv 54 → se plătesc **54**.

Garanția lunii **se reduce proporțional** cu zilele lucrătoare (calendarul de producție) în care raportul nu e „disponibil”:
- zilele în care raportul nu există încă sau a încetat (angajare / eliberare în mijlocul lunii) și zilele în care tariful nu
  e în vigoare;
- zilele de **absență** din setare — implicit concediul de odihnă (se plătește din medie, care cuprinde deja orele), concediul
  suplimentar, neplătit, de studii, zilele libere plătite, boala, maternitatea / paternitatea, îngrijirea copilului;
- zilele de **suspendare** a contractului.

**Deplasarea și formarea profesională nu reduc garanția** — sunt muncă. Exemple (luna cu 22 de zile lucrătoare, garantat 50):
- angajat la 11 ale lunii (15 zile lucrătoare din 22): 50 × 15 / 22 = **34,09**; efectiv 20 → se plătesc 34,09;
- 5 zile de concediu de odihnă: 50 × 17 / 22 = **38,64**; efectiv 30 → se plătesc 38,64; o deplasare de 5 zile — fără reducere.

Explicația din calcul arată totul: „ZBOR: garantat 50 × 17 / 22 zile disponibile (5 zile C) = 38,64; efectiv 30 → plătit
38,64 × 300 lei = 11 592 lei”. Dacă tariful s-a schimbat în lună, orele scrise pe zile merg la tariful zilei lor, iar totalul pe
lună se împarte între tarife după zilele fiecăruia; garanția fiecărui tarif se socotește pe zilele lui.

**5. Calculul salariului.** Tipul de calcul automat **„Ore pe tipuri”** (ORE): un rând pe fiecare tip de ore cu tarif — ore
plătite × tariful, cu explicația garanției. Un tip de ore poate avea tipul lui de calcul (în clasificator: *Se plătește cu tipul
de calcul* — un tip automat „Ore pe tipuri”, de ex. „Plata orelor de zbor” cu contul lui contabil). Plata pe ore intră în media
pentru concediu și boală după bifa „Intră în salariul mediu” a tipului de calcul (ORE — da) și în completarea până la salariul
minim (e salariu tarifar al timpului lucrat, nu spor).

**Ce intră în orele lucrate** (coloana *Legătura cu orele lucrate* a tipului):
- *O parte din program* (implicit; instruirea, examinarea, zborul făcute în timpul programului) — orele sunt deja în orele
  standard din grafic: nu se adună a doua oară, nu fac suplimentare, nu schimbă partea lucrată din normă; dacă sunt mai multe
  decât orele lucrate ale liniei, pontajul avertizează;
- *Se adaugă la orele lucrate* — timp de muncă peste orele standard: intră în orele lucrate (`OreLucrate`) și în partea lucrată
  din normă (deci și în baza minimă CAS); suplimentarele nu se socotesc singure din ele — orele suplimentare se scriu în celula
  zilei;
- *Nu e timp de muncă* (rezerva acasă, disponibilitatea) — doar se plătește tariful.

Orele pe tipuri **nu intră în tariful orar** pentru noapte, sărbători și suplimentare: acelea se socotesc din orele standard ale
pontajului. Sporurile proprii pe orele de zbor (noapte, sărbători) — cu formula (mai jos); regulile aviației vin în etapa
următoare.

**6. Formule.** În formula unui tip de calcul (*Tipuri de calcul → Formulă*): `Ore.COD` — orele efective din pontaj,
`OrePlatite.COD` — max(efective; garantate reduse), `Garantat.COD` — garanția redusă a lunii (0 fără garanție),
`Tarif.COD` — tariful pe oră în vigoare la sfârșitul lunii. De ex. `OrePlatite.ZBOR * Tarif.ZBOR * 0,1` sau
`Ore.INSTR * 20`. Un cod de tip de ore care nu există e eroare la salvare. În editor: alegeți tipul de ore și clic pe variabilă.

## Cumulul ≠ cumularea funcțiilor

- **Cumulul** (intern / extern, CM — capitolul „Munca prin cumul”, art. 267 și urm.; de verificat numerotarea în redacția în
  vigoare) e un **raport de muncă separat**: CIM, normă, salariu sau tarife proprii, pontaj propriu, linie proprie în calcul.
- **Cumularea funcțiilor (profesiilor), suplinirea salariatului temporar absent și interimatul** în cadrul aceluiași contract,
  fără eliberare de la munca de bază (**CM art. 156**), **nu** sunt raporturi separate: sunt înregistrări pe raportul de bază,
  cu plata lor: **% din salariul funcției proprii**, **% din salariul funcției cumulate / suplinite** (salariul ei, luat din
  raportul celui suplinit sau scris în ordin), **sumă fixă pe lună** sau **pe ore cu tarif** (orele unui tip de ore din
  pontaj). Plata e tipul **„Plata pentru cumularea funcțiilor / suplinire”** (CUMUL): % × salariu × partea lucrată × zilele
  lucrătoare ale cumulării din lună / zilele raportului; suma fixă × aceleași zile; pe ore — orele × tariful.

Ordinele *Cumul de funcții*, *Suplinire temporară*, *Interimat* au câmpul **„Cum se exercită”**:
- *Pe același contract (CM art. 156)* — implicit: înregistrarea pe raportul de bază; cu *„Încheie mai devreme”* ordinul
  încheie o cumulare / suplinire existentă la data dată;
- *Raport de muncă separat* — pentru omul care face munca celuilalt **cu pontaj separat** (în afara programului de bază sau
  pe un post vacant, cu CIM pe durată determinată): raport nou (cumul intern / suplinire) cu norma, salariul / tarifele și
  pontajul lui, ca la cumul.

De ce așa: clientul vrea „modalitatea de remunerare și salariul pentru fiecare funcție, independent de clasificarea ei ca
raport de muncă” — înregistrarea pe raportul de bază dă fiecărei funcții plata ei fără un raport fals (fără normă dublă în
statele de personal, fără salariu de funcție plătit a doua oară), iar munca cu pontaj propriu rămâne raport separat, cu tot
ce are un raport. Încetarea raportului de bază sau a celui suplinit încheie cumularea; anularea ordinului o scoate sau o
redeschide.

## Pentru cine configurează

- *Setări → Tipuri de ore*: codul (litere latine, cifre, „_” — în formule `Ore.COD`), denumirile RO / RU / EN, grupa,
  legătura cu orele lucrate, *Se introduc* (pe zile sau doar total pe lună), profilul (general / fabrică / aviație /
  transport), *Coloană pentru toți* (coloana apare în pontajul tuturor), tipul de calcul cu care se plătește. Livrate: INSTR,
  EXAM; tipurile aviației, fabricii și transportului le aduc profilurile lor; ale dvs. (de ex. ZBOR) se adaugă aici.
- *Setări → Funcții (CORM)*, butonul cu portmoneul: **tarifele-tip pe tipuri de ore** ale funcției (completează ordinul de
  angajare).
- *Setări → Odihna între ture și turele de noapte pe lună*: **absențele care reduc orele garantate** și bifa pentru
  suspendare (implicit: toate concediile și boala, plus suspendarea).
- Datele vechi: „Plata pentru cumul (%)” de pe raport (versiunile de dinainte) s-a mutat singur în înregistrări de cumulare
  („% din salariul funcției proprii”, pe perioadele din istoric), cu aceleași sume; tipul CUMUL e redenumit.

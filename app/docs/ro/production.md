# Producția: salarizarea în acord

*Modul opțional, pentru fabrici și ateliere.* Lucrările făcute în acord (bucăți, operații, produse) se scriu în **rapoartele de
producție**, individuale sau pe brigadă. Raportul aprobat intră singur în calculul salariului lunii lui: suma lucrărilor,
rebutul plătit după vinovat (CM art. 162), sporul acordului progresiv peste normă și, pentru brigadă, partea fiecărui membru.

## Pentru omul de la ecran

**1. Raportul de producție** (*Salarizare → Rapoarte de producție*). Lista arată rapoartele lunii alese: numărul, data, felul,
starea, angajații / brigada, suma și orele normate; jos — totalul aprobat în lună. Butoanele **„Raport individual”** și
**„Raport pe brigadă”** deschid un raport nou (seria **RP**).

În antet:
- **data** — raportul intră în calculul salariului **lunii acestei date**, iar tarifele se iau pe cele în vigoare la ea;
- **felul**: *individual* (fiecare rând are angajatul lui) sau *pe brigadă* (rândurile n-au angajat, suma se împarte membrilor);
- **brigada** (la raportul pe brigadă), **secția / atelierul**, observațiile.

**Lucrările** — câte un rând pe lucrare:
- la raportul individual: **angajatul** și **raportul lui de muncă** (la un singur raport activ se alege singur);
- **lucrarea** (din *Lucrările în acord*) și **cantitatea bună**;
- **rebutul**, pe vinovați (CM art. 162):
  - *r.f.v.* — rebut **fără vina lucrătorului**: se plătește ca produsul bun;
  - *r.p.* — rebut **parțial din vina lucrătorului**: se plătește la procentul din contractul colectiv — câmpul „%” apare
    când scrieți cantitatea, și e obligatoriu;
  - *r.v.* — rebut **total din vina lucrătorului**: nu se plătește;
- **orele lucrate** efectiv la lucrare (la raportul individual): din ele se socotește **îndeplinirea normei**; la lucrările
  progresive sunt obligatorii; goale — se iau orele lucrate din pontaj;
- observațiile.

La **salvare** fiecare rând își socotește suma și orele normate și le arată lângă el (treceți cu mouse-ul — explicația:
„510 bucăți × 12 + rebut parțial 20 × 12 × 50 % = 6 240 lei; categoria 3 (G1) 48 lei/oră × norma de timp 0,25 ore”). Sus
apare lista **„De corectat înainte de aprobare”**: rebutul parțial fără procent, lucrarea fără normă, rândul fără angajat,
lucrarea progresivă fără ore, raportul de muncă încetat la data raportului. Jos — totalul: suma, orele normate, orele lucrate.

**Membrii brigăzii** (la raportul pe brigadă): angajatul și raportul de muncă, **orele lucrate** în lună la brigadă și
**KTU** — coeficientul de participare la muncă. **„Completează din brigadă”** pune membrii brigăzii la data raportului, cu
KTU-ul lor și cu orele din tabela de pontaj a lunii (dacă există); membrii scriși deja rămân. După salvare fiecare membru își
vede partea: suma, orele normate și, la împărțirea „după tarif”, tariful lui orar. Suma brigăzii se împarte **după ore × KTU**
(sau după ore × tariful orar × KTU); bănuții rămași din rotunjire merg la membrul cu ponderea cea mai mare, ca totalul să fie
exact.

**Din Excel.** „Lucrări din Excel”: nr. de tabel (la raportul individual; la cel pe brigadă — gol), raportul de muncă (doar la
angajații cu mai multe raporturi: funcția, „Cumul intern” sau numărul raportului), codul lucrării, cantitatea bună, rebutul
(fără vină, parțial și procentul lui, din vină), orele, observațiile. „Membri din Excel” (la raportul pe brigadă): nr. de tabel,
raportul de muncă, orele, KTU (gol — cel din brigadă). Întâi se încearcă (se văd rândurile cu erori), apoi se importă;
rândurile se **adaugă** la raport, iar membrul existent primește orele și KTU-ul din fișier. Șablonul se descarcă din fereastra
importului.

**Aprobarea.** „Aprobă” verifică totul încă o dată (orice problemă oprește aprobarea) și **fixează tarifele** pe rânduri: o
schimbare ulterioară a normelor sau a grilei nu mai schimbă raportul aprobat. Raportul aprobat nu se modifică; **„Anulează
aprobarea”** îl readuce la ciornă (cu dreptul de aprobare) — doar cât calculul salariului lunii lui, pentru acești angajați,
nu e aprobat (altfel: redeschideți întâi calculul). După orice aprobare / anulare recalculați luna în *Calculul salariului*.

**Tiparul** — forma „Raport de producție”: lucrările cu cantitățile, rebutul, orele, tariful, orele normate și suma, apoi
împărțirea între membrii brigăzii, semnăturile (maistrul / brigadierul, controlul calității, contabilul-șef); textele se schimbă
în *Setări → Șabloane de tipar*.

**2. În calculul salariului.** Pe fiecare raport de muncă:
- **ACORD — „Salarizarea în acord”**: suma lucrărilor din rapoartele aprobate ale lunii (individuale + partea din brigăzi),
  cu orele normate ca și cantitate; explicația trimite la rapoarte și arată **îndeplinirea normei** = orele normate / orele
  lucrate × 100 (orele din rapoarte, dacă toate rândurile le au, altfel orele lucrate din pontaj);
- **ACORDP — „Acord progresiv”**: pe lucrările marcate „progresiv”, producția peste normă primește sporul treptelor (de ex.
  îndeplinirea 125 %, treptele 100:50 și 110:100 → (110 − 100) / 125 din suma progresivă × 50 % + (125 − 110) / 125 × 100 %);
- la modalitatea **„În acord”**: fără salariul de funcție; **suplimentarele** — doar sporul (+50 % primele 2 ore, +100 %
  următoarele) din **tariful orar al categoriei** din raportul de muncă (CM art. 157); **noaptea** — din același tarif;
  **sărbătorile** — încă o dată câștigul în acord pe oră (dublul tarifelor în acord, CM art. 158); **completarea până la
  salariul minim** compară salariul minim × norma × partea lucrată cu suma acordului (fără sporuri și fără ACORDP);
- concediul și boala iau ACORD și ACORDP în medie; sindicatul și pensia alimentară livrate le au în bază.

Raportul de muncă **„În acord”** se pune ca orice remunerare: în ordinul de angajare / de modificare a salariului sau în fișă
(*Raporturi de muncă*), cu **tariful orar al categoriei** — obligatoriu la această modalitate. Tarifele pe tipuri de ore
(de ex. orele lucrate în regim de timp) se plătesc și la „În acord”. Un angajat cu salariu lunar care are lucrări în rapoarte
primește și ACORD, peste salariu.

În formule: `[ACORD]` (suma lucrărilor), `OreNormate`, `OreAcord` (orele din care se socotește îndeplinirea),
`IndeplinireNorma` (%) — de ex. un premiu pentru norma depășită:
`daca(IndeplinireNorma >= 105; [ACORD] * 10 / 100; 0)`.

## Pentru cine configurează

**Pornirea.** *Administrare → Setări → Constante → Module → „Modulul Producția (salarizarea în acord)”*. Oprit (implicit),
rapoartele, setările producției și API-ul lor nu apar, iar drepturile `production.*` nu se dau nimănui. Modulul face parte
din livrarea cu salariu. Drepturile — în *Roluri*: „Producția: salarizarea în acord” (vizualizare, creare, editare, ștergere,
aprobare, export; cu filtrul „doar subdiviziunea mea”); setările producției le schimbă cine are *editare*. Rolurile livrate:
contabilitatea — tot; directorul — vizualizare și aprobare; șeful de subdiviziune (maistrul) — completarea rapoartelor, doar
pentru subdiviziunea lui; șeful resurse umane — vizualizare.

**Grila tarifară** (*Setări → Grila tarifară*, CM art. 130, 170): codul (de ex. G1), denumirea, **în vigoare din**, **tariful
categoriei I** (lei/oră) și **categoriile**: coeficientul față de categoria I sau tariful scris direct. O grilă nouă din altă
dată — **rând nou cu același cod**; lucrările țin codul și categoria, iar rapoartele iau versiunea în vigoare la data lor.

**Lucrările în acord** (*Setări → Lucrările în acord*): codul (îl scrieți și în Excel), denumirea RO / RU / EN, unitatea de
măsură, secția, bifa **„Progresiv”**. Butonul **„Norme și tarife”** — istoria normelor lucrării, fiecare **din data dată**:
- **norma de timp** (ore pe unitate) sau **de producție** (unități pe oră);
- **grila și categoria lucrării** — tariful pe unitate = tariful pe oră al categoriei × norma de timp (= tariful ÷ norma de
  producție, CM art. 170); sau **tariful pe unitate scris direct** (atunci grila nu contează);
- temeiul (ordinul de normare).
Tariful se păstrează cu 4 zecimale (bani pe bucată), sumele — cu 2. Coloana „Tariful acum” arată ce se aplică azi sau de ce nu
se poate socoti (grila fără categoria cerută, lucrarea fără normă).

**Brigăzile** (*Setări → Brigăzile*): codul, denumirea, secția, **împărțirea sumei** (*ore × KTU* sau *ore × tariful orar ×
KTU*) și **membrii** — raportul de muncă, KTU-ul implicit, de la / până la. În raport KTU-ul și orele se pot schimba pentru
luna lui.

**Tipurile de calcul** (*Setări → Tipuri de calcul*): **ACORD** și **ACORDP** sunt livrate (automate, impozabile, cu CAS și
CNAM, intră în medie). **Treptele ACORDP nu sunt livrate** — le scrieți din contractul colectiv / regulamentul de salarizare,
în tipul ACORDP: „de la % îndeplinire : spor %”, de ex. `100:50, 110:100`. Fără trepte, ACORDP nu se calculează. Procentul de
plată a rebutului parțial se scrie pe rând, în raport (din contractul colectiv).

**De verificat de contabilitate:** procentul rebutului parțial și treptele progresive din contractul colectiv; dublul la
sărbători în acord socotit pe câștigul mediu pe oră al lunii în acord; orele lucrate în acord luate din pontaj când rândurile
nu le au.

**Garanția la neîndeplinirea normei (S5b).** În antetul raportului, câmpul „Neîndeplinirea normei (CM art. 161)”: din vina
angajatorului — cel puțin câștigul mediu pe oră × orele lucrate la raport; fără vina părților — cel puțin 2/3 din tariful orar al
categoriei × orele. Salariul plătește diferența până la câștigul în acord al raportului — tipul **GARANT**. Cu cauza scrisă, orele
lucrate sunt obligatorii pe fiecare rând. Detaliile, cu staționarea, șomajul tehnic, sporul vătămător și evidența globală — în
*Fabrica: timpul fără producție, sporul vătămător, evidența globală*.

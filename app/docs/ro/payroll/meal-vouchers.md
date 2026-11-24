# Tichetele de masă

Borderoul tichetelor de masă (Legea nr. 166/2017, HG nr. 227/2018 cu modificările din 22.01.2026): câte tichete primește fiecare
angajat pentru **luna lucrată**, transferate pe instrumentul lui de plată la **data borderoului**. Tichetele în limita valorii
neimpozabile nu intră în salariu; partea peste ea e **facilitate impozabilă** (Codul fiscal, art. 19 lit. a¹)) și intră singură în
calculul salariului lunii datei.

## Pentru omul de la ecran

**Borderou nou** (*Salarizare → Tichete de masă → „Borderou nou”*):
- **luna lucrată** — tichetele se socotesc din pontajul ei (de regulă luna trecută);
- **data transferului** — partea impozabilă intră în calculul salariului lunii acestei date;
- **subdiviziunea** — gol pentru toată întreprinderea, sau o secție (cu sub-secțiile ei).

Borderoul se completează singur din **pontajul lunii lucrate**:
- **o zi lucrată (cu ore în pontaj) = un tichet**; zilele de concediu, boală, deplasare, staționare n-au ore — n-au tichet;
- **munca în schimburi** (graficul de lucru pe ture sau graficul de ture al secției în acea lună): **orele din schimburile de zi
  ÷ 8 + orele din schimburile de noapte ÷ 7**, rotunjit la întreg (HG 227/2018 pct. 12). Un schimb e „de noapte” când cel puțin
  jumătate din orele lui sunt noaptea (22–06). De exemplu: 8 ture de zi × 12 h + 8 ture de noapte × 12 h → 96 ÷ 8 + 96 ÷ 7 =
  12 + 13,71 = 25,71 → **26 de tichete**;
- fiecare persoană primește tichetele **o singură dată**, pe raportul de bază (ziua lucrată pe două raporturi nu dă două
  tichete); contractul de prestări servicii — fără tichete.

Rândul arată zilele lucrate, orele în schimburi (zi / noapte), **tichetele**, **suma** (tichete × valoarea nominală), **partea
impozabilă** (tichete × (valoarea − valoarea neimpozabilă)) și explicația. **Numărul tichetelor se poate scrie de mână** pe rând
(rămâne la recompletare, cu eticheta „de mână”); săgeata de lângă el îl întoarce la cel socotit. **„Completează din pontaj”**
reface borderoul după un pontaj corectat (rândurile noi se adaugă, cei care n-au mai lucrat ies).

**Valoarea nominală** (antetul) vine din Constante, se poate schimba pe borderou. Sus apare lista **„De corectat înainte de
aprobare”**: valoarea 0 sau sub minim, data transferului înaintea lunii lucrate, borderoul gol, angajatul care are deja tichetele
pe aceeași lună într-un alt borderou aprobat.

**Aprobarea** (dreptul de aprobare din salarizare): partea impozabilă intră în calculul salariului lunii datei — rândul **TICHET**
„Tichete de masă: partea peste valoarea neimpozabilă” (cu impozit, CNAM și CAS) și rândul **TICHETN** „Tichete de masă acordate
în natură” — reținerea aceleiași sume, fiindcă tichetele sunt deja pe card și nu se plătesc a doua oară în bani. La valoarea de
cel mult 70 lei nu apare nimic în salariu. Aprobarea / anularea ei se opresc cât calculul salariului lunii datei e aprobat pentru
acești angajați (redeschideți-l întâi). După aprobare recalculați luna.

**Tiparul** — „Borderoul tichetelor de masă”: antetul întreprinderii, luna lucrată, valoarea, tabelul cu zilele, orele, tichetele,
suma, partea impozabilă și coloana pentru semnătură, semnăturile conducătorului și contabilului-șef.

## Pentru cine configurează

**Constantele salarizării** (*Setări → Constantele salarizării*, cu dată):
- `meal_voucher_value` — **valoarea nominală a tichetului** din ordinul conducătorului (HG 227/2018 pct. 8); livrată **0** —
  întreprinderea nu dă tichete până nu o scrieți;
- `meal_voucher_min` 35 lei, `meal_voucher_cap` **70 lei** — valoarea neimpozabilă; peste ea — facilitate impozabilă;
- `meal_voucher_night_pct` 50 % — de la câte procente ore de noapte un schimb e „de noapte”.

**Tipurile de calcul** livrate: **TICHET** (acumulare automată, impozabilă, cu CNAM și CAS, nu intră în medie) și **TICHETN**
(reținere automată). Dreptul — al salarizării (`payroll.*`); numerotarea — seria **TM** (*Setări → Numerotarea*); șablonul de
tipar — *Setări → Șabloane de tipar → Borderoul tichetelor de masă*.

**De verificat de contabilitate:** limitele 35 / 70 lei în textul final al HG 227/2018 și al Codului fiscal pe 2026; dacă partea
peste 70 lei intră și în baza CAS și CNAM (programul: da — se schimbă în tipul TICHET); regula „un tichet pe zi” la timpul parțial
(programul: o zi lucrată = un tichet, indiferent de ore, în afara muncii în schimburi).

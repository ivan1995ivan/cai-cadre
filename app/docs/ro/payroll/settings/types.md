# Tipurile de calcul: formula și baza

*Administrare → Setări → Tipuri de calcul.* Fiecare acumulare, reținere sau contribuție a angajatorului e un **tip de
calcul**: codul, denumirea (RO / RU / EN), categoria, **cum se calculează** și **ce se impozitează**.

## Tabelul

Coloana **„Din ce se calculează”** arată regula fiecărui tip, ca baza să fie vizibilă:
- la tipurile **automate** — regula motorului, cu valorile constantelor în vigoare. Exemplu, SUPL: „tariful orar × (primele 2
  ore pe zi × 150 % + restul × 200 %), CM art. 157”;
- la celelalte — formula sau baza cu denumirile tipurilor (de ex. SINDICAT: „baza × procentul (implicit 1 %); baza: SAL
  Salariul de funcție + MINIM Completare până la salariul minim + …”).

Apoi: categoria, impozitul, CNAM, CAS, „intră în medie”, plafonul neimpozabil și codul sursei de venit (IPC21 / IALS21).

## Felurile de calcul

| Formula | Ce face |
|---|---|
| Automat | Se calculează singur din pontaj, concedii, foi de boală, ordine (salariul, sporurile fixe, noaptea, sărbătorile, suplimentarele, concediul, boala, premiile, CAS) |
| Sumă fixă | Suma din rândul angajatului (fila „Salariu”, ordinul, documentul) |
| % din salariul de funcție | SalariuFunctie × partea lucrată × procentul |
| % din baza de calcul | Suma tipurilor din bază × procentul |
| Tarif orar × ore | Tariful din rândul angajatului × orele lucrate (+ sporul pentru suplimentare și sărbători) |
| % pe trepte de vechime | Baza × procentul treptei atinse de vechimea totală |
| **Formulă** | O expresie scrisă de dvs. (mai jos) |

**„Se calculează pentru”**: *doar angajații care au rândul* (implicit) — tipul intră în calcul doar la cine îl are în fila
„Salariu”; *toți angajații* — un tip general (de exemplu un spor pentru toți din pontaj), calculat pe fiecare raport de
muncă (fără contractele de prestări servicii). Treptele de vechime sunt „pentru toți” (așa erau și înainte).

## Formula

Se scrie ca în Excel, dar pentru Moldova: **argumentele se despart cu „;”**, zecimalele se scriu cu **„,” sau „.”**
(`1,5` = `1.5`). Literele mari / mici nu contează.

- Operatorii: `+ - * / ( )`; comparațiile `< <= > >= = <>`; `și` / `sau` (și `and` / `or`).
- Funcțiile: `min(a; b; …)`, `max(a; b; …)`, `round(x; n)` (rotunjirea comercială la n zecimale), `abs(x)`,
  `daca(condiție; da; nu)` (și `if`). În `daca` se calculează doar ramura aleasă.
- `C.<cod>` — o constantă a salariului (de ex. `C.night_pct`), valoarea în vigoare în luna calculului.
- `[COD]` — suma deja calculată a altui tip în același rând (de ex. `[PREMIU]`).

**Variabilele** (în editor: clic pe ele le inserează; descrierea — la trecerea cu mouse-ul):

| Variabila | Ce este |
|---|---|
| SalariuFunctie | salariul de funcție pentru norma raportului (salariul × norma) |
| Norma, OreLucrate | norma de ore a lunii, orele lucrate (pontajul) |
| ZileLucrate, ZileNorma | zilele lucrate; zilele lucrătoare ale lunii după calendar |
| TarifOrar | SalariuFunctie / Norma |
| ParteLucrata | partea lucrată din normă (0…1), ca la salariu |
| OreNoapte | orele de noapte (22–06) |
| OreSarbatoare, OreOdihna | orele în zile de sărbătoare și de repaus; din ele — în zilele de repaus după grafic |
| OreSarbatoareInNorma, OreSarbatoarePesteNorma | aceleași ore în limita normei lunare / peste ea (CM art. 158) |
| OreSuplim2, OreSuplimPeste | orele suplimentare: primele 2 pe zi / următoarele (CM art. 157) |
| Suma, Procent, Cantitate | din rândul angajatului (Procent gol — procentul tipului) |
| Baza | suma tipurilor din „Baza de calcul” a tipului |
| SalariuMinim, SalariuMediu | salariul minim pe țară, salariul mediu prognozat (constantele) |
| NormaRaport | norma raportului de muncă (1; 0,5…) |
| VechimeAni, VechimeIntreprindereAni | vechimea totală / în întreprindere, ani întregi, la sfârșitul lunii |

**Exemple care funcționează** (verificate de teste):

| Ce | Formula |
|---|---|
| Noaptea, ca regula automată | `TarifOrar * OreNoapte * C.night_pct / 100` |
| Spor de fidelitate 10 % de la 5 ani în firmă | `daca(VechimeIntreprindereAni >= 5; SalariuFunctie * 10 / 100; 0)` |
| Suma cerută, dar nu peste salariul minim | `min(Suma; SalariuMinim)` |
| Procent din bază (ca „% din bază”) | `Baza * Procent / 100` |
| Staționarea (CM art. 80¹): 2/3 din salariul pe oră, cel puțin salariul minim pe oră | `max(SalariuFunctie * 2/3 / Norma; SalariuMinim / 169) * Cantitate` |

**Verificarea la salvare**: o greșeală de sintaxă, o variabilă, constantă sau un tip care nu există — eroare cu **poziția**
(„Constanta C.nu_exista nu există (poziția 25)”); editorul o arată pe loc, pe măsură ce scrieți. Nu se pot folosi tipurile
calculate după formule (CAS, CAS pe baza minimă) sau la plată (impozitul, CNAM, avansul). **Dependența circulară** (A
folosește B, B îl folosește pe A — direct, prin bază sau prin [COD]) se respinge: „Dependență circulară: A → B → A”. Codul
unui tip folosit în formula / baza altuia nu se redenumește și nu se marchează pentru ștergere — întâi îl scoateți de acolo.

**Ordinea de calcul** se face singură: întâi tipurile automate, apoi rândurile scrise de mână și completarea până la salariul
minim, apoi celelalte tipuri — fiecare după tipurile de care depinde; la sfârșit bazele, CAS și CAS pe baza minimă.

**Rezultatul negativ** se oprește la 0 (o acumulare / reținere nu poate fi negativă), cu avertisment în explicație. O eroare la
calcul (de ex. împărțirea la 0 la un angajat cu Norma 0) oprește calculul lunii cu numele tipului și al angajatului:
folosiți `daca(Norma > 0; …; 0)`.

## Cum se citește explicația

În calculul lunii, rândul unui tip cu formulă are explicația: formula cu valoarea fiecărei variabile și rezultatul, de ex.
`TarifOrar 37,28 × OreNoapte 16 × C.night_pct 50 / 100 = 298,24`; după „;” — temeiul din rândul angajatului.

## „Încearcă pe un angajat”

În editorul tipului: alegeți angajatul și luna, opțional suma / procentul / cantitatea (un rând închipuit) și apăsați
**Încearcă**. Programul calculează luna în memorie, cu formula așa cum e scrisă acum (și nesalvată), și arată pe fiecare
raport de muncă variabilele cu valorile lor, rezultatul și eventualele erori. **Nu se salvează nimic.**

## Ce se impozitează

Grupa „Ce se impozitează” din editor: impozitul pe venit, CNAM, CAS (bifele), „intră în salariul mediu” (concedii, boală),
plafonul neimpozabil (pe lună, pe an sau % din salariul mediu — partea de sub plafon nu intră în baze) și codul sursei de
venit (IPC21 / IALS21).

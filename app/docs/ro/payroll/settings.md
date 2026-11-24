# Setările salariului (constantele 2026)

Pentru cine configurează salarizarea: *Administrare → Setări → Constantele salarizării* și *Tipuri de calcul*. Fiecare
constantă are **„în vigoare din”**: la schimbarea legii se adaugă un rând nou cu data lui, cel vechi rămâne pentru lunile
trecute. Temeiul neconfirmat încă din textul oficial are eticheta **„de verificat”** — valoarea se corectează aici, fără
programator.

**Preîncărcate la instalare și la actualizare** (rândurile lipsă se adaugă pe cod și dată; cele schimbate de dvs. rămân):

| Constanta | 2026 | 2027 (adoptat) | Temeiul |
|---|---|---|---|
| Salariul minim pe țară | 6 300 lei; 169 ore (37,28 lei/oră) | — | HG 771/2025 |
| Salariul mediu lunar prognozat | 17 400 lei | — | HG 773/2025 |
| Scutirea personală P / majorată M | 29 700 / 34 620 | 40 020 / 46 680 | CF art. 33; Legea 247 din 22.10.2026 |
| Scutirea pentru soț / soție Sm | 21 780 | — | CF art. 34 alin. (2) |
| Întreținutul N / cu dizabilitate H | 9 900 / 21 780 | 11 040 / — | CF art. 35 alin. (1); Legea 247/2026 |
| Venitul maxim al întreținutului | 12 400 lei / an | — | CF art. 35 alin. (2) lit. b) |
| Plafonul pentru P / M; alerta | 360 000 lei; 90 % | — | CF art. 33 alin. (1) |
| CAS angajator; timp parțial — minim | 24 %; 25 % din CAS pe salariul minim | — | Legea 489/1999 art. 22 alin. (1), anexa 1 |
| Ore suplimentare | primele 2 ore / zi 150 %, următoarele 200 % | — | CM art. 157 |
| Sărbători / zile de repaus | salariu lunar +100 % în normă, +200 % peste; tarif pe oră 200 % | — | CM art. 158 |
| Boala — zilele angajatorului | 5 pe certificat, cel mult 15 pe an; 75 % | — | Legea 289/2004 art. 4 |
| Boala — venitul mediu | 12 luni, cel mult 5 salarii medii pe lună | — | Legea 289/2004 art. 7 |
| Accident de muncă / boală profesională | 20 de zile, 100 % (de verificat) | — | Legea 756/1999 |
| Salariul mediu pentru concedii | 3 luni | — | HG 426/2004 |

Valorile pentru 2027 marcate „—” nu sunt adoptate încă (proiectele de acte nu se pun): când apare actul, adăugați rândul cu
data 01.01.2027.

**Tipurile de calcul noi** (automate): **MINIM** „Completare până la salariul minim”, **BOALAACC** „Indemnizația pentru
accident de muncă / boală profesională (zilele angajatorului)”, **CASMIN** „CAS pe diferența până la baza minimă”. Un tip
automat se poate face inactiv (de exemplu MINIM), dar legea cere salariul minim — avertismentul rămâne.

**La actualizarea unei instalări vechi** migrația corectează doar ce a rămas cu valoarea livrată: salariul minim 5 500 → 6 300,
salariul mediu 17 200 → 17 400, temeiurile vechi; sporul unic pentru orele suplimentare devine plata primelor ore (100 + spor).
Cererile de scutire „pe an” devin cereri cu valabilitate de la / până la, persoanele întreținute — rânduri; cererile cu „S”
(abrogată) apar „De verificat”.

**Timpul fără producție, sporul vătămător, tichetele de masă (S5b)** — pentru cine configurează:
- tipurile de calcul noi, automate: **STATIONARE** (staționarea), **SOMAJT** (șomajul tehnic), **GARANT** (garanția acordului),
  **VATAM** (sporul vătămător din subdiviziune / funcție), **TICHET** (partea impozabilă a tichetelor) și reținerea **TICHETN**;
  STATIONARE, SOMAJT, GARANT, VATAM intră în baza sindicatului / pensiei alimentare livrate;
- constantele noi: `idle_employer_pct` 100, `idle_nofault_pct` 66,6667, `idle_worker_pct` 0, `tech_unemployment_pct` 50,
  `shortfall_nofault_pct` 66,6667, `meal_voucher_value` 0 (scrieți valoarea tichetului), `meal_voucher_min` 35,
  `meal_voucher_cap` 70, `meal_voucher_night_pct` 50;
- salariul lunar al celui angajat / eliberat în lună se plătește din norma lunii întregi (până acum — salariul întreg);
- vezi *Fabrica: timpul fără producție, sporul vătămător, evidența globală* și *Tichetele de masă*.

**Salarizarea în acord (S5a)** — pentru cine configurează:
- tipurile de calcul noi **ACORD** („Salarizarea în acord”: lucrările din rapoartele de producție aprobate) și **ACORDP**
  („Acord progresiv”: sporul peste normă pe lucrările marcate „progresiv”) — automate, impozabile, cu CAS și CNAM, intră în
  medie și în baza sindicatului / pensiei alimentare livrate;
- **treptele ACORDP nu sunt livrate**: în tipul ACORDP, câmpul „Treptele acordului progresiv” — „de la % îndeplinire : spor %”,
  de ex. `100:50, 110:100`, din contractul colectiv; fără trepte ACORDP nu se calculează;
- modalitatea de remunerare nouă **„În acord”** (raportul de muncă, ordinul), cu tariful orar al categoriei obligatoriu;
- în formule: `OreNormate`, `OreAcord`, `IndeplinireNorma`; vezi *Producția: salarizarea în acord*.

**Tipurile de ore și remunerarea pe funcție (S4b)** — pentru cine configurează:
- tipul de calcul nou **ORE** („Ore pe tipuri”, automat: ore plătite × tariful, cu orele garantate) — intră în media pentru
  concediu / boală și în baza sindicatului / pensiei alimentare livrate; un tip de ore poate avea tipul lui de calcul (automat,
  „Ore pe tipuri”), legat în *Setări → Tipuri de ore*;
- **CUMUL** se numește „Plata pentru cumularea funcțiilor / suplinire” și se calculează din înregistrările de cumulare de pe
  raport (CM art. 156), nu din cumul; „Plata pentru cumul (%)” de pe raport s-a mutat singur în înregistrări, cu aceleași sume;
- în formule: `Ore.COD`, `OrePlatite.COD`, `Garantat.COD`, `Tarif.COD` (vezi *Tipuri de ore, tarife pe funcție și orele
  garantate*).

**Formula și acumulările planificate (S3)** — pentru cine configurează:
- *Tipuri de calcul*: felul nou **„Formulă”** (expresia, variabilele, „Încearcă pe un angajat”) și coloana „Din ce se
  calculează” la toate tipurile — vezi *Tipurile de calcul: formula și baza*. La actualizare, tipurile existente pe **trepte
  de vechime** devin „pentru toți angajații” (așa se calculau); celelalte rămân „doar cu rândul”, ca până acum.
- *Funcții (CORM)*: **acumulările-tip** ale fiecărei funcții (butonul cu portmoneul) — completează tabelul „Acumulări și
  rețineri” din ordinul de angajare.
- Numerotarea documentului „Modificarea acumulărilor planificate” — seria **MA** (*Administrare → Setări → Numerotarea*);
  forma lui de tipar — în *Forme de tipar*.
- Ordinea de calcul s-a schimbat la cauza ei: completarea până la salariul minim și corectările de mână se fac **înaintea**
  tipurilor care depind de ele (sindicatul și pensia alimentară se iau acum și din MINIM și din salariul corectat de mână).


**Regimul fiscal (S4)** — sus pe pagina *Constantele salarizării*: regimul general / **rezident IT Park** cu „în vigoare
din” (luna următoare datei statutului, CF art. 375) și istoria lui. Constantele noi: `it_park_tax_pct` 7 %, `it_park_min_pct`
30 %, `it_park_insured_pct` 68 %, `it_park_sick_covered` (zilele de boală ale angajatorului acoperite de impozitul unic — de
verificat), `it_park_count_maternity` (concediul de maternitate la minimul pe angajați — de verificat),
`it_park_sales_alert_day` 20. Formele noi de tipar: „Impozitul unic IT Park — calculul lunii (IU17)”, „ISAPTI17”, „Nota
anuală pentru angajat (IT Park)”. Vezi [Regimul IT Park](help:payroll/it-park).

# CAI CADRE — note de lucru pentru Claude

Instalarea de sine stătătoare a produsului CAI CADRE (al lui Anatol) pe acest
server, adresa publică: `https://cai-cadre.integratii.md`. Acest fișier descrie
ce există deja, regulile serverului și cum se lucrează aici. Actualizează
secțiunea **Status** la fiecare etapă încheiată, ca următoarea sesiune să
pornească de unde s-a rămas, nu de la zero.

## Status

- **Ce este** (2026-11-17, cerut de Ion): copia proiectului SCTO
  (`/srv/projects/scto`, commit `826a92f`, **CAI CADRE 1.6.0**) făcută proiect
  separat, ca Anatol să lucreze aici fără să atingă instalarea SCTO: alt folder,
  altă adresă, alt depozit git, altă stivă compose, altă bază. De aici codul
  merge pe drumul lui — nu se sincronizează singur cu SCTO; o schimbare făcută
  aici ajunge acolo (sau invers) doar dusă de mână (`git format-patch` / `git am`
  pe `app/`).
- **Produsul**: CAI CADRE — evidența cadrelor și salarizarea pentru instituții
  medico-sanitare din Moldova (Django 6 + DRF + JWT, React 19 + Ant Design 6,
  interfață ro / ru / en, documentație în `app/docs/ro|ru`, 131 de teste
  pytest); planul și istoricul versiunilor — `app/PLAN.md`. Istoricul git de
  până la 1.6.0 a rămas în depozitul SCTO (`ivan1995ivan/caicadre`); aici
  istoria începe cu un singur commit.
- **Ce s-a schimbat față de SCTO** (doar infrastructura, `app/` e identic):
  proiectul compose `cai-cadre`, volumele `cai-cadre-db` / `cai-cadre-data`,
  imaginea `cai-cadre-app`, aliasul de rețea `cai-cadre-web`, baza `caicadre`
  cu rolurile `caicadre` (superuser) și `caicadre_app` (aplicația), portul local
  `127.0.0.1:3960`, comenzile `cai-cadre-backup` / `cai-cadre-restore`, copiile
  `cai-cadre-AAAA-LL-ZZ.*`, grupul `proj-cai-cadre`.
- **Rețeaua stivei are subrețea fixă** (`10.219.0.0/28`, `networks` în
  `docker-compose.yml`): plajele implicite ale Docker de pe server sunt epuizate
  (31 de rețele), o rețea fără subrețea dată nu se mai creează. Proba
  restaurării ia `10.219.0.16/28` (`STACK_SUBNET` în `restore-check.sh`),
  `deploy/nginx-test.sh` — `10.219.0.32/29`.
- **Instalare curată** (hotărât de Ion): fără date demo, bază goală; instituția
  și administratorul se dau în asistentul de instalare (doar local, prin tunel
  SSH — `docs/instalare.md`). Regimul de probă ține 30 de zile de la instalare,
  apoi doar citire — licența o emite Anatol.
- **Instalată — cu date demo** (2026-11-24, cerut de Anatol, ca să verifice S1–S5a pe
  `https://cai-cadre.integratii.md`): stiva reconstruită cu codul de la `14f9718`, instalarea prin API-ul asistentului
  din containerul `app` (PostgreSQL `db` / `caicadre` / `caicadre_app`), administratorul `anatol`, „Demo Producție” SRL
  (`crm_demo`, utilizatorii pe roluri — `docs/instalare.md`); modulul Producția — oprit. Prima copie cu aplicația:
  `cai-cadre-2026-11-24`. **Baza e demonstrativă**: pentru date reale — bază nouă, instalare curată.

- **Stiva — pornită** (2026-11-17, Ion): `.env` cu parole generate și
  `TUNNEL_TOKEN` (tunel propriu), toate cele cinci servicii `healthy`,
  `http://127.0.0.1:3960/health` → 1.6.0, `installed: false` (aplicația așteaptă
  asistentul de instalare). Public Hostname `cai-cadre.integratii.md →
  http://cai-cadre-web:80` pus de Ion; verificat prin tunel: `/health` → 200,
  `/__platform/…` și `POST /api/setup/install/` → 404, `..` → 400,
  `http://` → 301, CSP și HSTS prezente.

- **Direcția nouă — întreprinderi private (SRL)** (2026-11-21, hotărât de Anatol): produsul nu mai e
  pentru spital; tot ce ține de stat se scoate, salarizarea se face după legislația RM pentru sectorul
  privat, cu profilurile **IT Park / fabrică / aviație / transport** ca constante. Studiul (legislația
  2026–2027, cu surse), deciziile și etapele S0–S7: **`app/PLAN-SRL.md`** — de acolo se lucrează.
- **S1 „fără stat” — gata** (2026-11-21): antetul întreprinderii (logo, IDNO, CAEM, adresa,
  semnatarii din Constante) în locul Stemei / fondatorului pe toate formele; categoriile de personal —
  clasificator după grupele CORM; 42 de funcții cu coduri CORM 006-2021; temeiurile din Codul muncii
  (redacția 2026); tipurile de ordin fără atestare / gărzi; pontajul după Convenția colectivă nr.
  17/2020; graficul de ture (CM art. 101); scoase EMC, atestarea, vaccinurile, rezidenții, categoria
  de calificare medicală, MS nr. 17, VECH / CATEG / GARDA; examenele medicale cu periodicitatea pe
  funcție; **evidența militară — modul opțional, oprit implicit** (Legea 112/2023); demo „Demo
  Producție” SRL (70 de persoane). Verificat: 155 de teste, typecheck. De verificat de om: codurile
  CORM față de Ordinul MMPS 212/2025 (în vigoare din 04.07.2026); HG 1025/2016 → HG 146/2026?

- **S2 „cifrele și regulile 2026” — gata** (2026-11-21): constantele 2026 corectate (salariul minim 6 300 —
  HG 771/2025, mediu 17 400 — HG 773/2025) și cele 2027 adoptate (P 40 020, M 46 680, N 11 040 — Legea
  247/2026), seed pe (cod, dată); suplimentarele pe zi: primele 2 ore 150 %, restul 200 % (`split_overtime`,
  baza pentru evidența globală din S5); sărbătorile +100 % în limita normei / +200 % peste; completarea până
  la salariul minim (tipul MINIM, CM art. 131); **baza minimă CAS** (CASMIN, Legea 489 art. 22, 25 % la timp
  parțial); boala: 5 zile × certificat, **cel mult 15 pe an**, accidentul de muncă 20 de zile (BOALAACC,
  15321), plafonul 5 salarii medii; **scutirile**: Sm în locul „S” abrogat, întreținuții ca rânduri
  (`ExemptionDependent`: rudenia, de la / până la, legătura cu familia, H), cererea cu valabilitate și
  renunțarea la P / M, pragul de 360 000 (venitul trebuie să fie mai mic), alerta la 90 %; IALS21 pe coduri;
  tiparul cererii (`exemption_request`). Verificat: 171 de teste, typecheck. **De verificat de om /
  contabilitate:** 75 % la boală vs. stagiul; 20 de zile / 100 % la accident; excepțiile de la baza minimă
  CAS; rubrica IPC21 pentru diferența de bază CAS; forma anexei 6 (HG 697/2014) în vigoare. **Rămas:** locul
  aplicării scutirii (bază / cumul) — de făcut împreună cu S3.

- **S3 „formula și acumulările la angajare” — gata** (2026-11-21): tipul de calcul cu **formulă**
  (`payroll/formula.py`: evaluator `ast` cu listă albă, Decimal; sintaxa RO — `;` între argumente,
  `1,5`; variabilele `SalariuFunctie`, `TarifOrar`, `OreNoapte`, `OreSuplim2`, `Suma`, `Procent`,
  `Cantitate`, `Baza`, `C.<cod>`, `[COD]`…; ciclurile respinse la salvare; ordinea topologică;
  explicația rândului cu valorile), `/api/payroll/types/{id}/try/` („Încearcă”, fără salvare),
  `how` pentru toate tipurile; tabelul **„Acumulări și rețineri”** în ordine (adaugă / modifică /
  oprește; semnarea → `EmployeePayItem`, anularea le întoarce), acumulările-tip pe funcție
  (`OccupationPayItem`); documentul **„Modificarea acumulărilor planificate”** (`PayItemChange`, seria
  MA); fila „Salariu” cu sursa rândurilor; scutirea la cumul extern + `ExemptionRequest.place`.
- **Interfața „Clasic de birou”** (2026-11-21, cerută de Anatol: „să fie ca C++ / Java”): tema și
  aspectul `desktop` (implicit pentru întreprindere; `desktop_dark`): bara de titlu, meniul clasic
  (Alt + litera), bara de unelte legată de fereastra activă, ferestrele ca file, bara de stare, tabele
  dense cu grilă, dialoguri ca ferestre; pe telefon „☰”. `layout/DesktopLayout.tsx`, `layout/desktop/`,
  `theme/themes.ts`, `styles.css` (`html[data-look='desktop']`); temele vechi rămân de ales.
  Verificat: 210 teste, typecheck, build, capturi Playwright (RO / RU / telefon).

- **S4 „IT Park” — gata** (2026-11-21): regimul fiscal pe luni cu istoric (`FiscalRegime`, din luna
  următoare statutului — CF art. 375) în Constantele salarizării; constantele `it_park_*` (7 %, 30 %, 68 %,
  boala acoperită / maternitatea numărată — de verificat, alerta din ziua 20); calculul: salariul din CIM
  impozitat final (`PayrollLine.it_park`: fără bazele impozitului / CNAM, fără CAS / CASMIN; MINIM rămâne),
  prestările de servicii în regimul general; plata fără CNAM, impozit, scutiri (`PaymentLine.final_gross`),
  regimul lunii calculului; media pentru boală din venitul asigurat 11 832; „Impozitul unic IT Park”
  (`ItParkMonth`: venitul din vânzări, IU17 010 / 020 / 030, angajații cu ≥ 1 zi lucrată); IPC21 cu bifa
  (`table1/it/flag1`) și 162 / 160 / 15311 / 159; IALS21 și anexa 8 doar regimul general; ISAPTI17 și nota
  anuală (anexa 5); formele noi `it_park_tax`, `isapti17`, `it_park_note`; `app/docs/ro|ru/payroll/it-park.md`.
  Verificat: 223 de teste, typecheck, build, capturi. **De verificat de om:** structura oficială IU17 /
  ISAPTI17 (fără scheme XML), tag-ul XML al bifei, tariful / CAS 0 la 162, zilele de boală acoperite,
  maternitatea la minim; ucenicia nu e un fel de raport în program.

- **S4b „tipurile de ore și remunerarea pe funcție” — gata** (2026-11-21, cererea clientului §2.6): clasificatorul
  `worktime.HourType` (INSTR, EXAM livrate; grupa, legătura cu orele lucrate within / added / none, pe zile / pe lună,
  profilul, tipul de calcul); pe raport — **modalitatea de remunerare** cu istoric (`Employment.pay_mode` salary / hourly /
  hour_types / mixed, `hourly_rate`, în `EmploymentHistory`), **tarifele pe tipuri de ore** (`JobHourRate`: tarif, ore
  garantate, de la / până la, din ordin — tabelul „Tarife pe tipuri de ore”, `apps/worktime/rates.py` — sau de mână; tarifele-tip
  ale funcției `OccupationHourRate`); orele pe tipuri în pontaj (`TimesheetLine.typed_hours`, pe zile / total, import Excel,
  tipar, export); **garanția = minimul plătit**, redusă proporțional cu zilele lucrătoare fără raport / tarif, suspendarea și
  absențele din setarea `guarantee_absences` (implicit toate concediile și boala; deplasarea și formarea nu) —
  `apps/worktime/hour_types.py`; salariul: tipul ORE („Ore pe tipuri”), variabilele `Ore.COD` / `OrePlatite.COD` /
  `Garantat.COD` / `Tarif.COD`; **cumularea funcțiilor / suplinirea / interimatul pe același CIM (CM art. 156)** =
  `staff.FunctionCombination` pe raportul de bază (% propriu / % al funcției / sumă fixă / pe ore), separat de cumul (raport
  propriu); ordinele de cumul / suplinire / interimat: „pe același contract” (implicit) sau „raport separat”; `combination_pct`
  mutat în înregistrări (migrația staff 0007) și scos; CUMUL redenumit; `app/docs/ro|ru/worktime/hour-types.md`. Verificat:
  236 de teste, typecheck, build, capturi `s4b-*` (RO / RU). **De verificat de om:** numerotarea articolelor despre cumul în CM
  (capitolul „Munca prin cumul”, art. 267 și urm.?); lista absențelor care reduc garanția (am pus și maternitatea, studiile,
  zilele libere — după principiul „tot ce nu e muncă”); sporurile de noapte / sărbătoare pe orele de zbor — S6.

- **S5a „producția — salarizarea în acord” — gata** (2026-11-23, hotărât de Anatol: modul general, configurabil, fără client
  concret; volumele de mână + Excel; S5 în doi pași). Aplicația nouă `apps/production` (modul opțional, oprit implicit:
  `Company.production_enabled`, drepturile `production.*` filtrate ca la evidența militară; licența — parte din salarizare):
  **grila tarifară** cu istoric pe cod (`TariffGrid` + `TariffRank`: coeficient sau tarif direct), **lucrările**
  (`Operation`, bifa „progresiv”) cu **normele și tarifele din data dată** (`OperationRate`: norma de timp / de producție,
  categoria din grilă sau tarif pe unitate direct; tariful = tariful categoriei × norma de timp, 4 zecimale), **brigăzile**
  (`Brigade`, `BrigadeMember` cu KTU; împărțirea ore × KTU sau × tariful orar), **raportul de producție** (`ProductionReport`
  seria RP, individual / pe brigadă; rândurile cu rebutul pe vinovați CM art. 162; membrii cu ore și KTU; socotit la salvare,
  verificat strict și **fixat la aprobare**; aprobarea / anularea blocate cât calculul lunii e aprobat; „Completează din
  brigadă” cu orele din pontaj; import Excel lucrări / membri; tiparul `production_report`) — `apps/production/services.py`.
  Salariul: modalitatea **„În acord”** (`pay_mode="piece"`, cere tariful orar al categoriei; plătește și tarifele pe tipuri de
  ore), tipurile **ACORD** (auto `piece`) și **ACORDP** (auto `piece_prog`, treptele în `PayType.scale` — **nelivrate**, din
  contractul colectiv), suplimentarele în acord = doar sporul din tariful categoriei, sărbătorile = câștigul în acord pe oră ×
  100 %, MINIM compară și ACORD; variabilele `OreNormate`, `OreAcord`, `IndeplinireNorma`. Rolurile livrate primesc
  `production` (contabilitatea tot, directorul view/approve, șeful de subdiviziune view/create/edit pe „own”). Interfața:
  Salarizare → Rapoarte de producție, Setări → Grila tarifară / Lucrările în acord / Brigăzile, Constante → Module, editorul
  treptelor ACORDP; `app/docs/ro|ru/production.md`. Verificat: 250 de teste, typecheck, build, capturi Playwright RO / RU
  (copie de unică folosință, rețea izolată). **De verificat de om / contabilitate:** procentul rebutului parțial și treptele
  progresive (contractul colectiv); dublul la sărbători pe câștigul mediu pe oră al lunii în acord; orele în acord din pontaj
  când rândurile nu le au. **Mutat în S5b:** garanția la neîndeplinirea normei (CM art. 161), alături de staționare.

- **S5b „fabrica: timpul fără producție” — gata** (2026-11-24, hotărât de Anatol: staționarea / șomajul tehnic din ordin,
  evidența globală pe graficul de lucru, tichetele — borderou + salariu, sporul vătămător automat din subdiviziune / funcție).
  **Staționarea / șomajul tehnic**: tipurile de ordin `idle` / `tech_unemployment` (efectul `idle`, colective) → `Absence`
  (`idle`, `tech_unemployment`, cu `cause` și `pay_pct`) → pontajul St / Șt cu orele planificate (`ph`), doar pe zilele cu tură;
  salariul: STATIONARE / SOMAJT = orele × salariul pe oră × % (cauza: 100 / 66,6667 nu sub salariul minim pe oră / 0; șomajul
  50 %), constantele `idle_*`, `tech_unemployment_pct`; IPC21 categoria 179; ordinele colective: „Adaugă subdiviziunea”
  (`orders/<id>/add-subdivision/`), „La toate punctele” (`items/<id>/copy-params/`). **Garanția CM art. 161**:
  `ProductionReport.shortfall_cause` (employer / nobody; orele obligatorii) → GARANT = max(garanția − câștigul raportului),
  media pe oră (`engine.average_hourly`, din `PayrollLine.info`) / 2/3 din tariful categoriei; intră în MINIM. **Sporul
  vătămător**: `harmful_pct` pe `Subdivision` / `Occupation` (procentul mai mare) → VATAM = salariul pe oră × orele lucrate
  acolo, pe zile, din pontaj; rândul personal NOCIV îl înlocuiește. **Evidența globală**: `WorkSchedule.accounting_months` /
  `accounting_start`, `worktime.accounting_period`; în pontaj fără suplimentare lunară, în ultima lună suplimentarele perioadei
  (din liniile lunilor de dinainte), `norm_absent`; salariul = norma lunii fără absențe. **Tichetele**: `MealVoucherList` /
  `MealVoucherLine` (seria TM, `apps/payroll/meal_vouchers.py`, `meal_views.py`, tiparul `meal_vouchers`), din pontajul lunii
  lucrate (o zi — un tichet; în schimburi zi ÷ 8 + noapte ÷ 7, rotunjit — HG 227/2018 pct. 12, verificat în textul HG din
  01.2026), numărul de mână, aprobarea → TICHET (partea peste `meal_voucher_cap` 70) + reținerea TICHETN; `meal_voucher_value`
  livrat 0. **Reparat**: salariul celui angajat / eliberat în lună = partea din norma lunii întregi (`Month.full_norm`), salariul
  pe oră = salariul / norma lunii întregi; un raport în două tabele de pontaj — totalurile unite (`worktime.merge_totals`).
  Câmpurile noi au `db_default` (migrațiile vechi din teste). Interfața: Salarizare → Tichete de masă, ordinele (cauza, %),
  raportul de producție, graficul de lucru, subdiviziunea / funcția; `docs/ro|ru/factory-time.md`,
  `docs/ro|ru/payroll/meal-vouchers.md`. Verificat: 257 de teste, typecheck, build. **De verificat de om / contabilitate:**
  articolele CM (80, 80¹, 99, 161) în redacția 2026, categoria 179 în IPC21, ridicarea la salariul minim pe oră la timp
  parțial, suplimentarele perioadei „2 ore / restul”, limitele tichetelor 35 / 70 și CAS / CNAM pe partea impozabilă, un tichet
  pe zi la timp parțial.

- **S6b „transportul”, pasul (a) — gata** (2026-11-24, hotărât de Anatol: transportul înaintea aviației — e un client
  posibil —, în trei pași, general, fără materialele clientului). Aplicația `apps/transport`, modul opțional
  (`Company.transport_enabled`, drepturile `transport.*`, ca producția; licența — salarizarea): `Vehicle`, `KmRate` (rândul cu
  cele mai multe potriviri exacte: felul cursei / aria / vehiculul, din data), `Country` + `PerDiemNorm` (seed: 186 de țări,
  anexa nr. 2 la HG 10/2012 în redacția HG 1058/2023, categoria I — citită din MO 502-504/2023, verificată prin sondaj; rândurile
  fără țară proprie nelivrate), `Trip` (seria FP; km din kilometraj; socotit la salvare, fixat la aprobare; luna întoarcerii) cu
  `TripLeg` (țara, intrarea / ieșirea, încărcare / descărcare, masa) și `TripDiem`; `apps/transport/per_diem.py` — pct. 31 (≤ 8 h
  20 %, 8–24 h 40 %, > 24 h modul general 100 % pe zi de la plecare la sosire, pct. 24), pct. 26 (țara de destinație a zilei),
  pct. 23 (tranzitul < 24 h — norma destinației), pct. 33 (masa — 20 %), pct. 22¹ (privat ≥ 70 %), cursul BNM din ziua dinaintea
  plecării (pct. 41), în țară — doar cu `per_diem_domestic_pay` (pct. 3, 24); verificările (curse suprapuse, absențe, segmente),
  actele șoferului ca avertismente (tipuri noi de act: `cpc`, `tachograph_card`, `adr`), importul din Excel (rând pe țară), tiparul
  `trip_sheet`; salariul: KM (în MINIM), DIURNA, DIURNAEX; constantele `per_diem_*`. Interfața: Salarizare → Curse, Setări →
  Vehiculele / Tarife pe km / Țările și diurnele; `docs/ro|ru/transport.md`. Verificat: testele, typecheck, build. **De verificat de
  om / contabilitate:** 70 % peste 20 / 40 %, 20 / 40 % față de pct. 24, țara zilei, cursul la avans, regimul fiscal / CAS al
  diurnei (legis.md inaccesibil de pe server), normele RF pe orașe. **Urmează:** (b) tahograful .ddd + limitele conducere / odihnă;
  (c) GPS + KPI; apoi S6 aviația.

- **S6b „transportul”, pasul (b) „tahograful” — gata** (2026-11-24, hotărât de Anatol: doar cardul șoferului; încălcările + rezumatul,
  pontajul rămâne cum e; fișierele reale le cere Anatol de la firmă). `apps/transport/ddd.py` — citirea descărcării cardului (EF-urile
  cu eticheta FID + anexa 00/01 G1, 02/03 G2: 0520 identificarea, 050E, 0521, 0504 tamponul circular al activităților — pe zile, din cea
  mai nouă înapoi —, 0505 vehiculele (31 / 48 de octeți), 0506 locurile (10 / 21), la G2v2 0528 frontiera (17) și 0529 încărcările (20);
  semnăturile nu se verifică); `TachoFile` (originalul în `media/private/tachograph/`, sha256 unic, legat după numărul cardului din actul
  `tachograph_card` — primele 14 caractere — sau nume + data nașterii, atunci actul se creează), `TachoDay` (ziua UTC, intervalele, minutele;
  din descărcarea cea mai nouă — `tacho.rebuild` la fiecare încărcare / legare / ștergere), `TachoEvent`; `apps/transport/tacho_rules.py` —
  AETR art. 6–8 (continuă, zilnică 9 / 10 h cu 2 prelungiri, 56 / 90 h, odihna zilnică 11 / 3 + 9 / redusă ≤ 3, echipajul 9 h în 30 h,
  săptămânală 45 / 24 h după ≤ 6 × 24 h, două reduse la rând, compensarea până la sfârșitul săptămânii a 3-a), UTC, săptămâna luni, fără
  card = odihnă; `tacho.py` — zilele pe ora Moldovei, cursa (timpi, avertismente, `trips/{id}/tacho/`, `tacho-legs/`), alertele
  `tacho_download` (28 de zile) și `tacho_infringement` (14 zile). Interfața: Salarizare → Tahograful (descărcări / zilele șoferului /
  încălcările), panoul și „Țările din tahograf” în foaia de parcurs; `docs/ro|ru/transport.md` secțiunea 4. Verificat: 279 de teste
  (fișiere G1 / G2v2 construite după specificație), typecheck, build. **De verificat:** pe fișiere .ddd reale (G1, G2, G2v2); fără card =
  odihnă; compensarea (prima odihnă ≥ 9 h + deficit); termenul de 28 de zile în RM; pachetul de mobilitate UE neaplicat. Reparat după capturi: odihna tăiată
  de marginea datelor (începutul / sfârșitul descărcării) nu mai e judecată ca „redusă”; zilele se opresc la ora descărcării.
- **Instrucțiunea pentru firma de transport** — gata (2026-11-24, cerută de Anatol: de la angajat, acte, ordin, vehicul, constante, cursă,
  diurnă, tahograf — până la salariu; Word de descărcat + video care rulează într-o filă nouă, din program): `app/docs/files/`
  (`transport-instructiune.docx`, 28 de pagini, 28 de capturi; `transport-video.webm`, ~4 min, VP9, subtitrări), servite public de
  `/api/help/files/<nume>` (Word ca atașament, video cu Range), legate din Ajutor → Transportul (RO / RU). Se refac cu
  `app/tools/ghid-transport/` (copia de probă cu date demo, Playwright, docx) — README acolo. Instalate pe site cu pasul (b)
  (2026-11-25, fără copie, baza demo).

- **S6b „transportul”, pasul (c) „GPS + KPI” — gata** (2026-11-25, hotărât de Anatol: furnizor GPS cu API — numele și accesul le
  cere de la firmă; KPI: consumul față de normă, daunele și amenzile, actele la timp, tahograful; prima = baza × punctajul). **Foaia
  de parcurs**: `fuel_out` / `fuel_added` / `fuel_in` → `fuel_used` (`fuel_source` tank / manual / gps), `fuel_norm_l` = norma
  vehiculului × km × (1 + `fuel_adj_pct`), `docs_submitted` (termenul — întoarcerea + `kpi_docs_days`). **GPS** (`apps/transport/gps.py`):
  `Vehicle.gps_id`, `GpsDay` (vehicul + zi: km, timpii, pornire / oprire, combustibil, kilometraj, țări, sursa), importul din fișier
  (Excel / CSV, antetul RO / RU / EN al exporturilor obișnuite, doar coloanele din fișier se actualizează), în foaie — km GPS față de
  foaie (avertisment peste `gps_km_tolerance_pct` 5), „Km din GPS”, consumul din GPS când foaia nu-l are; **conectorul API — nefăcut,
  până se știe furnizorul** (va scrie `GpsDay` cu `source`). **Evenimentele** (`DriverIncident`, din vina șoferului). **KPI**
  (`apps/transport/kpi.py`): `KpiIndicator` (sursa fuel / incidents / documents / tacho / manual, liniar / prag, 100 % la / 0 % la —
  seed CONSUM, DAUNE, AMENZI, ACTE, TAHO, EVAL), `KpiScheme` + `KpiSchemeItem` (ponderi, baza fixă / % din salariu, prag, pe timpul
  lucrat; seed SOFERI cu baza 0), `KpiAssignment` (funcția sau raportul, de la / până la), `KpiSheet` / `KpiLine` (seria KP; fără date
  — indicatorul iese din punctaj; valorile de mână în `overrides`; aprobarea fixează) → tipul **KPI** (auto `kpi`, × partea lucrată cu
  `prorate`); tiparul `kpi_sheet`. **Reparat în importul Excel comun**: `_norm` păstrează chirilica (antetele RU nu se recunoșteau),
  CSV, unitățile în celule, data cu ora; `ExcelImport` cu `accept`. Interfața: Salarizare → GPS-ul vehiculelor / Evenimentele șoferilor /
  KPI-ul șoferilor, Setări → Indicatorii KPI / Schemele KPI, foaia de parcurs; `docs/ro|ru/transport.md` secțiunile 5–8. Verificat:
  288 de teste, typecheck, build. **De verificat:** un export GPS real al firmei; valorile KPI din regulamentul ei; prima KPI în
  salariul mediu. **Urmează:** conectorul GPS (furnizorul), apoi S6 aviația.

## Următorii pași (de aici pornește sesiunea următoare)

0. **Deschiderea**: (a) ~~Public Hostname~~ — făcut. (b) ~~asistentul de
   instalare~~ — făcut 2026-11-24, cu date demo (vezi Status). (c) proba
   restaurării (`./restore-check.sh`) după prima copie cu aplicația instalată.
1. **Sursa adevărului pentru cod**: `app/` din acest depozit; schimbările se fac
   și se comit aici.
2. **Ce nu e „la cauza rădăcină” încă** (moștenit de la SCTO): (a) conexiunea la
   bază din `POSTGRES_*` când `config.json` lipsește (acum: asistentul); (b)
   `run.py` în loc de `launcher.py` în `Dockerfile` (o singură bază, fără proxy
   intern și fără `/__platform`); (c) `SECURE_PROXY_SSL_HEADER` pentru
   `X-Forwarded-Proto` dacă aplicația va construi URL-uri absolute; (d)
   `read_only` + `tmpfs` pe `app`.
3. **IP-ul real nu ajunge în aplicație**: `AuditLog.ip` și `UserSession.ip` sunt
   mereu `127.0.0.1` — waitress 3 șterge `X-Forwarded-For` de la un proxy
   nedeclarat, iar `run.py` / `launcher.py` nu dau `trusted_proxy`. Repararea,
   în `app/`: baza cu `trusted_proxy="127.0.0.1"` + `trusted_proxy_headers`,
   launcher-ul cu proxy de încredere doar când e în spatele unuia (variabilă de
   mediu), `audit.client_ip` pe `REMOTE_ADDR`. nginx trimite deja doar IP-ul
   real ca `X-Forwarded-For`.
4. **Limita pe cont la autentificare** (blocare după N parole greșite) — în
   aplicație; nginx limitează doar pe IP.
5. **Copia în afara serverului** — de hotărât de Ion unde; acum `./backups` e pe
   aceeași mașină. Web Analytics din Cloudflare trebuie oprit pentru
   `cai-cadre.integratii.md` (CSP-ul blochează scriptul lui).
6. Actualizează **Status**, README și `docs/instalare.md` în același commit cu
   fiecare pas.

## Serverul (partajat) — reguli nenegociabile

Aceeași mașină găzduiește scto, cota0, crm-transport, crm-cargo, plinap, sbora,
lear, etichete, salon, tolea, nextcloud, immich. Modelul lor e standardul; nu
inventa alt model — șabloanele sunt în `/srv/projects/tolea` și
`/srv/projects/salon` (`docker-compose.yml`, `backup.sh`, `deploy/nginx/`,
`.github/workflows/`).

- **Intrarea publică e doar tunelul Cloudflare.** TLS se termină la margine.
  nginx publică exclusiv `127.0.0.1:${NGINX_PORT}`. Niciun serviciu nu leagă
  `0.0.0.0` — ar permite cereri pe lângă margine cu `X-Forwarded-Proto`
  falsificat. Aplicația se expune doar în rețeaua compose (`expose`, nu
  `ports`), nginx e singurul în fața ei.
- **Orice rețea Docker nouă primește subrețea explicită** din `10.219.0.0/24`
  (liber: de la `10.219.0.40` în sus) — plajele implicite sunt epuizate.
- **Numele proiectului compose se fixează** (`name: cai-cadre`), volumele au
  prefixul `cai-cadre-`. Nu crea un al doilea fișier compose cu aceleași nume de
  servicii fără propriul `name:` — un `up` ar recrea containerele celuilalt.
- **Fiecare serviciu**: `restart: unless-stopped`, plafon de jurnale
  (`<<: *logging`), `healthcheck`, `TZ` din `.env`, `no-new-privileges`;
  `read_only` + `tmpfs` unde programul nu scrie pe disc.
- **Secretele stau doar în `.env`** (660, grupul `proj-cai-cadre`, nu intră în
  git). Orice variabilă nouă se documentează în `.env.example` în același
  commit. Aplicația refuză să pornească cu valori de dezvoltare în producție
  — fail fast, nu rulare nesigură.
- **Tunelul** pornește singur când `TUNNEL_TOKEN` nu e gol (`.env` are
  `COMPOSE_PROFILES=${TUNNEL_TOKEN:+tunnel}`); fără token stiva merge local.
  Nu pune `${TUNNEL_TOKEN:?}` în compose — e verificat și cu profilul oprit.
- **Deploy = `git pull && docker compose up -d --build`.** Migrările rulează
  la pornirea containerului aplicației; fără pași manuali de deploy.
- **Baza are backup zilnic** (serviciu `backup` + `backup.sh`). Fișierele
  încărcate stau în volumul `cai-cadre-media`, niciodată în copia de lucru, și se
  servesc doar prin endpoint-uri autorizate.
- **nginx e montat ca folder** (`./deploy/nginx:/etc/nginx/conf.d:ro`): după
  o editare ajunge `docker compose exec web nginx -t && docker compose exec
  web nginx -s reload`. Nu monta fișierul singur — editorul scrie alt inode
  și containerul rămâne cu vechiul.
- **Nimic global pe gazdă**: fără `apt`, `systemd`, `sudo`, servicii în
  afara compose. Toolchain de dezvoltare (Node, Python, JDK) — în `~/.local`.
- **Porturi ocupate pe gazdă** (2026-11-17): 3000, 3010, 3020, 3030, 3040, 3100,
  3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900 (scto), 3950, **3960 (cai-cadre)**, 4000, 4100–4103, 5432, 5433,
  5440, 6379, 8080–8082, 2283. Verifică `ss -ltn` înainte să alegi un port
  de dezvoltare; leagă-l pe `127.0.0.1`.
- Testele se rulează în containere de unică folosință (`python:*-slim`,
  `node:*-slim`) cu proiectul montat `:ro`, sau pe un Postgres de test
  separat (fără port pe gazdă) — niciodată pe baza stivei `cai-cadre`.

## Structura depozitului

```
app/                 CAI CADRE 1.6.0 (Dockerfile, backend/ Django, frontend/ React, docs/ ro|ru + files/ (ghidurile Word / video), PLAN.md)
docs/                instrucțiuni pentru cine configurează serverul (instalare.md)
docker-compose.yml   stiva de pe server (db, backup, app, web, cloudflared)
backup.sh, backups/  copia zilnică: dump + fișierele instanței + oglinda media; copiile nu intră în git
restore.sh           restaurarea dintr-o copie (serviciul `restore`, profilul `restore`)
restore-check.sh     proba restaurării într-un proiect compose izolat (`cai-cadre-proba`)
deploy/nginx/        default.conf — proxy spre `app:8000`, /health, ce se închide din internet, CSP, limita la login
deploy/nginx-test.sh verificarea comportamentului nginx (nginx + aplicație-ecou de unică folosință; și în CI)
deploy/db/           10-app-role.sh — rolul `caicadre_app` (fără superuser), la prima pornire a bazei
.env / .env.example  configurația serverului / șablonul ei
.github/workflows/   CI — compose, scripturi shell, nginx, pytest (app/backend), typecheck (app/frontend)
README.md            instrucțiuni de rulare pentru oameni
```

## Comenzi

```bash
docker compose config -q                # validează compose înainte de commit
docker compose up -d --build            # pornește / actualizează stiva
docker compose ps                       # toate: running / healthy
docker compose logs -f app              # jurnale (sau web, db, backup, cloudflared)
curl -s http://127.0.0.1:3960/health    # verificare locală, fără tunel
docker compose exec backup cai-cadre-backup  # copie acum (baza + instanța + media)
./restore-check.sh                      # proba restaurării ultimei copii, izolat
docker compose stop app && docker compose run --rm restore AAAA-LL-ZZ && docker compose up -d   # restaurarea
./deploy/nginx-test.sh && docker compose exec web nginx -t && docker compose exec web nginx -s reload   # după o editare în deploy/nginx
docker compose up -d --no-deps --force-recreate backup   # după o editare în backup.sh (montat ca fișier)
```

## Git

- Ramura `main`, remote `origin` = `git@github.com:ivan1995ivan/cai-cadre.git`
  (privat). Fiecare împinge cu cheia lui SSH (`ssh -T git@github.com` arată
  contul); contul trebuie să fie colaborator la depozit — îl adaugă Ion.
- Fiecare push pornește CI-ul (GitHub Actions, `.github/workflows/ci.yml`);
  rezultatul — în fila **Actions** a depozitului.
- Commit-uri mici, cu mesaj care spune CE s-a schimbat pentru utilizator,
  nu „fix”/„wip”.
- Niciun secret, `.pdf`, `node_modules`, `dist`, `backups` în git —
  `.gitignore` le acoperă; nu-l slăbi.
- Depozitul e `core.sharedRepository=group`; înainte de prima comandă git
  fiecare rulează o dată
  `git config --global --add safe.directory /srv/projects/cai-cadre`.
- Identitatea de commit NU e setată în depozit (îl folosesc doi oameni):
  fiecare o are global, în `~/.gitconfig`-ul lui. Nu rula
  `git config user.name/user.email` local — ai semna și commit-urile
  celuilalt.
- Înainte de commit: `docker compose config -q`, testele trec, verificarea
  de drepturi de mai jos nu afișează nimic.

## Drepturi de fișiere

Folderul are grupul `proj-cai-cadre` (Ion + Anatol), setgid și ACL implicit —
fișierele noi sunt automat ale grupului, scriibile de amândoi. Nu rula
`chown`/`chmod` recursive, nu folosi `sudo`. Dacă o comandă din Claude Code
dă „Operation not permitted” / „Permission denied”, sesiunea shell a pornit
înainte de adăugarea în grup (`id` nu arată `proj-cai-cadre`): rulează comanda
prin `sg proj-cai-cadre -c ...` sau reconectează-te.

**Capcană verificată pe acest server (2026-09-18):** `mkdir` din shell este
cel din uutils coreutils și face un `chmod` după creare, care **șterge
setgid-ul** de pe folderul nou. Fișierele create apoi în el primesc grupul
personal al autorului, iar celălalt om nu mai poate scrie. (Python
`os.mkdir`, git și Docker nu au problema.) De aceea:

- foldere noi din shell: `mkdir -m 2775 cale` (sau `install -d -m 2775`),
  dintr-o sesiune care are grupul (`id`), altfel prin `sg proj-cai-cadre -c "..."`;
- la copieri / dezarhivări mari, la final:
  `sg proj-cai-cadre -c 'chgrp -R proj-cai-cadre DIR && chmod -R g+rwX DIR && find DIR -type d -exec chmod g+s {} +'`
  — doar pe folderul adus, nu pe tot proiectul;
- `mkdir -p -m 2775 a/b/c` pune modul doar pe ultimul (`c`); `a` și `b`
  rămân fără setgid — creează-le pe rând sau repară cu `find … chmod g+s`;
- verificare înainte de commit (trebuie să nu afișeze nimic):
  `find . -path ./.git -prune -o \( -not -group proj-cai-cadre -o -type d -not -perm -2070 \) -print`

## Cum se lucrează

- Doi oameni pot fi la tastatură: **Anatol** și **Ion** (Ion administrează
  și serverul, panoul Cloudflare și `TUNNEL_TOKEN`). Limba: **română cu
  Anatol**, rusă cu Ion.
- Se rezolvă corect și până la capăt, la cauza rădăcină — fără variante
  „rapide” puse alături de cea corectă. Un exemplu trecut nu e dovadă:
  verifică toate cazurile relevante (gol/NULL, limite, primul/ultimul).
- Dacă lipsește ceva ce are doar omul (fișiere, imagini, accesuri, o decizie
  de produs sau vizuală) — oprește-te și cere; nu fabrica un înlocuitor.
  Fișierele trimise în chat nu există pe disc: cere să fie puse în proiect.
- Subagenții de review/audit primesc doar unelte read-only; după orice agent
  cu drept de scriere verifică `git status` / `git diff` — poate a modificat
  sau a anulat ceva în tăcere.
- Fiecare etapă livrată vine cu instrucțiuni în `docs/`: una pentru omul
  care lucrează cu ecranul, una pentru cel care instalează / configurează.
  Se scriu în română și se actualizează în același commit cu funcția.
- Actualizează acest fișier și README-ul în același commit cu schimbarea pe
  care o descriu.

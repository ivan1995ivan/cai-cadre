# Ce e nou

## Etapa S6b, pasul (c): GPS-ul vehiculelor și KPI-ul șoferilor

- **Combustibilul în foaia de parcurs**: rezervorul la plecare, alimentat, rezervorul la întoarcere — consumul se socotește singur
  (altfel de mână sau din GPS); consumul normat din norma vehiculului × km, cu corecția (iarna, munți); data predării actelor cursei.
- **Salarizare → GPS-ul vehiculelor**: importul raportului zilnic exportat din orice sistem GPS (Excel sau CSV; antetul în
  română, rusă, engleză se recunoaște; „ID în GPS” în fișa vehiculului); km, timpii, combustibilul, țările pe zile. În foaia de
  parcurs — km din GPS față de km din foaie, butonul „Km din GPS”, avertismentul la diferență.
- **Salarizare → Evenimentele șoferilor**: daunele, accidentele, amenzile, reclamațiile (din vina șoferului — în KPI).
- **Salarizare → KPI-ul șoferilor** (seria KP): fișa lunii cu șoferii care au schemă KPI — consumul față de normă, daunele,
  amenzile, actele la timp, încălcările de tahograf, evaluarea de mână; nota fiecărui indicator, punctajul ponderat, prima = baza ×
  punctajul; valorile se pot scrie de mână; aprobată — rândul **KPI** în salariul lunii (proporțional cu timpul lucrat, dacă schema o
  cere); tiparul cu semnăturile.
- **Setări → Indicatorii KPI / Schemele KPI**: ce se măsoară și cum se notează (liniar sau prag); baza primei (sumă fixă sau % din
  salariul de funcție), ponderile, pragul, cui se aplică (funcția sau raportul de muncă). Schema-model SOFERI are baza 0.
- **Importul din Excel** (toate): se citesc și antetele în rusă (literele chirilice se pierdeau la comparare), valorile cu
  unitatea („640,5 km”) și data cu ora.

## Etapa S6b, pasul (b): tahograful — cardul șoferului și limitele de conducere / odihnă

- **Instrucțiunea pentru firma de transport**: documentul Word (de la angajat la salariu, cu capturi) și video-ul — în Ajutor (F1) →
  Transportul.
- **Salarizare → Tahograful**: se încarcă fișierele descărcate de pe **cardul de conducător** (.ddd, generația 1 și „smart”);
  fiecare se citește (activitățile pe minute, km, vehiculele, țările, la „smart 2” și trecerile frontierei / încărcările) și se
  leagă singur de angajat — după numărul cardului din dosar sau după nume și data nașterii (cardul se adaugă atunci în dosar).
  Originalul se păstrează pentru control.
- **Zilele șoferului**: luna zi cu zi, cu bara celor 24 de ore și totalurile (conducere, altă muncă, disponibilitate, odihnă, fără
  card), km, țările, vehiculele.
- **Încălcările** limitelor (CTR 150/2014, AETR art. 6–8): conducerea continuă 4 h 30, zilnică 9 / 10 h, săptămânală 56 h, două
  săptămâni 90 h, odihna zilnică (11 h / 3 + 9 / redusă 9 h de cel mult 3 ori), săptămânală (45 / 24 h, după cel mult 6 × 24 h,
  compensarea reducerii).
- **În foaia de parcurs**: timpii de pe card în timpul cursei, încălcările ca avertismente; butonul „Țările din tahograf” pune
  țările cursei din trecerile frontierei (tahograful „smart 2”).
- **Alertele**: descărcarea cardului la 28 de zile; încălcările din ultimele 14 zile.

## Etapa S6b, pasul (a): transportul — cursele, diurnele șoferilor, plata pe km

- **Modulul opțional „Transportul”** (Constante → Module, oprit implicit) — pentru transportatori, marfă și pasageri, în țară și
  internațional.
- **Setări**: vehiculele și remorcile; **tarifele pe km** cu istoric (după felul cursei, arie și vehicul — se ia rândul cel mai
  potrivit); **țările și diurnele** — 186 de țări cu normele pe zi din anexa nr. 2 la HG 10/2012 (redacția 2024).
- **Cursa (foaia de parcurs)** (*Salarizare → Curse*): șoferii, vehiculul, remorca, plecarea / întoarcerea, km din kilometraj,
  țările cu ora trecerii frontierei, încărcarea / descărcarea, masa; verificările (curse suprapuse, concediu în timpul cursei,
  segmentele); actele șoferului ca avertismente (permis, CPC, card tahograf, medical, ADR — tipuri noi de act); import din Excel;
  tiparul.
- **Diurna pe zile și țări** după HG 10/2012: șoferii până la 8 ore — 20 %, 8–24 de ore — 40 %, peste — 100 % pe zi cu norma
  țării de destinație (tranzitul sub 24 de ore — norma destinației), masa asigurată — 20 %, minimum 70 % în privat, cursul BNM.
- **Salariul**: **KM** (plata pe km, în comparația cu salariul minim), **DIURNA** (neimpozabilă), **DIURNAEX** (peste norme).

## Etapa S5b: fabrica — timpul fără producție, sporul vătămător, evidența globală, tichetele de masă

- **Staționarea și șomajul tehnic prin ordin** (tipurile noi „Staționare”, „Șomaj tehnic”, colective): perioada, cauza (din vina
  angajatorului — integral; fără vina părților — 2/3, nu sub salariul minim pe oră; din vina salariatului — neplătit), procentul;
  în pontaj singure ca **St / Șt** cu orele planificate; în salariu — **STATIONARE**, **SOMAJT** (CM art. 80, 80¹).
- **Ordinele colective**: „Adaugă subdiviziunea” (toți angajații secției într-un clic) și „La toate punctele” (aceiași parametri).
- **Garanția la neîndeplinirea normei** în acord (CM art. 161), pe raportul de producție: din vina angajatorului — media pe oră,
  fără vina părților — 2/3 din tariful categoriei; tipul **GARANT**.
- **Sporul pentru condiții vătămătoare** din subdiviziune / funcție (câmpul nou „Sporul vătămător, %”), plătit singur pe orele
  lucrate acolo — tipul **VATAM**; rândul personal NOCIV îl înlocuiește.
- **Evidența globală a timpului de muncă** (CM art. 99): perioada de calcul pe graficul de lucru (1–12 luni); suplimentarele —
  la sfârșitul perioadei, salariul — pentru norma lunii fără absențe.
- **Tichetele de masă** (*Salarizare → Tichete de masă*): borderoul pe luna lucrată, din pontaj (o zi — un tichet; în schimburi —
  ore ÷ 8, noaptea ÷ 7), numărul de mână, aprobarea, tiparul; partea peste 70 lei — în salariu (TICHET), reținută (TICHETN).
- **Reparat**: salariul celui angajat sau eliberat în lună se plătește pentru partea lui din norma lunii întregi (până acum —
  salariul întreg), iar salariul pe oră e salariul / norma lunii întregi; un raport de muncă în două tabele de pontaj (transfer
  în lună) intră în calcul cu orele din amândouă.

## Etapa S5a: producția — salarizarea în acord

- **Modulul opțional „Producția”** (Constante → Module, oprit implicit) — pentru fabrici și ateliere.
- **Grila tarifară** (Setări): tariful categoriei I și coeficienții categoriilor (sau tariful scris direct), cu „în vigoare din”.
- **Lucrările în acord** (Setări): unitatea, secția, bifa „progresiv” și **normele și tarifele cu istoric** — norma de timp sau de
  producție, categoria lucrării din grilă (tariful = tariful categoriei × norma de timp, CM art. 170) sau tariful pe unitate
  scris direct.
- **Brigăzile** (Setări): membrii cu coeficientul de participare (KTU), împărțirea sumei după ore × KTU sau și după tariful orar.
- **Rapoartele de producție** (Salarizare): individuale sau pe brigadă; cantitatea bună, **rebutul pe vinovați** (fără vină — ca
  produsul bun, parțial — la procentul din contractul colectiv, din vină — neplătit; CM art. 162), orele; membrii brigăzii
  „din brigadă”, cu orele din pontaj; import din Excel (lucrările, membrii); aprobarea fixează tarifele; tiparul.
- **Salariul**: tipurile **ACORD** (lucrările) și **ACORDP** (acordul progresiv pe treptele de îndeplinire a normei, din contractul
  colectiv); modalitatea de remunerare **„În acord”** — fără salariu de funcție, suplimentarele și noaptea din tariful orar al
  categoriei, sărbătorile — dublul câștigului în acord, completarea până la salariul minim; variabilele `OreNormate`,
  `OreAcord`, `IndeplinireNorma` în formule.

## Etapa S4b: tipurile de ore și remunerarea pe funcție

- **Tipuri de ore** (Setări): instruire, examinare (livrate) și ale dvs. (de ex. zbor) — grupa, legătura cu orele lucrate, pe
  zile sau pe lună, profilul, tipul de calcul.
- **Remunerarea pe fiecare raport de muncă**, cu istoric: salariu lunar / tarif orar / pe tipuri de ore / mixt; **tarifele pe
  tipuri de ore** cu **orele garantate** (minimul plătit: max(efective, garantate), redus după zilele fără raport, absențe și
  suspendare); din ordin (tabelul „Tarife pe tipuri de ore”, completat din tarifele-tip ale funcției) sau de mână.
- **Pontajul** cu coloanele tipurilor de ore: pe zile sau total pe lună, de mână sau din Excel; garantat / disponibil / efectiv
  / de plată; în tipar și în export.
- **Salariul**: tipul „Ore pe tipuri” cu explicația garanției; variabilele `Ore.COD`, `OrePlatite.COD`, `Garantat.COD`,
  `Tarif.COD` în formule.
- **Cumulul ≠ cumularea**: cumularea funcțiilor, suplinirea și interimatul pe același contract (CM art. 156) sunt înregistrări pe
  raportul de bază, cu plata lor (% din salariul propriu / al funcției cumulate, sumă fixă, pe ore); cumulul rămâne raport
  separat. „Plata pentru cumul (%)” veche s-a mutat singură în înregistrări.

## Etapa S3: formula în tipurile de calcul și acumulările planificate

- **Tipul de calcul „Formulă”**: o expresie scrisă de dvs. (`TarifOrar * OreNoapte * C.night_pct / 100`), cu variabilele din
  pontaj și din rândul angajatului, constantele `C.cod` și alte tipuri `[COD]`; verificarea pe loc cu poziția erorii,
  dependențele circulare respinse, ordinea de calcul după dependențe; **„Încearcă pe un angajat”** fără să se salveze
  nimic. Explicația rândului din calcul arată formula cu valorile ei.
- **Din ce se calculează** — coloana nouă la toate tipurile (și la cele automate: regula, cu valorile constantelor), plus
  impozitul, CNAM, CAS, media, plafonul neimpozabil și codul IPC; editorul grupează „Ce se impozitează”.
- **Tabelul „Acumulări și rețineri”** în ordinele de angajare, transfer, condiții, salariu, sporuri, cumul / suplinire și
  reținere: adaugă / modifică / oprește; la semnare intră în fila „Salariu”, anularea ordinului le întoarce. La angajare —
  din **acumulările-tip ale funcției**.
- **Documentul „Modificarea acumulărilor planificate”** (Salarizare) — pentru schimbările fără ordin: titlul executoriu,
  sindicatul la cerere, tichetele de masă; aprobarea și anularea aprobării, tiparul.
- **Fila „Salariu”**: sursa fiecărui rând (ordinul nr. / documentul nr. / de mână) cu legătura, istoricul rândurilor închise.
- **Scutirea** se aplică și angajatului al cărui singur raport aici e cumulul extern; cererea arată locul depunerii (de bază /
  prin cumul), și în tipar.

## Aspectul „Clasic de birou”
- Programul arată ca o aplicație de birou: **bara de titlu** (*CAI CADRE — întreprinderea*), **bara de meniu** (Fișier,
  secțiunile meniului principal, Ferestre, Ajutor; din tastatură cu **Alt**, săgețile, Enter, Esc), **bara de unelte**
  (Nou, Salvează — și Ctrl+S, Tipar, Excel, Reîmprospătează, Căutare, Ferestrele deschise — legate de fereastra activă),
  ferestrele deschise ca **file**, **bara de stare** (legătura cu serverul, utilizatorul, rolul, notificările, cine e
  online, versiunea).
- Ferestre gri deschis, câmpuri și tabele albe cu chenar subțire, rânduri dese cu grilă, rândul ales albastru, grupele de
  câmpuri în chenar cu titlu, dialoguri cu bară de titlu și OK / Anulare în dreapta jos; fără colțuri rotunde și animații.
- E **tema implicită** a instalărilor noi și a întreprinderii rămase pe vechea temă implicită; există și varianta
  **întunecată**. Celelalte teme (cu meniul în stânga) rămân de ales în Profil sau în Constante. Vezi
  [Aspectul programului](help:interfata).

## Etapa S1 (CAI CADRE pentru întreprinderi): fără funcțiile de spital — formarea, sănătatea, evidența militară, vechimea
- **Formarea profesională** în locul EMC și al atestării: registrul cursurilor și instruirilor cu orele, certificatul și
  **termenul lui de valabilitate**; alerta și raportul *Certificatele de formare care expiră*; planul anual se completează
  din certificatele care expiră în anul lui. Creditele EMC, normele lor, calendarul atestării și ordinul de conferire a
  categoriei au ieșit.
- **Sănătatea și securitatea în muncă**: periodicitatea examenului medical periodic **pe funcție / subdiviziune** (fila
  *Periodicitatea examenului*; 0 luni — fără examen periodic). Vaccinările și clasificatorul *Vaccinuri* au ieșit.
- **Evidența militară** e modul opțional, **oprit implicit** (Legea 112/2023): se pornește în *Constante → Module*. Oprit —
  pagina, fila din dosar, rapoartele și clasificatoarele militare nu apar.
- **Vechimea**: totală, în specialitate (stagiul bifat și munca de aici, orice funcție) și în întreprindere — fără „în
  sistemul sănătății”. Felul angajării „rezident” și **categoria de calificare medicală** (fila din dosar, importul, alerta,
  sporul) au ieșit.
- **Salarizarea**: tipurile predefinite VECH și CATEG (HG 837/2016) și GARDA nu se mai preîncarcă (cele nefolosite se șterg,
  cele folosite se dezactivează); NOCIV rămâne (Codul muncii, art. 139). Formula „pe trepte” rămâne, pe **vechimea totală**,
  pentru sporul de vechime din contractul colectiv al firmei.
- Graficul concediilor avertizează când pleacă deodată toți cei de aceeași funcție (fără avertismentul „toți medicii”).
- Rapoartele: au ieșit *Cadrele medicale (MS nr. 17)* și gruparea pe categoria de calificare din *Structura personalului*.
- Rolurile: **Șef de subdiviziune** (fost „Șef de secție”) și **Director / administrator**.

## Versiunea 1.6.0: Panoul funcțiilor, ca în 1C
- **Panoul funcțiilor** — se pornește în *Constante (instituția) → Module*. Secțiunile meniului stau **sus, ca file**, iar
  clic pe o secțiune deschide panoul ei: **Schema de lucru** (documentele secțiunii ca iconițe mari, cu săgeată de la
  documentul de bază la cel făcut din el), apoi **Registre**, **Clasificatoare** și **Rapoarte**. Meniul din stânga
  dispare; favoritele sunt sub butonul ★ din antet. Oprit — totul ca până acum.
- Fiecare vede în panou doar ce are în meniu: drepturile rolului și bifele lui. **Administrare** rămâne lista funcțiilor ei.
- Fundalul panoului e gri deschis, benzile blocurilor și legăturile spre registre, clasificatoare și rapoarte — gri închis cu
  text alb. Pe telefon meniul rămâne cel obișnuit.

## Versiunea 1.5.1: fluturașii din îndreptare, Esc și ferestrele deschise, adeverința pentru bancă
- **Fluturașii** (fișele de calcul) se fac acum din **îndreptarea spre plată pe salariu**, pentru angajații ei: tiparul,
  PDF-ul și trimiterea pe e-mail (din îndreptarea aprobată sau achitată). Din calcul butoanele au ieșit.
- **Esc** închide pagina deschisă (forma sau lista) și fila ei; cu modificări nesalvate întreabă „Salvați
  modificările?” (Da / Nu / Anulare).
- **`` Alt+` ``** — lista **Ferestrele deschise**: săgețile sau `` Alt+` `` mută, Enter deschide, cifra 1–9 deschide direct, Esc
  închide lista.
- **Adeverința privind salariul (pentru bancă)** în fișa angajatului → *Tipar*: ultimele 3, 6 sau 12 luni ori un interval
  de luni — pe fiecare lună brutul, CNAM, impozitul, alte rețineri și netul, cu totalul și media lunară.
- **Ordinele**: unul sau mai multe **temeiuri legale** (și la tipul ordinului); preambulul se compune din ele. Antetul și
  punctele — ca în 1C, pe două coloane, cu eticheta în stânga.
- **Esc** întreabă „Salvați modificările?” pe toate formele cu *Salvează* (ordinul, fișa angajatului, statele, setările).
- **Rapoarte**: căutare după denumire și descriere.
- **Cine e online, în timp real**: pagina se actualizează singură, iar în antet **● N** arată cine are programul deschis.
- În tabele numele și numerele nu mai sunt butoane colorate: rândul se deschide cu dublu clic.
- Adeverințele iau numărul la **Tipărește**, nu la previzualizare. Bifele din fereastra de tipar a formelor de cadre au
  denumiri (*Cu IDNP*, *Cu salariul*…).

## Versiunea 1.5.0: salariul în două documente — calculul și îndreptarea spre plată
- **Calculul salariului** are acumulările, celelalte rețineri și CAS al angajatorului. **CNAM, scutirea și impozitul pe
  venit nu mai sunt în calcul**: se rețin la plată, în **îndreptarea spre plată** (fostul stat de plată; meniul
  *Îndreptările spre plată*).
- Îndreptarea pe salariu se face **în baza calculului aprobat** (butonul *Îndreptare spre plată* din calcul: doar angajații
  lui) sau **pe sold** (restul lunii din toate calculele aprobate). Impozitele se socotesc pe tot venitul plătit în lună,
  minus ce s-a reținut deja din avans — avansul și salariul împreună rețin exact impozitul lunii. Coloana nouă: scutirea.
- Calculul și îndreptările lui sunt legate: în titlul calculului — îndreptările făcute din el, în titlul îndreptării —
  calculul de bază (clic — se deschide). Calculul cu o îndreptare aprobată nu se redeschide.
- **Formele**: titlul cu numărul și data, starea; **data se scrie de mână** în antet (în îndreptare — și felul, baza, luna,
  modalitatea), apoi *Salvează*; acțiunile în dreapta sus, **✕** ultimul închide forma și fila ei. La plecarea din formă cu
  modificări nesalvate programul întreabă **„Salvați modificările?”** (Da / Nu / Anulare).
- **Fișa personală anuală (anexa 8), IPC21 (tabelul 1) și IALS21** se fac doar din îndreptările **achitate**. Datoriile
  salariale se arată înainte de impozit (brutul calculat minus brutul achitat).
- La actualizare, calculele de dinainte își păstrează sumele brute și reținerile; rândurile de impozit, CNAM și avans din
  ele se scot (impozitele reținute sunt deja în plățile achitate).

## Versiunea 1.4.1: setările pe rol, foile de boală continuate
- **Setările se bifează pe rol**: în *Roluri și drepturi → Meniul principal*, la sfârșit, e grupa **Setări**. Setarea
  debifată nu apare în lista *Administrare → Setări* a rolului; cu toate debifate nu apare nici rândul **Setări**.
- **La actualizarea de la 1.3** favoritele, meniul principal salvat și bifele de meniu ale rolurilor trec o dată pe
  setările noi: rolul vede ce vedea înainte. Favoritele vechi (*Clasificatoare*, *Grafice de lucru și gărzi*,
  *Setările salariului*) poartă denumirea setării și se scot cu steluța; funcțiile puse în grupa Setări a unei secțiuni
  (de ex. *Import din Excel*) rămân în secțiunea lor.
- **Foaia de boală continuată** de alta e încheiată: are eticheta *continuat* în loc de *deschis*, nu mai e scrisă cu
  albastru și nu mai apare la *Doar cele deschise*.
- Rândul marcat pentru ștergere rămâne gri și tăiat și în tema întunecată.
- Filele din bara de jos poartă denumirea de acum a paginii, în limba interfeței.
- Indicațiile din ecrane trimit la *Administrare → Setări → Roluri*.

## Versiunea 1.4.0: toate setările într-un singur loc, culoarea rândurilor după stare
- **Administrare → Setări**: toate setările programului pe o singură pagină, în ordine alfabetică, cu căutare după
  denumire (fără diacritice: „campuri” găsește *Câmpuri obligatorii*); Enter deschide setarea rămasă singură.
- Din secțiunile meniului a ieșit grupa **Setări**: în fiecare secțiune rămân **Registre** și **Rapoarte**. Utilizatorii și
  rolurile s-au mutat și ele la Setări.
- Fiecare clasificator e o setare separată (Funcții CORM, Tipuri de ordine, Vaccinuri…); graficele de lucru, turele,
  calendarul de producție, evidența concediilor, tipurile de calcul, constantele salarizării, datele plătitorului pentru
  raportări, alertele și poșta — la fel. Favoritele și filele cu adresele vechi duc singure la setarea nouă.
- **Culoarea rândurilor după stare** în registre (ordine, cereri, concedii, grafice, pontaje, calcule, plăți, state,
  atestări): **albastru** — documentul e în lucru, **verde** — e încheiat (semnat, aprobat, închis, achitat), negru — în
  rest (ciornă, anulat, respins).

## Versiunea 1.3.0: marcarea pentru ștergere, ca în 1C
- **Șterge** din liste și din documente doar **marchează** obiectul: rămâne în bază, tăiat în liste, nu se mai alege în
  câmpuri și nu se mai modifică; **Scoate marcajul** îl readuce. Documentul marcat nu mai contează în calcule (pontajul,
  foaia de boală, formarea, examenele).
- **Administrare → Ștergerea obiectelor marcate**: verificarea legăturilor (unde e folosit fiecare obiect) și ștergerea de
  tot doar a obiectelor pe care nu le mai folosește nimic din bază.
- Butonul de marcare și în calculul salariului, plată, graficul gărzilor, pontaj, graficul concediilor, planul de formare
  și în dosarul candidatului.

## Versiunea 1.2.1: fișa scurtă și echipamentul de lucru
- **Fișa scurtă în lista angajaților**: la trecerea mouse-ului pe nume — fotografia, vârsta, vechimea (în instituție,
  totală, în sănătate), raporturile de muncă, categoria, absența de azi, concediul disponibil.
- **Mărimile echipamentului de lucru** în dosar (îmbrăcăminte, încălțăminte, înălțime), în importul din Excel și raportul
  *Mărimile echipamentului de lucru* pe secții, cu numărul de bucăți pe mărimi.

## Versiunea 1.2.0: salarizarea — corectări, impozitul la achitare, fluturașii pe e-mail
- **Corectarea de mână a oricărei sume** din calculul salariului, inclusiv **impozitul, CNAM și CAS**; impozitele se refac
  din sumele corectate; „Revine la suma calculată” șterge corectarea.
- **Impozitul se reține la achitare**: în statul de plată — brutul, CNAM, impozitul și suma de plată pe fiecare angajat; la
  avans se reține din avans, la salariu doar diferența. Brutul, netul sau impozitele se corectează de mână.
- **IPC21 (tabelul 1)** și **fișa personală anexa 8** (forma 2018) — după datele achitării.
- **Fluturașii în PDF** și **pe e-mail**: fiecărui angajat o arhivă ZIP cu parolă — ultimele 5 cifre ale IDNP.
- **Cartea privind salariul** (fișa de evidență a retribuției), ca în POLARIS: pe angajat și pe luni, cu toate acumulările
  și reținerile, Excel și tipar.

## Versiunea 1.1.0: din CRM acoperiș gard — meniul, alegerea, formele
- **Meniul pe grupe**, ca în 1C: în fiecare secțiune **Registre**, **Rapoarte** și **Setări**; rapoartele secțiunii se
  deschid direct din meniu (Angajați → Rapoarte → Mișcarea cadrelor). Aceeași funcție poate sta în mai multe locuri;
  în editorul meniului — lista **Funcții neafișate**. Cu meniul în stânga se vede tot arborele.
- **Închide toate** în bara ferestrelor deschise.
- **Alegerea angajatului**, ca în 1C: scrieți numele sau nr. de tabel, ori apăsați **…** — lista angajaților cu subdiviziunea,
  funcția și starea, filtrul pe subdiviziune și pe cei care lucrează acum (la ordinele colective — mai mulți deodată).
- **Alegerea subdiviziunii** peste tot ca arbore, cu căutare și butonul **…** (structura instituției).
- **Forma** după gustul fiecăruia, ca în 1C: în dosarul angajatului, raportul de muncă, ordin, concediu, foaia de boală,
  formare, atestare, utilizatori, subdiviziuni și clasificatoare — grupe, ordinea, lățimea și câmpurile ascunse; pentru
  dvs. sau, de administrator, pentru toți.

## Versiunea 1.0.0: prima versiune a CAI CADRE
- **Instituția**: subdiviziunile, statele de personal cu versiuni și ocuparea posturilor, clasificatoarele (cu butonul
  „…” la fiecare câmp).
- **Angajații**: dosarul electronic (fișa MR-2), mai multe raporturi de muncă cu norma în procente, vechimea, importul din Excel.
- **Ordinele** de personal cu efectul la semnare și registrul lor.
- **Concediile** (soldul, graficul, cererile, foile de boală) și **timpul de muncă** (grafice, gărzi, pontaj).
- **Salarizarea**: calculul, plata, IPC21 / IALS21 / IRM19 în Excel și XML.
- **Formarea și atestarea** (EMC, creditele, calendarul atestării, planul anual), **sănătatea în muncă** (examene,
  vaccinări, instructaj SSM), **evidența militară**.
- **Termene și alerte** cu rezumatul pe e-mail, **panoul de start**, **catalogul de rapoarte**.
- **Cabinetul angajatului**: datele proprii, ordinele cu „am luat cunoștință”, cererile, fișele de calcul.
- **Limbile sistemului** (RO / RU / EN) se aleg în Constante.

Instrucțiunea pentru fiecare ecran se deschide cu **?** din antet (sau F1).

# Plan — CAI CADRE (evidența cadrelor și salarizarea pentru instituții medicale)

> Versiunea 2 · 2026-10-21 · document de lucru, se actualizează pe parcurs
>
> **Decizii confirmate (v2, 2026-10-21):** numele produsului **CAI CADRE** · instituția-pilot **IMSP Spitalul Clinic de
> Traumatologie și Ortopedie** (Chișinău, bd. Ștefan cel Mare 190, 160 de paturi) · **nu există bază 1C** la ei — se face
> **instrument de import din Excel** (angajați, secții, funcții, state, solduri de concediu, solduri salariale) · interfață
> **RO / RU / EN** · **modulul Salariu intră în produs**, pornit sau oprit din Constante la livrare (bifa „cu / fără salariu”) ·
> formularele oficiale se iau din legislația în vigoare (§5.12.6) · ordinea de lucru: Etapa 0 → … → Salariu după Etapa 4.
>
> **Stare:** Etapa 0 — **gata** (2026-10-21): scheletul copiat din CAI ERP Vânzări și curățat (fără clienți, vânzări, stoc,
> producție, Telegram, schimb între firme); aplicațiile `users, core, printing, setup, help`; catalogul modulelor de cadre în
> `users/registry.py` (7 roluri predefinite: administrator, șef RU, inspector RU, director, șef de secție, contabilitate, angajat);
> meniul cu secțiunile Instituția / Angajați / Ordine / Concedii și timp / Salarizare / Formare / Rapoarte / Administrare (modulele
> arată „în curând” cu etapa lor); limba EN (cheile lipsă cad pe RO); seriile de numerotare pentru ordine și documente; tipurile
> formelor de tipar; migrări noi; port 8030, date în `%ProgramData%\CAI-Cadre`, porturi interne 8701+, installer `cadre-setup`.
> Verificat: `npm run typecheck`, `manage.py check`, instalarea prin asistent (SQLite), autentificarea și API-urile de bază.
>
> Etapa 1 — **gata** (2026-10-21): aplicația `org` — clasificatoarele (funcții CORM, specialități, temeiuri legale din Codul
> muncii și actele MS, **47 de tipuri de ordine** pe grupe A–G cu registrul de numerotare, efectul la semnare, temeiul și IRM19;
> categorii de calificare, studii, acte, rudenie, motive de încetare, sancțiuni, tipul angajării, evidență militară); subdiviziunile
> ca arbore (paturi, condiții vătămătoare, concediu suplimentar); **statele de personal pe versiuni** (ciornă → aprobat → versiune
> nouă / anulat, diferențele față de versiunea anterioară, totaluri și efectivul-limită pe categorii); **ocuparea posturilor**
> (se umple din Etapa 2 prin `services.OCCUPANCY_PROVIDERS`); **importul din Excel** comun (`core/excel_import.py`: șablon,
> încercare, import într-o tranzacție) pentru funcții, specialități, subdiviziuni și rândurile statelor; tiparul statelor cu
> **Stema de Stat** (SVG) și fondatorul în antet, RO / RU / EN; Constante: fondatorul, șeful RU, Stema, **bifa „cu / fără
> salariu”** (ascunde meniul Salarizare). Limba EN în tot antetul, profil, intrare și asistent. Verificat: 16 teste, typecheck,
> build, proba de capăt-la-capăt pe server (instalare, import, aprobare, versiune nouă, tipar) și capturi ale ecranelor.
> Codurile CORM ale funcțiilor de spital (fără cod) și articolele temeiurilor fără număr se completează la instalare.
>
> Etapa 2 — **gata** (2026-10-22): aplicația `staff` — **dosarul angajatului** (persoana, acte cu termen și scanări, familia,
> studiile, categoriile de calificare, stagiul anterior, evidența militară, lista de verificare la angajare / eliberare —
> preluată din `CecList` din 1C); **raporturile de muncă** (de bază, cumul intern / extern, rezident, suplinire) cu **istoric
> „din data”** (modificare, suspendare, reluare, încetare; schimbările cu dată în viitor intră în vigoare prin sarcina de noapte;
> suplinirile încetează odată cu raportul suplinit); **vechimea** calculată (totală, în sănătate, în specialitate, în instituție;
> perioadele suprapuse o singură dată); **ocuparea posturilor** din statele de personal se umple acum cu angajații (CIM suspendat =
> temporar vacant); **vizibilitatea pe secții** (șeful de secție vede subdiviziunile lui, „echipa” = cu sub-secțiile);
> **datele sensibile** ascunse după drept (IDNP, acte, familie, salariu) — inclusiv la salvare; **jurnalul accesului** la dosar
> (Legea 133/2011); registrul **contractelor** cu termenele care expiră; **importul din Excel** pentru angajați (cu raportul de
> muncă, cumul pe rânduri separate, reimport fără dubluri), acte, familie, studii, categorii, stagiu; pagina **Import din Excel**
> cu pașii în ordine; tipar: **fișa personală MR-2**, **adeverința de la locul de muncă** și **adeverința de vechime** (numerotate),
> **lista angajaților** — toate cu Stema (antet comun `{% gov_header %}`). Verificat: 28 de teste, typecheck, build, proba pe server
> (20 de angajați fictivi importați, ocuparea, tiparele) și capturi ale ecranelor. Forma exactă a fișei MR-2 se ajustează după
> exemplarul de la SCTO.
>
> Etapa 3 — **gata** (2026-10-22): aplicația `orders` — ordinul (individual sau colectiv) cu punctele lui, **47 de tipuri** cu
> textul-model al punctului (editabil în clasificator), **numerotarea pe registre și an** (125-p, 38-c, 12-d, numere manuale,
> numerele lipsă semnalate), **semnarea aplică efectele** într-o singură tranzacție: angajare, transfer, modificarea normei /
> salariului / condițiilor, prelungirea CIM, suplinire / cumul / interimat, suspendare / reluare, încetare (cu motivul), toate
> concediile și deplasările (aplicația `leave`, cu suprapuneri verificate; concediul de îngrijire a copilului suspendă CIM),
> rechemarea din concediu, premii și ajutor material, sancțiuni (stinse după un an, ridicare înainte de termen), conferirea
> categoriei, aprobarea statelor de personal; **anularea prin ordin** întoarce efectele; **calendarul sărbătorilor** din Codul
> muncii (Paștele ortodox calculat) — concediile în zile calendaristice fără sărbători; „Am luat cunoștință”; tipar: **ordinul**,
> **extrasul**, **registrul ordinelor**; fila „Ordine și absențe” în fișa angajatului; șeful de secție vede ordinele oamenilor lui.
> Verificat: 41 de teste, typecheck, build, proba pe server (angajare, concediu colectiv, transfer, sancțiune, eliberare anulată
> prin ordin), tiparul și capturi ale ecranelor.
>
> Etapa 4, partea 1 (concediile) — **gata** (2026-10-22): aplicația `leave` — **dreptul și soldul** pe anii de muncă
> (de la angajare; concediile pentru îngrijirea copilului prelungesc anul; zilele de bază ale funcției + condițiile din
> funcție / subdiviziune + drepturile personale; anul în curs și eliberarea — proporțional; folositul din ordine, cu anul de
> muncă sau pe cel mai vechi an cu zile rămase; „data pornirii evidenței” + sold inițial; compensarea în bani din ordinul de
> compensare și din eliberare); lista soldurilor și fila „Concedii” în fișă; **graficul anual** pe subdiviziune (completat
> singur, planificat de șeful de secție, transmis, aprobat prin ordinul „Aprobarea graficului concediilor”; avertismente când
> lipsesc toți medicii sau toți de aceeași funcție; plan / realizat / amânat; ordinul colectiv al lunii din grafic; tipar);
> **cererile** de concediu (aprobarea șefului de secție → ordin colectiv pe tip); **amânarea** prin ordin (mută concediul
> neînceput și marchează graficul); **concediile sociale** (126 / 14 zile, îngrijirea copilului până la 3 / 4 ani din data
> nașterii, revenirea automată noaptea); **foile de boală** (registrul certificatelor → absență „concediu medical”,
> avertisment la suprapunerea cu concediul de odihnă). Verificat: 53 de teste, typecheck, build.
> De verificat cu SCTO: zilele de bază pe funcții (medicii — peste 28?), perioadele care nu dau drept (concediul neplătit?),
> regula de rotunjire la compensare. Pe bazele existente rolul „Șef de secție” trebuie să primească de mână „Concedii →
> editare” (planificarea graficului); la instalările noi îl are din oficiu.
>
> Completare (2026-10-22): **mai multe raporturi** pe angajat cu norma în procente (100% / 50% / 25%, pe server în unități),
> câmpul „Plata pentru cumul (%)” cu istoric „din data” (ordinul de cumul îl completează), tipul nou **„Contract de prestări
> servicii”** (nu ocupă post, nu dă concediu, nu intră în vechime); importul primește norma și ca „50%”; graficul concediilor
> arată celelalte raporturi ale angajatului și ia în calcul la suprapuneri pe cei care lucrează în secție prin cumul.
>
> Etapa 4, partea 2 (timpul de muncă) — **gata** (2026-10-22): aplicația `worktime` — **turele** (cod, ore, ore de noapte,
> gardă) și **graficele de lucru** săptămânale / pe ture (cu date inițiale: 5 × 8, 5 × 7, 5 × 6, 6 zile, zi-noapte-liber-liber,
> gardă 24 h), puse pe fiecare raport de muncă „din data” (cu decalaj în ciclu); **calendarul de producție** (norma lunii
> pentru 40 / 35 / 30 h, zile transferate, declarate libere sau scurtate); **graficul lunar al secției** (gărzile): se
> completează din graficele de lucru, se editează pe celule, avertizează la ore peste normă, odihnă prea scurtă, prea multe
> gărzi și tură în zi de absență; ciornă → transmis → aprobat; tipar. **Tabela de pontaj** pe secție: din graficul lunar (sau
> cel de lucru) + concedii, foi de boală, deplasări, suspendări; corectare de mână (rămâne la recalculare); totaluri (zile,
> ore, noapte, sărbători, norma, ± , absențe pe coduri); ciornă → transmis → închis; tipar; **export Excel pentru 1C Salariu**
> (totaluri pe raport + zilele). Totul pe **raport de muncă** (de bază, cumul, suplinire — fiecare cu norma lui, în secția
> lui). Verificat: 62 de teste, typecheck, build, proba în browser (grafic, pontaj, fișa angajatului).
> De verificat cu SCTO: codurile absențelor din tabela lor, dacă graficul pe ture se micșorează la cumul, formatul exact al
> fișierului pentru 1C Salariu (acum: Excel cu totaluri + zile).
>
> Etapa 4b, partea 1 (calculul salariului) — **gata** (2026-10-22): aplicația `payroll` — **constantele** cu „în vigoare din”
> (preîncărcate 2026: impozit 12 %, scutirile, CNAM 9 %, CAS 24 %, noapte / sărbători / suplimentare, boala 5 zile × 75 %);
> **tipurile de calcul** flexibile (automat, sumă fixă, % din salariu, % din bază, tarif orar, trepte; impozabil / CAS / CNAM,
> plafoane neimpozabile pe lună / an / % din salariul mediu, intră în medie, cod IPC) cu 25 de tipuri predefinite;
> **cererea de scutire** (P / M / S / N / H) și **sporurile / reținerile personale** în fila „Salariu” din fișă; **calculul
> lunar** pe raport de muncă: salariul pro-rata la orele din pontaj, sporurile fixe, cumulul, noaptea, sărbătorile,
> suplimentarele, concediul pe medie (HG 426), boala (zilele angajatorului), premiile și ajutorul din ordine, vechimea și
> categoria pe trepte, CNAM, scutirea lunară, impozitul, CAS; rânduri de mână care rămân la recalculare; ciornă → verificat
> → aprobat; tipar: **statul de calcul** și **fișele de calcul**. Verificat: 66 de teste, typecheck, build, proba în browser.
> De verificat cu SCTO: treptele sporului de vechime și ale categoriei (HG 837/2016 + contractul colectiv), salariul minim și
> mediu 2026, perioada de decontare pentru medie.
>
> Etapa 4b, partea 2 (plata și raportările) — **gata** (2026-10-22): **statele de plată** (avans: % din salariul de funcție;
> salariu: netul calculelor aprobate minus ce s-a plătit; card după IBAN / numerar), ciornă → aprobat → achitat (data și
> documentul de plată); avansul se scade singur în calculul lunii; tipar **stat de plată** și **lista pentru bancă**,
> **fișierul pentru bancă** (CSV); **datoriile salariale** pe angajat; **fișa personală anuală** (anexa 8, din fila „Salariu”);
> **IPC21** (lunar: total + persoane), **IALS21** (anual, cu codul scutirii), **IRM19** (din ordinele semnate, cu termenul de 10
> zile lucrătoare) — previzualizare și export Excel. Verificat: 69 de teste, typecheck, build, proba în browser.
> De verificat cu SCTO / contabilitatea: formatul fișierului băncii lor, codul categoriei asiguratului, structura electronică
> IPC21 / IALS21 / IRM19 la depunere.
>
> Declarațiile electronice (2026-10-22): **XML IPC21, IALS21, IRM19** după schemele SFS din dosarul `xml file` și
> instrucțiunile oficiale (OMF 94/2020 modif. OMF 109/2025, OMF 95/2020, anexa 4 la OMF 126/2017) + clasificatoarele CNAS ale
> categoriilor (101, 123, 105, 160, 15311, 157, 158, 159, 165...). IPC21 și IALS21 trec validarea XSD completă. IRM19: schema
> cere dată în col. 6, 7 și 12, iar instrucțiunea spune că nu se completează la angajare / eliberare — de clarificat la prima
> încărcare în SFS.
>
> Etapa 5, partea 1 (termene, notificări, panoul de start) — **gata** (2026-10-22): **Termene și alerte** — 17 tipuri
> (perioada de probă, CIM pe termen, actul de identitate, categoria / certificatul, sfârșitul concediului de îngrijire a
> copilului și de maternitate, concediul nefolosit art. 118, sancțiunea, pensionarea, zilele de naștere / jubileele, treapta
> de vechime, ordinele nefamiliarizate și cele pentru contabilitate, cererile de concediu, concediile lunii următoare,
> graficul lipsă, termenul IRM19), fiecare cu zilele de avertizare și pornit / oprit din setări; destinatarii după rol
> (cadre / contabilitate / șeful — doar secțiile lui); **sarcina de noapte**: notificare în sistem o singură dată pe termen +
> **rezumatul pe e-mail** (serverul SMTP al instituției, parola criptată, proba); **panoul de start** cu indicatorii la zi
> (angajați, concedii, boală, deplasări, cereri, ordine, statul de funcții, zile de naștere, termenele apropiate).
> Verificat: 74 de teste, typecheck, build, proba în browser.
>
> Etapa 5, partea 2 (catalogul de rapoarte) — **gata** (2026-10-22): **Rapoarte** pe grupe, cu filtre comune (perioada / data /
> luna / anul, subdiviziunea cu sub-subdiviziunile, categoria de personal, raporturile de bază sau și cumulul, tipul absenței),
> vizibilitatea pe secțiile utilizatorului, **Excel** și **tipar** cu Stema (forma nouă „Raport”), titluri RO / RU / EN:
> mișcarea cadrelor (cu rata fluctuației), structura personalului (categorii, sex, vârstă, studii, categoria de calificare,
> vechime, normă, tipul angajării), vechimea, zilele de naștere / jubileele, pensionările, posturile vacante, concediile și
> absențele pe perioadă, pontajul consolidat, extrasul din ordine pentru contabilitate, ordinele pe tipuri, **cadrele medicale
> (MS nr. 17)** și **Munca 1 (BNS)**; rapoartele care au deja pagina lor (lista angajaților, ocuparea, contractele, registrul
> ordinelor, soldurile, graficul concediilor, foile de boală, pontajul, IPC21 / IALS21 / IRM19) apar în catalog ca legături.
> Verificat: 82 de teste, typecheck, build, proba în browser. De verificat cu SCTO: rândurile exacte ale formularelor MS nr. 17
> și Munca 1 / 1-IM pentru anul curent. Evidența militară (registrul, raportul lunar) și atestarea / EMC rămân în Etapa 6.
>
> Etapa 6, partea 1 (formare și atestare) — **gata** (2026-10-22): **registrul EMC** (cursuri, conferințe, stagii: ore, credite,
> certificat; ordinul de trimitere la perfecționare pune singur activitatea în registru), **creditele pe perioada de atestare**
> (de la conferirea categoriei, față de norma pe categorii de personal; în grafic / în urmă / risc), **calendarul atestării**
> (categoriile care expiră), lista candidaților la tipar, rezultatul comisiei → **ordinul colectiv de conferire** (la semnare
> categoria intră în dosar), **planul anual de formare** (completare din credite, realizarea din registru, aprobare, tipar),
> alerta „credite insuficiente” cu un an înainte, rapoartele „Creditele EMC” și „Formarea pe perioadă”, fila EMC în fișă.
> Verificat: 86 de teste, typecheck, build, proba în browser. De verificat cu SCTO: norma de credite EMC pe 5 ani pentru
> medici / farmaciști / asistenți (implicit 250 / 250 / 150 — se schimbă din „Normele de credite”).
>
> Etapa 6, partea 2 (sănătatea în muncă și evidența militară) — **gata** (2026-10-22): **examenele medicale** (la angajare,
> periodic, suplimentar; concluzia, restricțiile), **vaccinările** (clasificatorul *Vaccinuri* cu revaccinarea și vaccinurile
> obligatorii pentru personalul medical), **instructajul SSM**; termenul următor calculat din periodicitate; lista
> „depășit / lipsește / urmează” cu tipar pentru medicina muncii și **ordinul colectiv de trimitere la examen**; alertele
> examen / instructaj / vaccin; fila „Sănătate” în fișă. **Evidența militară**: registrul recruților și rezerviștilor, cei
> fără fișă, **modificările lunii pentru centrul militar** (angajări, eliberări, transferuri și schimbările datelor din
> jurnalul de audit), lista recruților — cu Excel și tipar. Verificat: 91 de teste, typecheck, build, proba în browser.
> De verificat cu SCTO: periodicitatea examenului medical pe secții (implicit 12 luni) și forma raportului către centrul militar.
>
> **Etapa 6 încheiată.**
>
> Decizii (2026-10-22): **fără Telegram** — notificările rămân în sistem și pe e-mail (legarea Telegram din profil, câmpul
> din utilizatori și modulul de licență au fost scoase); **limbile sistemului** se aleg în Constante → Module (RO / RU / EN, oricare
> combinație; comutatoarele și câmpurile RU / EN arată doar limbile pornite); la câmpurile din clasificatoare — butonul **„…”**
> care deschide clasificatorul (căutare, adăugare, corectare, alegere), ca în 1C.
>
> Etapa 7 (cabinetul angajatului) — **gata** (2026-10-22): **Cabinetul meu** — datele proprii, zilele de concediu disponibile,
> funcțiile, vechimea, absențele apropiate; **ordinele mele** cu „am luat cunoștință” electronic; **cererile de concediu**
> (șeful de secție aprobă → cadrele fac ordinul; notificare la fiecare pas), **adeverințe și alte cereri** (de la locul de
> muncă, vechime, salariu, modificarea datelor) cu lista „Cererile angajaților” pentru cadre; **fișele de calcul** din
> calculele aprobate; notificările în sistem și pe e-mail (fără Telegram); accesul la cabinet din fișa angajatului (contul cu
> rolul „Angajat”, parola temporară) și conturi pentru toți dintr-un buton. Verificat: 97 de teste, typecheck, build, proba în
> browser (ca angajat și ca cadre).
>
> Etapa 8 (livrarea) — **în lucru** (2026-10-22/23). Făcut: **datele demo** (`crm_demo` / bifa din asistent: spital fictiv,
> ~70 de angajați cu dosare, statele aprobate, concedii, cereri, ordin semnat, pontajul și salariul lunii trecute, utilizatori
> `cadre`, `inspector`, `director`, `sef.trauma`, `contabil`, `angajat` — parola `Demo-Cadre-2026`; evidența concediilor de la
> 1 ianuarie anul trecut); **licența** adaptată (modulele `cadre` + `payroll`, Salarizarea se licențiază separat); versiunea
> **1.0.0**; „Posibilități” și „Ce e nou” rescrise (RO / RU); **instrucțiunile RU** pentru toate modulele și pentru administrare
> (instrucțiunile de administrare curățate de CRM); README, Docker (numele „cadre”); angajatul cu doar cabinetul nu mai vede
> panoul de start și termenele.
>
> Partea 2 (2026-10-23): șeful de secție se leagă de secții din *Utilizatori* („Subdiviziunile lui”); *Câmpuri obligatorii*
> pentru dosarul angajatului, acte și studii; scoase resturile CRM (marja, reducerea, managerii de vânzări, agenții, ruta,
> fila „Perioade și ore”); instrucțiunile RO / RU fără frazele vechi; **site-ul de prezentare** `site/index.html` (cu capturi
> din instanța demo, pe calculator și telefon); pachetul de actualizare semnat (`tools/make_release.py`) verificat cu cheia
> programului, `crm_upgrade` pe o instalare curată. Verificat: 100 de teste, typecheck, build.
>
> **Etapa 8 încheiată — versiunea 1.0.0.** De făcut la livrare: proba installer-ului pe un Windows curat; clarificările cu
> SCTO notate la etape (normele EMC, formularele MS nr. 17 / Munca 1, IRM19 la prima încărcare în SFS, formatul fișierului băncii).
> Installer-ul `cadre-setup-1.0.0.exe` construit cu Inno Setup 6 (2026-10-23); pentru Linux pachetul Docker
> (`tools/make_docker_package.ps1` → `install.sh`, PostgreSQL, parolele în `.env`).
>
> **Versiunea 1.1.0 (2026-10-23) — preluate din CRM acoperiș gard:** meniul pe grupe Registre / Rapoarte / Setări (rapoartele
> catalogului ca funcții de meniu, „Funcții neafișate”, „Închide toate”); alegerea angajatului (`EmployeeSelect`, cu „…” și
> lista angajaților, `?ids=` fără jurnal de acces) și a subdiviziunii (`SubdivisionSelect`, arbore cu „…”) în toate formele;
> **FormLayout** din Gard (câmpurile se iau singure din formă; grupe, lățime, ascunse; pentru mine sau pentru toți —
> `/api/ui-defaults/`) pe dosar, raporturi de muncă, ordin, concedii, foi de boală, formare, atestare, sănătate, utilizatori,
> subdiviziuni, statele de personal, bănci, localități, SMTP și toate clasificatoarele (CrudTable). Verificat: 106 teste,
> typecheck, build, proba de randare a FormLayout.
>
> **Versiunea 1.2.0 (2026-10-24) — salarizarea:** corectarea de mână a oricărei sume din calcul (rândul de mână înlocuiește
> tipul calculat, inclusiv impozitul / CNAM / CAS; recalcularea doar a angajatului); **impozitul reținut la achitare**
> (PaymentLine: brut, scutire, CNAM, impozit, rețineri, net; avansul cu CNAM 9 % și 12 % din rest, salariul — diferența până
> la impozitul lunii; corectarea brutului / netului / impozitelor); IPC21 tabelul 1 și fișa anexa 8 (forma 2018) după datele
> achitării; fluturașii în PDF (reportlab + DejaVu) și pe e-mail în ZIP cu parolă — ultimele 5 cifre ale IDNP (ZipCrypto,
> se deschide în Windows / macOS / telefon), cu evidența trimiterilor; **cartea privind salariul** (după „Книга по ЗП” din
> POLARIS.cf). Verificat: 111 teste, typecheck, build, PDF-ul randat, arhiva deschisă cu libarchive.
>
> **Versiunea 1.6.0 (2026-11-07) — Panoul funcțiilor, ca în 1C:** bifa `Company.function_panel` (Constante → Module,
> migrația `core 0006`, în branding). Pornită, pe ecran lat: secțiunile sus ca file (`.fn-sections` în `AppLayout`, fără
> `Layout.Sider`; favoritele sub ★ în antet), secțiunea → `/panel/<cheie>` (`layout/SectionPanel.tsx`,
> `useSectionPanel` din `menu.tsx`): Schema de lucru (`PANEL_KIND` = `doc` / `start`, săgețile `PANEL_FLOWS`), Registre (restul
> grupei Registre), Clasificatoare (`PANEL_CLASSIFIERS` → setările vizibile ale rolului), Rapoarte; Administrare — lista
> funcțiilor, neîmpărțită. Totul din `useMainMenu` (drepturi, bifele rolului, modulul Salarizare); panoul nu ia filă jos;
> fila secțiunii rămâne aleasă pentru pagina / clasificatorul deschis din ea. Oprită — nimic schimbat. Instrucțiunea
> `docs/*/panel.md`. Verificat: 131 de teste (cheile panoului din `nav.tsx` există), typecheck, Playwright pe `scto-ui` cu
> copia de azi (5 roluri, tema întunecată, telefonul, oprirea).
>
> **Versiunea 1.5.1 (2026-11-02) — fluturașii din îndreptare, tastele ferestrelor, adeverința pentru bancă:** fluturașii
> (tipar, PDF, e-mail) din îndreptarea pe salariu (`PaymentViewSet.payslip*`, `printing.payment_slip_lines` — toată luna
> angajaților ei; `PayslipDispatch.payment`, migrația `payroll 0008`); `layout/windowKeys.tsx` — Esc închide pagina
> (prin `close` din `tabs.tsx`, deci și cu „Salvați modificările?”), Alt+` — „Ferestrele deschise”; adeverința
> `certificate_salary` (`staff/printing.salary_period` / `salary_context`, din `payments.settlement`; dreptul
> `payroll.view`; `printing 0004`); `PrintDialog` cere previzualizarea cu `preview=1`, documentul final (și numărul
> adeverinței) — la Tipărește; denumirile bifelor formelor de cadre. Apoi: ordinul cu mai multe temeiuri legale
> (`Order.legal_bases`, `OrderType.legal_bases`, `LegalBasis.combined` / `preamble`, `/org/legal-bases/preamble/`),
> antetul și punctele ca în 1C (`DOC_HEAD`); `useEditGuard` pe toate formele cu Salvează (Esc nu pierde nimic);
> căutarea în Rapoarte (`utils/text.fold`); „Cine e online” în timp real și `OnlineNow` în antet; legăturile din tabele
> fără aspect de buton. Verificat: 129 de teste, typecheck, copia de azi în `scto-ui`, Playwright 21 + 17.
>
> **Versiunea 1.5.0 (2026-11-02) — salariul în două documente, ca în 1C:** **calculul** (acumulări, rețineri, CAS; pe rând
> `taxable` și `cnam_base` — bazele, fără `exemption` / `income_tax` / `cnam`) și **îndreptarea spre plată** (fostul stat de
> plată, `Payment`, cu `payroll` = calculul de bază sau gol = pe sold): CNAM, scutirea lunii și impozitul se socotesc la
> plată, cumulat pe lună, minus ce s-a reținut deja (`payments.month_taxes`, `salary_due`, `settlement` pentru fluturaș și
> cabinet; soldul `debts` — pe brut). Migrația `payroll 0007` pune bazele calculelor vechi și șterge din ele rândurile
> IMPOZIT / CNAM / AVANS. Anexa 8, IPC21 t. 1 și IALS21 — doar din îndreptările achitate. Calculul cu îndreptări aprobate
> nu se redeschide. Formele ambelor după „Ghid meniu și forme” (cap. 8–9): titlul cu nr. și data, starea, legăturile
> Calcul ↔ Îndreptare, antetul scris de mână, acțiunile dreapta sus, ✕ ultimul (`CloseForm` închide fila), „Salvați
> modificările?” (`UnsavedGuard`, `useBlocker` — de aceea `createBrowserRouter` în `App.tsx`; filele se închid abia după
> plecarea efectivă). Verificat: 127 de teste, typecheck.
>
> **Versiunea 1.4.1 (2026-10-28) — corectările după 1.4.0:** setările se bifează pe rol (`RoleMenuTree`, grupa
> `set:`; `menu_hidden` ține și cheile setărilor, `useVisibleSettings`); datele salvate până la 1.4.0 — favoritele,
> `menu_layout`, `Role.menu_hidden` — le aduce la zi o dată migrația `users 0004` (`apps/core/moved.py`; aceleași funcții
> la salvare, pentru filele rămase pe programul vechi), în locul curățării la fiecare citire; foaia de boală continuată
> (`continuations` nemarcate) e încheiată — `continued_by`, filtrul `open`; rândul marcat fără culoarea stării; titlul
> filelor din meniu se ia la afișare (`crm.tabs.v2`); paginile setărilor — harta `SETTING_PAGES` din `App.tsx`, fără pagina
> clasificatorului ca rezervă; testul `DICT_KINDS` (nav.tsx) = `DictItem.KINDS`.
>
> **Versiunea 1.4.0 (2026-10-27) — toate setările într-un singur loc, culoarea rândurilor:** Administrare → Setări
> (`/settings`, `SETTINGS_NAV` în `layout/nav.tsx`, lista alfabetică cu căutare); grupa Setări a ieșit din secțiunile
> meniului (`MenuLayoutView.GROUPS` = items, reports); clasificatoarele, timpul de muncă, concediile, salarizarea,
> raportările, alertele și poșta — setări separate; adresele vechi — `movedTo`. Rândurile registrelor colorate după
> stare (`components/rowTone.ts`). Lucrat direct în depozitul SCTO (sursa codului de la 2026-10-27).
>
> **Versiunea 1.3.0 (2026-10-24) — marcarea pentru ștergere, ca în 1C:** câmpul `deletion_mark` pe clasificatoare (funcții,
> specialități, alte clasificatoare, temeiuri, tipuri de ordin, subdiviziuni, tipuri de calcul, ture, grafice de lucru,
> localități, bănci) și documente (angajat, ordin, state, grafic de concedii, cereri, foi de boală, calcul, plată, grafic de
> gărzi, pontaj, formare, atestare, plan, examene, vaccinări, instructaje); `apps/core/deletion.py`: `DELETE` marchează
> (verificările de până acum în `check_delete`), `POST …/unmark/` scoate marcajul (dreptul „șterge”), obiectul marcat nu
> se mai modifică (`ensure_not_marked` și în rândurile documentelor), nu se mai alege în câmpuri și nu intră în calcule
> (pontajul în salariu, foaia de boală — absența se scoate la marcare și se pune la loc la scoaterea marcajului, creditele
> EMC, termenele de sănătate). *Administrare → Ștergerea obiectelor marcate* (`/api/system/marked/`): legăturile prin
> `Collector`-ul Django (PROTECT / RESTRICT, câmpurile SET_NULL, documentele care s-ar șterge în cascadă, many-to-many
> declarat la alt obiect; rândurile se arată prin documentul lor) și ștergerea repetată cât timp se mai șterge ceva
> (obiectele alese împreună — în ordinea potrivită). Verificat: 121 de teste, typecheck, build.
>
> **Punct de plecare:** configurația 1C `Personal.cf` („Cadre”, sinonim „Lear Ungheni sistem auxiliar”, versiunea 1.1.0.1,
> platforma 8.3.x) + conceptul de design și de livrare din **CAI ERP Vânzări** (`D:\Proiecte Cloude\CAI ERP VInzari`).
>
> **Ce se construiește:** un sistem web în Python, instalabil la client (installer Windows cu Python inclus, SQLite / PostgreSQL /
> MySQL / MS SQL / Oracle), interfață RO / RU, pentru **serviciul resurse umane al unei instituții medico-sanitare** (IMSP):
> state de personal, dosarul angajatului, toate tipurile de ordine, concedii, timp de muncă, rapoarte, notificări, forme de tipar
> cu Stema de Stat a Republicii Moldova.

---

## 0. Ce am găsit (studiul de pornire)

### 0.1 Configurația 1C „Cadre” (Personal.cf)

Container 1C despachetat: 2 748 fișiere de metadate. Nu e „1C: Salariu și Personal” tipic, ci o **configurație proprie** făcută
pentru fabrica Lear Ungheni, pe Biblioteca Standard (БСП). Subsisteme: *Clasificatoare, Administrare, Salariu, Ordine,
Planificare*. Roluri proprii: *Administrator, Cadre, Planificare, Telefon*.

**Ce merită preluat (logica de cadre):**

| Obiect 1C | Conținut | Decizie |
|---|---|---|
| Catalog **Angajati** (≈120 câmpuri) | nume / prenume / patronimic, IDNP, act de identitate (serie, nr., oficiu, dată, expirare), adresă + domiciliu, sex, naționalitate, starea familială, membrii familiei (soț/soție, copii cu IDNP), telefon, e-mail, foto, IBAN, nr. tabelar, secție + subdiviziune, funcție (profesie) + funcție cumul, tip angajare, data angajării / eliberării, motivul concedierii, temeiul acordării funcției, salariu, % salarizare, grad de calificare, **evidență militară** (categoria, grupa, componența, grad, comisariat, specialitate, apt/inapt, evidență specială), **studii** (instituție, diplomă serie/nr., specialitate, forma de învățământ, data eliberării, ISCED), **calificări**, **stagiu de muncă** (întreprindere, perioadă, funcție), scutiri fiscale, cod asigurare medicală / CPAS, checklist angajare–eliberare, mărimi haine/încălțăminte, nr. dulap, fișiere atașate, arhivat, suspendat temporar | **Se preia integral** ca model pentru *Dosarul angajatului*, reorganizat pe tab-uri |
| 18 **documente-ordine** (vezi §0.2) | fiecare cu: angajat, tip ordin, din data / până la data, nr. zile, zile de sărbătoare, firmă, autor, Ordon (cine semnează), Coordonat, comentarii, cod tabelă, tipar | **Se preia** modelul „un document = un ordin” + registrul *OrdonConformOrdinelor* (semnatarul pe tip de ordin) |
| **StateleDePersonal** | secție, funcție, unități, salariu tarifar de funcție, total | Se preia și se extinde (versiuni, aprobare, cod CORM, efectiv-limită) |
| **TabelaDePontaj**, **GraficDeLucru** (Z1..Z31 / N1..N31, ture, săptămână pară, ore noapte) | pontaj lunar pe secție, grafice standard / pe ture | Se preia (modelul zi / noapte e exact ce trebuie pentru gărzi) |
| Registre: *SarbatoriAnuale, GraficDeLucruAngajati, Functii, Departamente, SalariiComformFunctie* | istoric pe angajat | Se preia ca istoric periodic (funcție, secție, salariu cu „din data”) |
| Enumerări: *TipAngajare* (de bază, de bază student, cumul extern, cumul intern, rezident), *Studii, FormaDeInvatamint, StareaFamiliara, Membrul, GrupaEvidentei, Componenta, Apt, ClasificareISCED, TipGrafic* | | Se preiau ca nomenclatoare editabile |
| Imaginea comună **Stema** + forma de tipar a ordinului | antet instituție, „ORDINUL N … DIN …”, text „SE OFERĂ CONCEDIUL DE ODIHNĂ ANUAL SALARIATULUI [secția] [funcția] N.T. [nr. tabelar] D. [angajat] [zile] ZILE CALENDARISTICE DE LA … PÎNĂ LA … PENTRU ANUL LUCRĂTOR …, TEMEIUL: 1. CEREREA D. …” | Se preia **formatul ordinului** (stilul clasic RM) și se pune Stema pe toate formele |
| Rapoarte: *RaportAngajati, RaportSalariu* | puține | Se înlocuiesc cu setul din §6 |

**Ce NU se preia** (specific fabricii): KPI (PondereKPI, RezultateKPI, CalculBonusKPI, GrupeKPI, NereguliFabrica cu GPS și
puncte de penalizare), calcul salariu + rețineri + export MAIB (salariul rămâne în 1C Salariu / contabilitate), sondaje și teste
(Тест, ШаблоныТестов), senzori de temperatură, echipament conectat, Proiecte, TimeDoctor, mărimi de haine (rămân opțional
ca „echipament / uniformă” la spital).

### 0.2 Cele 18 ordine din 1C (toate se păstrează)

Concediu de odihnă anual plătit · concediu suplimentar plătit · concediu neplătit · concediu din cont propriu · concediu parțial
plătit pentru îngrijirea copilului · concediu de maternitate (126 zile) · concediu de învățământ · rechemare din concediu ·
ordin de angajare · ordin de angajare prin transfer · ordin de demisie · modificarea salariului · transfer (funcție) · delegare ·
foaie de boală · lucru în zi de odihnă · modificarea orelor de lucru · premii.

Pentru spital lipsesc încă vreo 30 de tipuri (vezi §5.3) — mai ales suplinirea, cumulul, interimatul, suspendarea,
sancțiunile disciplinare, atestarea, perfecționarea, gărzile, sporurile.

### 0.3 Ce e specific unui astfel de sistem în Moldova (din internet)

| Subiect | Act / sursă | Ce înseamnă pentru sistem |
|---|---|---|
| Raporturile de muncă | Codul muncii nr. 154/2003 (perioadă de probă până la 6 luni; CIM pe durată determinată — max. 3 contracte succesive, cumulat ≤ 60 luni; suspendarea art. 76–78; încetarea art. 82–86; sancțiuni art. 206: avertisment, mustrare, mustrare aspră, concediere, cu termen de acțiune 1 an) | fiecare ordin are **temei legal** (articol) ales din nomenclator; notificări la expirarea probei / contractului / sancțiunii |
| Carnetul de muncă | abrogat din 01.01.2019 (Legea 123/2017, HG 426/2018); înscrierile de până atunci rămân valabile; evidența se ține în **Registrul electronic al angajaților (SIA REA)** la CNAS | nu mai există „carnet”, dar sistemul ține **istoricul complet al raporturilor de muncă** și poate genera extrasul / adeverința de vechime; export pentru REA |
| Dosarul personal | Procedura IMSP SCR „T. Moșneaga” POS-CEP-01: un singur dosar de la angajare la eliberare, înregistrat cu **nr. de tabel**, documente în ordine cronologică, fișa personală **MR-2**, interzise datele despre apartenența politică / religioasă, declarații (prelucrarea datelor, lipsa antecedentelor penale, confidențialitate, evidența militară), păstrare în safe, arhivare la plecare | Dosarul electronic = fișa MR-2 + registrul documentelor + declarațiile + checklist; **jurnal de acces** la date personale (Legea 133/2011) |
| Statele de personal | Ordinul MS nr. 100/2008 „Normativele de personal medical” (modif. 809/2025, 483/2026 — caracter de recomandare, personal administrativ-gospodăresc ≤ 13 % în AMP); aprobate de fondator (consiliul raional / MS) cu **structura**, **efectivul-limită** pe categorii (medici, personal medical mediu, personal medical inferior, administrativ-gospodăresc) și **organigrama**; funcțiile cu **cod CORM 006-21** (HG 208/2021), unități fracționate 0,25 / 0,5 / 0,75 / 1,0, „cu 50 % efort medic de familie” | documentul *State de personal* are versiuni, data intrării în vigoare, cod CORM, unități fracționate, totaluri pe categorii, tipar în formatul anexei la decizie |
| Salarizarea IMSP | HG 837/2016 (salariu de funcție pe categorii, sporuri: vechime, categorie de calificare, grad științific, condiții nocive, muncă de noapte, performanță stabilită semestrial) | ordine de stabilire salariu / sporuri; nu se calculează salariul, se transmite în 1C Salariu |
| Concedii | 28 zile calendaristice minim (art. 112 CM); **HG 1223/2004** — nomenclatorul profesiilor cu condiții vătămătoare: concediu suplimentar + zi de muncă redusă pentru personalul medical (pe secții: boli infecțioase, TBC, etc.); concedii sociale: maternitate 126 (140) zile, paternal 14 zile, îngrijire copil parțial plătit până la 3 ani, neplătit până la 4 ani, de studii, zile libere plătite (căsătorie, deces) | **soldul de concediu** pe angajat = de bază + suplimentar (din funcția / secția cu condiții nocive) − folosit; graficul anual al concediilor |
| Atestarea | Ordinul MS 386/2018 (comisii de atestare, categorii de calificare: a doua, întâi, superioară; reconfirmare periodic) | în dosar: categoria + data conferirii + data expirării → notificare cu 6 luni înainte |
| Educația medicală continuă | Ordinul MS 580/2026 — Regulamentul EMFC (obligatorie pentru medici, farmaciști, personal cu studii medii; planul anual de formare pe fiecare medic; certificat de participare cu credite) | registru **cursuri / credite EMC** pe angajat, planul anual de formare, raport „cine nu are creditele” |
| Evidența militară | HG 631/2003 + Ordinul Marelui Stat Major 46/2020: angajatorul ține evidența recruților și rezerviștilor, raportează lunar la centrul militar, listele anuale | tab „Evidență militară” (preluat din 1C) + raportul lunar al modificărilor + registrul |
| Raportări externe | CNAS: IRM19 (angajare / eliberare), IPC21; BNS: Munca 1 (lunar), 1-IM / Munca 2 (trimestrial), FORPRO, LM; MS: rapoarte statistice pe cadre (nr. 17 „Cadrele medicale”) | exporturi Excel în structura formularelor; sistemul generează cifrele, nu depune el |
| Model de referință de stat | HG 172/2025 — Conceptul **SI EMRU** (sistemul de evidență și management al resurselor umane din autoritățile publice): obiecte „autoritate, subdiviziune, funcție, post, persoană, document, act administrativ, contract”; dosar electronic; proceduri de personal; notificări automate; rapoarte; jurnalizarea; conturul „cabinet personal” al angajatului; integrare cu REA, MPass, MSign | ne aliniem la aceeași structură de date (ușurează o integrare ulterioară); cabinetul personal = portalul angajatului din Etapa 6 |
| Licitații publice pentru „1C: Salariu și Managementul personalului” | cerințe tipice: ordine pe formular tipizat, cumul și suplinire, state de personal exportabile, istoricul modificărilor datelor personale, funcții clasificate automat CORM / ISCO-08, portal angajat (zile de concediu rămase, fișa de salariu), IPC21 / IALS21 / IRM19, statistică M1–M3 | lista de verificare a funcționalului pentru vânzare la alte instituții |

---

## 1. Obiectiv

Un sistem **„CAI Personal”** (nume de lucru) pentru serviciul cadre al unei instituții medicale (spital, centru de sănătate,
policlinică), care:

- ține **statele de personal** (cu versiuni, cod CORM, unități fracționate, efectiv-limită, organigramă) și arată în orice moment
  posturile ocupate / vacante / temporar vacante;
- ține **dosarul fiecărui angajat** (fișa MR-2 electronică) cu toate raporturile de muncă (de bază, cumul intern, cumul extern,
  rezident, suplinire), studii, atestări, EMC, evidență militară, documente scanate;
- emite **toate tipurile de ordine** din registru, cu numerotare pe categorii, temei legal, semnatar, coordonare, tipar cu Stema;
  ordinul „postat” schimbă singur starea angajatului (funcție, secție, salariu, concediu, suspendare, eliberare);
- gestionează **concediile** (sold, grafic anual, cereri) și **timpul de muncă** (grafice, ture / gărzi, pontaj);
- livrează **rapoarte** (listă și individual, Excel / PDF / Word) și **notificări** (termene din Codul muncii și din regulamentele MS);
- are **interfață RO / RU**, se instalează la client ca CAI ERP (installer Windows, mai multe baze, licență, backup, actualizări);
- rămâne **fără calcul de salariu**: pontajul și ordinele se exportă în 1C Salariu / contabilitate.

---

## 2. Arhitectura tehnică (identică cu CAI ERP Vânzări)

| Strat | Tehnologie | Observații |
|---|---|---|
| Backend | **Python 3.12+ · Django 6 · Django REST Framework · JWT** | se refolosesc din CAI: `apps/core, users, setup, printing, reports, messaging, telegram, help, imports`, `launcher.py`, `desktop.py`, `updater.py`, `platform_console.py` |
| Baze de date | SQLite (local) · PostgreSQL · MySQL/MariaDB · MS SQL · Oracle | asistentul de instalare din CAI, neschimbat |
| Frontend | **React 19 · TypeScript · Ant Design 6 · Vite · i18next** | aceeași temă (Verde / Turcoaz / Albastru / Întunecată), panoul de start pe rol, tabele cu filtre, forme cu tab-uri |
| Tipar | șabloane HTML → PDF (WeasyPrint) + DOCX (python-docx) pentru ordine editabile în Word; **forme de tipar editabile** din interfață ca în CAI | antet: Stema de Stat, denumirea instituției RO (+ RU), IDNO, adresă |
| Sarcini în fundal | Django-Q2 (coadă în baza de date) | notificări zilnice, e-mail, backup |
| Notificări | în sistem · e-mail SMTP | Telegram scos (decizia din 2026-10-22) |
| Livrare | installer Inno Setup cu Python inclus (`vanzari-setup` → `personal-setup`), port implicit **8030**, date în `%ProgramData%\CAI-Personal`, sarcina Windows „CAI Personal Server”, Docker Compose pentru Linux | |
| Licență / actualizări / backup / jurnal de audit / date demo / „Posibilități” | preluate din CAI Etapa 11 | |

**Modulele noi** (`backend/apps/`): `org` (instituție, subdiviziuni, state de personal), `staff` (dosarul angajatului),
`orders` (ordine + registru + forme), `leave` (concedii), `worktime` (grafice, pontaj), `training` (atestare, EMC, instruiri),
`military` (evidența militară), `hr_reports`, `hr_notify`, `portal` (cabinetul angajatului), `exchange1c` (import / export 1C).

**Structura de date** urmează SI EMRU: *Instituție → Subdiviziune → Post (din statul de personal) → Raport de muncă (angajat × post,
cu tip: de bază / cumul / suplinire) → Act administrativ (ordin) → Document*. Toate datele „cu istoric” (funcție, secție, salariu,
categorie, normă) se țin ca **înregistrări periodice** cu „din data”, exact ca registrele din 1C.

---

## 3. Asistentul de instalare și administrarea (din CAI, cu adaptări)

1. Limba, tipul bazei, conexiunea, crearea structurii.
2. **Datele instituției**: denumire RO / RU, forma (IMSP / privată), IDNO, adresă, telefon, e-mail, **director (ordonator)**,
   **șef resurse umane**, contabil-șef, fondator (MS / consiliul raional / municipal), logo, Stema (implicită).
3. Nomenclatoarele inițiale: CORM 006-21 (ocupațiile din sănătate preîncărcate), categorii de personal, specialități medicale,
   grade de calificare, temeiuri legale (articolele CM), tipuri de ordine cu prefixe de numerotare, sărbătorile anuale RM,
   grafice de lucru standard (5 zile / 8 ore, 7 ore pentru personal medical, 6 ore nocive, ture 12 / 24 ore), calendarul.
4. Administratorul + opțional SMTP.
5. **Import din 1C** (opțional, din prima zi): angajații, secțiile, funcțiile, istoricul ordinelor — din baza Personal (OData sau
   Excel), ca în importul 1C din CAI.

Roluri: **Administrator**, **Șef resurse umane** (vede tot, semnează / coordonează ordine), **Inspector cadre** (creează ordine,
dosare), **Director** (aprobă, vede rapoarte), **Șef secție** (vede doar secția lui: angajați, concedii, pontaj, graficul),
**Contabilitate** (citește ordinele cu efect salarial, pontajul; export), **Angajat** (cabinetul personal: datele proprii, soldul
de concediu, cereri). Rolurile se editează din interfață; câmpuri ascunse pe rol (salariul, IDNP, datele medicale).

---

## 4. Clasificatoare (nomenclatoare)

- **Subdiviziuni** (ierarhic): secții, oficii ale medicilor de familie (OMF), oficii de sănătate (OS), laboratoare, servicii
  administrative; cu semnificație (clinică / paraclinică / administrativă), profil (boli infecțioase, TBC, etc. → condiții
  nocive), șef de secție, cod intern.
- **Funcții (posturi)** cu cod **CORM 006-21** și ISCO-08, **categoria de personal** (conducere · medici · farmaciști · personal
  medical cu studii medii · personal medical inferior · personal administrativ-gospodăresc · alt personal), grupa de salarizare
  (HG 837/2016), durata normală a săptămânii (40 / 35 / 30 ore), zile de concediu de bază și suplimentar.
- **Specialități medicale** (nomenclatorul MS), **categorii de calificare** (a doua, întâi, superioară), **grade științifice**
  (doctor, doctor habilitat), **titluri** (conferențiar, profesor).
- **Studii**: nivel (ISCED), instituții de învățământ, forme de învățământ, specialitatea.
- **Tipuri de documente** (buletin, pașaport, diplomă, certificat de rezidențiat, certificat de categorie, licență, certificat EMC,
  carnet medical, livret militar, etc.) cu „are termen de valabilitate”.
- **Temeiuri legale**: articol + alineat + litera din Codul muncii / HG, cu textul care se pune în ordin.
- **Tipuri de ordine** (§5.3) cu: categoria registrului (personal „-p” / de bază / concedii „-c” / deplasări), prefixul numărului,
  șablonul de tipar, efectul asupra angajatului, semnatarul implicit (registrul *OrdonConformOrdinelor* din 1C), lista de
  coordonare.
- **Tipuri de concedii** (§5.4), **sărbători anuale**, **grafice de lucru**, **motive de încetare**, **sancțiuni**, **tipuri de
  stimulare**, **centre militare**, grade militare, naționalități, țări, starea familială, membrii familiei, **sporuri**.

Toate: listă + fișă, import din Excel, export, istoricul modificărilor (jurnal de audit).

---

## 5. Module funcționale

### 5.1 Statele de personal

- Document **„State de personal”** cu versiuni: nr., data aprobării, cine a aprobat (decizia fondatorului), în vigoare de la.
  Rânduri: subdiviziune, funcție (cod CORM), categoria de personal, **unități** (0,25 … n), salariul de funcție, sporuri fixe,
  „cu X % efort …”, observații. Totaluri pe subdiviziune și pe categorie; **efectivul-limită** (anexa 2 din decizie) și
  **organigrama** (anexa 3, generată din ierarhia subdiviziunilor).
- Modificarea statelor: ordin „cu privire la modificarea statelor de personal” (introducerea / lichidarea / redenumirea unui
  post) creează versiunea următoare, cu diferențele evidențiate.
- Ecran **„Ocuparea posturilor”**: pentru fiecare post — unități aprobate, ocupate (de bază + cumul, în unități), vacante, temporar
  vacante (angajat în concediu de îngrijire a copilului, suspendat), cine le ocupă și cu ce normă. Avertizare la angajare dacă
  postul nu are unități libere (depășirea se permite doar cu drept special).
- Tipar: statul de personal în formatul anexei la decizie, cu Stema; export Excel; comparația plan (normative Ord. 100/2008 pe
  populația deservită) vs. aprobat.

### 5.2 Dosarul angajatului (fișa personală MR-2 electronică)

Lista angajaților (tabel cu filtre: subdiviziune, categorie, funcție, tip angajare, stare: activ / suspendat / eliberat / arhivat;
căutare după nume, IDNP, nr. tabelar; coloane configurabile; export) și **fișa individuală** cu tab-uri:

| Tab | Conținut |
|---|---|
| **Date personale** | nume, prenume, patronimic, nume anterior, IDNP, data și locul nașterii, sex, cetățenie, naționalitate, starea familială, foto, nr. tabelar (unic, dat la angajare), telefoane, e-mail |
| **Acte** | act de identitate (tip, serie, nr., oficiu, dată, **expirare**), adresă de domiciliu / reședință, cod asigurare medicală (CNAM), CPAS (CNAS), IBAN + bancă, grupa sanguină (opțional), persoană de contact în caz de urgență |
| **Familia** | membrii (soț / soție, copii cu IDNP și data nașterii — pentru scutiri fiscale, concedii, zile libere) |
| **Studii și calificare** | studii (nivel, instituție, diplomă serie / nr. / dată, specialitate, forma), rezidențiat / secundariat, specializări, **categoria de calificare** (specialitatea, categoria, nr. certificat, data conferirii, valabil până), grad științific, titlu, limbi, **certificat / licență de exercitare**, **EMC**: cursuri cu credite pe perioada de atestare (5 ani) cu totalul pe perioadă |
| **Raporturi de muncă** | lista contractelor: tip (de bază / cumul intern / cumul extern / rezident / suplinire / stagiar), postul din statul de personal, subdiviziunea, funcția, **norma** (0,25 … 1,5), data angajării, ordinul, CIM nr. / dată, durată determinată până la, perioadă de probă până la, salariul de funcție + sporuri (istoric), categoria, data încetării + temeiul + ordinul. Cu **istoricul** tuturor modificărilor (din ordine) |
| **Vechimea** | stagiul anterior (întreprindere, perioadă, funcție, din documente), calculat: vechime totală, în specialitate, în instituție, în funcție; pentru sporul de vechime și pentru adeverințe |
| **Concedii** | soldul pe fiecare an lucrător (de bază + suplimentar − folosit), lista concediilor cu ordinele, foile de boală |
| **Evidență militară** | categoria evidenței, grupa (Forțele Armate / Grăniceri / Carabinieri), componența, gradul, specialitatea militară, centrul militar, apt / inapt, evidență specială, livret serie / nr. (preluat din 1C) |
| **Sănătatea în muncă** | examenul medical periodic (data, concluzia, următorul), carnetul medical, vaccinări (hepatită B etc.), instructajul SSM, grupa de risc — cu termene → notificări |
| **Sancțiuni și stimulări** | sancțiuni disciplinare (abaterea, sancțiunea, ordinul, până la — se sting automat după 1 an), premii, diplome, distincții |
| **Instruiri și deplasări** | cursuri, conferințe, delegări (ordinul, raportul) |
| **Documente** | scanări atașate pe tip (cu termen de valabilitate), declarațiile (prelucrarea datelor, antecedente, confidențialitate, evidența militară), **checklist angajare / eliberare** (ce a prezentat / predat), registrul documentelor din dosar în ordine cronologică |
| **Ordine** | toate ordinele angajatului, cronologic, cu deschidere / tipar |
| **Jurnal** | cine, când, ce a modificat (audit) + cine a deschis dosarul (acces la date personale) |

Tipar din fișă: **fișa personală MR-2** (toate datele, cu Stema și foto), **adeverință de la locul de muncă**, **adeverință de
vechime / extras din raporturile de muncă**, **CV**, lista documentelor din dosar, fișa de evidență militară. Deduplicare la
IDNP. Arhivarea la eliberare (dosarul rămâne, doar citire).

### 5.3 Ordinele (toate tipurile)

Model comun (din 1C): nr. + dată (numerotare automată pe registru, cu prefix / sufix, ex. „125-p”, „38-c”), tipul, instituția,
**angajatul sau lista de angajați** (ordine colective: concedii, premii, atestare), temeiul (cererea angajatului nr. / dată,
certificatul medical, demersul șefului de secție, procesul-verbal, hotărârea), textul generat din șablon + editabil, **Ordon**
(semnatarul), coordonat cu (lista de vize), „adus la cunoștință” (data, semnătura angajatului), comentarii, fișiere atașate.

**Stări:** Ciornă → La coordonare → Semnat (postat) → Adus la cunoștință; **Anulat** / **Modificat** (ordinul de modificare
leagă ordinul inițial). Numai ordinul semnat produce efecte asupra angajatului și intră în **registrul ordinelor**.

**Tipurile de ordine** (grupate; cele marcate ★ există în 1C):

A. **Raporturi de muncă**
1. angajare ★ (de bază / cumul intern / cumul extern / pe durată determinată / rezident / stagiar), cu perioadă de probă
2. angajare prin transfer ★ (de la altă unitate)
3. modificarea CIM: transfer la altă funcție ★ / altă subdiviziune, modificarea normei (0,5 → 1,0), modificarea salariului ★,
   schimbarea condițiilor de muncă, prelungirea CIM pe durată determinată, trecerea pe durată nedeterminată
4. **suplinirea temporară** a unui angajat absent (concediu, boală) — cu plata pentru suplinire
5. **cumulul de funcții / extinderea zonei de deservire** (cumulare internă cu % din salariu)
6. **interimatul** (exercitarea temporară a atribuțiilor de șef secție / director)
7. detașare, **delegare** ★ (deplasare în interes de serviciu, internă / externă, cu raportul și decontul)
8. **suspendarea CIM** (art. 76–78: concediu de îngrijire a copilului, serviciu militar, detașare, absență > 30 zile, la cererea
   angajatului, etc.) și **reluarea activității**
9. **încetarea CIM**: demisie ★ (art. 85), acordul părților (art. 82 lit. a), expirarea termenului, din inițiativa angajatorului
   (art. 86: reducerea statelor, necorespundere, absență, concediere disciplinară), deces, pensionare, în circumstanțe
   independente de voința părților (art. 82); cu indemnizație / compensarea concediului nefolosit (calculată de sistem)
10. anularea ordinului de angajare / de eliberare (restabilirea în funcție)

B. **Concedii** (§5.4)
11. concediu de odihnă anual ★ (integral sau pe tranșe, cu „pentru anul lucrător de la … până la …”)
12. concediu suplimentar plătit ★ (condiții vătămătoare, copii, etc.)
13. concediu neplătit ★ / din cont propriu ★
14. concediu de maternitate ★ (126 / 140 zile)
15. **concediu paternal** (14 zile)
16. concediu parțial plătit pentru îngrijirea copilului până la 3 ani ★ · **concediu suplimentar neplătit până la 4 ani**
17. concediu de studii ★ · **concediu de creație / fără plată pentru formare**
18. **zile libere plătite** (căsătorie, nașterea copilului, deces în familie, donare de sânge)
19. rechemarea din concediu ★ · **amânarea / transferul concediului** · **compensarea** concediului nefolosit
20. foaie de boală ★ (înregistrare, nu ordin — alimentează pontajul și soldul)

C. **Timp de muncă**
21. aprobarea / modificarea **graficului de lucru** ★ (pe secție, pe lună; ture / gărzi)
22. **lucru în zi de odihnă / sărbătoare** ★ · **ore suplimentare** · **muncă de noapte**
23. stabilirea **zilei de muncă reduse** (condiții nocive) · **program parțial** · **regim individual**
24. **gărzi** (medic de gardă acasă / în staționar) — graficul lunar aprobat prin ordin

D. **Salarizare și stimulare** (fără calcul)
25. stabilirea / modificarea salariului de funcție ★ (la angajare, la schimbarea categoriei, la indexare)
26. **sporuri**: vechime, categorie de calificare, grad științific, condiții nocive, performanță (semestrial), pentru suplinire /
    cumul, pentru muncă de noapte, pentru intensitate
27. premii ★ · **ajutor material** · **indexare / majorare generală** (ordin colectiv)

E. **Disciplină**
28. **sancțiune disciplinară** (avertisment, mustrare, mustrare aspră, concediere), cu explicația angajatului și termenul de 1 an
29. **ridicarea sancțiunii înainte de termen**

F. **Profesional (specific medical)**
30. **trimitere la perfecționare / EMC** (curs, perioada, instituția, cu păstrarea salariului)
31. **atestare**: trimiterea la atestare, **conferirea / confirmarea categoriei de calificare** (colectiv, după ordinul MS)
32. **examen medical periodic** (ordin colectiv cu lista și termenele)
33. instruirea SSM, stagierea, mentoratul rezidenților

G. **Organizatorice (ordine de bază)**
34. aprobarea / modificarea **statelor de personal** (§5.1) · crearea / lichidarea / redenumirea subdiviziunii
35. aprobarea **graficului anual al concediilor**
36. numirea responsabililor (evidența militară, SSM, protecția datelor, arhivă), constituirea comisiilor (atestare internă, disciplinară)
37. ordin liber („cu privire la …”) cu text editabil — pentru tot ce nu se încadrează

Fiecare tip are **șablon de tipar** (HTML / DOCX, editabil de client) cu antetul: Stema de Stat, denumirea instituției RO (RU
dedesubt opțional), IDNO, adresă; apoi „ORDIN nr. … din …”, titlul „Cu privire la …”, preambulul cu temeiul legal, „ORDON:”
cu punctele, „Temei:”, semnătura directorului, vizele, „Am luat cunoștință: ___ (data, semnătura)”. Extras din ordin pentru
contabilitate. Ordinele colective — tabel cu angajații.

**Registrul ordinelor**: pe an și pe categorie, cu nr., dată, tip, angajați, stare, cine a semnat; tipar „Registrul de evidență a
ordinelor” (legat, numerotat) și export. Nr. nu se poate repeta; găurile în numerotare se semnalează.

### 5.4 Concedii

- **Dreptul la concediu** pe fiecare angajat și an lucrător (de la data angajării): zile de bază (28 sau mai mult după funcție),
  zile suplimentare (din funcție / subdiviziune cu condiții vătămătoare — HG 1223/2004; pentru copii; pentru vechime, dacă
  e în contractul colectiv), proporțional cu perioada lucrată, minus perioadele care nu dau dreptul.
- **Soldul** = drept − folosit (din ordine) ± rechemări, amânări, compensări; vizibil în fișă, în lista angajaților, pe portal.
- **Graficul anual al concediilor** pe subdiviziune (planificat de șeful de secție, consolidat de cadre, aprobat prin ordin);
  comparația plan / realizat; verificarea ca secția să nu rămână fără medic de gardă (suprapuneri).
- **Cererea de concediu** (de la angajat, din portal sau introdusă de cadre) → ordin generat automat.
- Concediile sociale (maternitate, îngrijire copil, paternal) cu calculul datelor (126 zile de la data din certificatul medical,
  până la împlinirea a 3 / 4 ani a copilului) și **suspendarea / revenirea** automată.
- Foile de boală: înregistrare (seria, nr., perioada, tipul), reflectare în pontaj; export pentru CNAS / contabilitate.

### 5.5 Timp de muncă

- **Grafice de lucru**: standard 5 zile (8 / 7 / 6 ore), 6 zile, ture 12 h și 24 h, „săptămâna pară / impară”, orele de noapte,
  grafic individual; calendarul de producere pe an cu sărbătorile RM și zilele transferate.
- **Graficul lunar pe secție** (gărzi): tabel angajat × zi cu codul turei; verificări: norma lunară de ore, odihna între ture,
  max. ore de gardă; aprobare de șeful secției și tipar.
- **Tabela de pontaj** lunară pe subdiviziune (modelul Z1..Z31 / N1..N31 din 1C): se completează automat din grafic + ordine
  (concedii, boală, delegări, suspendări), se corectează manual, se închide; **export pentru 1C Salariu** (Excel / fișier de
  schimb) și tipar în formatul tabelei de pontaj.

### 5.6 Formare, atestare, sănătate în muncă

- Registrul **EMC**: cursuri, credite, certificate; planul anual de formare al instituției (cerut de Regulamentul EMFC);
  raportul „credite acumulate în perioada de atestare”.
- **Atestarea**: calendarul (categoria expiră la 5 ani), lista celor care urmează, demersul către comisia MS, ordinul de
  conferire după rezultat.
- **Examenul medical periodic** și **vaccinările**: termene pe funcție / secție, liste pentru medicina muncii, notificări.

### 5.7 Evidența militară

Tab-ul din dosar (§5.2) + **registrul recruților și rezerviștilor**, fișa de evidență, raportul lunar al modificărilor
(angajări / eliberări / schimbări) către centrul militar teritorial, listele anuale, verificarea documentelor la angajare.

### 5.8 Notificări (în sistem și pe e-mail; zilnic, cu termene configurabile)

- expiră **perioada de probă** (cu 10 zile înainte) · expiră **CIM pe durată determinată** (30 zile) · se apropie limita de 60
  luni / 3 contracte
- **actul de identitate**, licența, certificatul de categorie, certificatul EMC, carnetul medical, examenul medical, vaccinarea
  — expiră (90 / 30 zile)
- **atestarea** la 5 ani (6 luni înainte) · credite EMC insuficiente cu 1 an înainte de atestare
- **concediul de îngrijire a copilului** se încheie (copilul împlinește 3 / 4 ani) → revenire · **concediul de maternitate** se încheie
- concediu de odihnă **neplanificat / nefolosit** pentru anul lucrător (art. 118: nu se admite neacordarea 2 ani la rând)
- **sancțiunea disciplinară** expiră (1 an) · vârsta de **pensionare** (6 luni înainte) · **ziua de naștere** / jubileu
- **vechimea** atinge o treaptă nouă (spor) · post **vacant** mai mult de N zile · ordin **neadus la cunoștință** după 3 zile
- pentru contabilitate: ordine semnate cu efect salarial (listă zilnică)
- pentru șeful de secție: cereri de concediu de aprobat, angajații în concediu luna viitoare, graficul lunar de completat

### 5.9 Rapoarte (toate cu filtre pe perioadă / subdiviziune / categorie, listă + individual, Excel / PDF / Word, Stema la tipar)

1. **Lista angajaților** (configurabilă: coloane alese, grupare pe subdiviziune / categorie / funcție) — forma de bază cerută
2. **Statele de personal** vs. **ocuparea** (unități aprobate / ocupate / vacante / temporar vacante) pe subdiviziuni
3. **Mișcarea cadrelor** (fluctuația): angajați / eliberați / transferați pe perioadă, cu motive; rata fluctuației
4. **Structura personalului**: pe categorii, sex, vârstă (grupe), studii, vechime, categorie de calificare, tip angajare
   (de bază / cumul), normă — baza pentru raportul statistic al MS pe cadre (nr. 17) și pentru BNS (Munca 1, 1-IM)
5. **Registrul ordinelor** · **Extrasul din ordine pentru contabilitate** · ordinele pe tip și perioadă
6. **Concedii**: graficul anual, soldurile, concediile pe lună, nefolosite, compensate; **foile de boală** pe perioadă
7. **Pontajul** pe secție și consolidat; orele de noapte, gărzile, suplimentare
8. **Expirări**: contracte, probe, acte, categorii, EMC, examene medicale (lista „de făcut” a inspectorului)
9. **Atestare / EMC**: cine și când, creditele pe persoană
10. **Evidența militară**: registrul, raportul lunar
11. **Vechimea** pe angajați (pentru sporuri) · **zile de naștere** · **pensionări** în anul următor
12. **Posturi vacante** (pentru anunțuri, ANOFM, site)
13. **Dosarul angajatului** complet (fișa MR-2) · adeverințe · CV · lista documentelor
14. **Export pentru raportări**: IRM19 (angajări / eliberări), structura Munca 1 / 1-IM, REA, 1C Salariu
15. Panoul de start cu indicatori: total angajați / unități, vacante, în concediu azi, bolnavi azi, expirări luna aceasta,
    ordine de semnat / adus la cunoștință

### 5.10 Portalul angajatului (cabinetul personal)

Angajatul vede datele proprii, soldul de concediu, ordinele sale (cu „am luat cunoștință” electronic), depune cereri
(concediu, zile libere, adeverință) → cadre primește notificare → ordin. Șeful de secție aprobă cererile și completează graficul.
Notificările angajatului: în cabinet și pe e-mail (fără Telegram).

### 5.12 Salarizarea (modul opțional, bifa „cu salariu” în Constante)

Scop: calculul lunar al salariului după legislația RM pentru toți angajații (nu doar managerii, ca în CAI ERP), cu tipuri de
calcul **flexibile**, trei documente (calcul → plată → achitare) și formularele oficiale. Datele vin din modulul de cadre:
funcții, salarii de funcție, sporuri din ordine, pontaj, concedii, foi de boală.

#### 5.12.1 Constantele salariului (cu istoric „din data”, preîncărcate pentru 2026)

| Constanta | Valoarea 2026 (de verificat la instalare) | Sursa |
|---|---|---|
| Impozitul pe venit persoane fizice | **12 %** | Codul fiscal art. 15 |
| Scutirea personală anuală | **29 700 lei** (nu se aplică la venit ≥ 360 000 lei/an) | art. 33 |
| Scutirea personală majorată | **34 620 lei** | art. 33 (2) |
| Scutirea pentru soț / soție | **21 780 lei** | art. 34 |
| Scutirea pentru persoană întreținută | **9 900 lei**; întreținut cu dizabilitate severă / din copilărie **21 780 lei**; venitul întreținutului ≤ 12 400 lei/an | art. 35 |
| Contribuții asigurări sociale, angajator | **24 %** (IMSP și sectorul privat; 29 % sectorul bugetar) | Legea BASS 2026 |
| Contribuții asigurări sociale, angajat | 0 % (abolit din 2021) | |
| Prime asigurare medicală, angajat | **9 %** | Legea FAOAM 2026 |
| Prime asigurare medicală, angajator | 0 % | |
| Cotizația sindicală | 1 % (opțional, pe angajat) | |
| Salariul minim pe economie · salariul mediu prognozat | pentru plafoane (cadouri ≤ 10 % din salariul mediu, tichete de masă, diurnă HG 10/2012) | HG anuale |
| Indemnizația pentru incapacitate temporară de muncă | primele **5 zile** le plătește angajatorul (**75 %** din venitul mediu), din a 6-a zi CNAS; % după stagiu (60 / 70 / 90 %); certificatele doar digitale din 03.2026 | Legea 289/2004 |
| Salariul mediu pentru concediu | HG 426/2004 (perioada de decontare 3 / 12 luni, cu sporurile și premiile incluse) | |

Toate sunt **editabile**, cu „în vigoare din data” — la schimbarea legii se adaugă un rând nou, calculul lunii ia valorile
valabile în luna respectivă.

#### 5.12.2 Tipurile de calcul (flexibile; se adaugă din interfață)

Fiecare **tip de calcul / reținere** are: cod, denumire RO/RU/EN, categoria (**acumulare** / **reținere**), **formula**
(sumă fixă · % din salariul de funcție · % din baza de calcul aleasă · tarif × ore · zile × media zilnică · formulă liberă),
baza de calcul (ce alte tipuri intră în ea), **se impozitează cu impozit pe venit** (da / nu), **se includ CAS** (da / nu),
**se includ CNAM** (da / nu), **plafon neimpozabil** (sumă pe lună / pe an sau % din salariul mediu — partea de sub plafon e
neimpozabilă, **ce depășește devine impozabil și se arată separat**), intră în salariul mediu (da / nu), intră în IPC21 /
IALS21 (coloana / codul), contul contabil, tipărit pe fișa de calcul (da / nu), ordinea de calcul, activ.

**Predefinite** (ce primesc acum în IMSP, conform HG 837/2016 și Codului muncii):

- *Acumulări din timp lucrat*: salariul de funcție (lunar, pro-rata la zile lucrate) · tarif orar · zi de muncă redusă (nocive)
- *Sporuri %*: vechime în muncă (trepte pe ani) · categorie de calificare (a doua / întâi / superioară) · grad științific · titlu ·
  condiții nocive / vătămătoare · intensitate · performanță (semestrial) · suplinire (% din salariul celui înlocuit) · cumul
  intern (% normă) · interimat
- *Timp special*: muncă de noapte (+50 %) · ore suplimentare (150 % / 200 %) · zile de odihnă / sărbătoare (200 %) · gărzi
- *Pe medie*: indemnizația de concediu de odihnă · compensarea concediului nefolosit · indemnizația de eliberare · delegare
  (salariul mediu) · incapacitate temporară (5 zile angajator)
- *Alte plăți*: premiu lunar · premiu unic · ajutor material (cu plafon) · cadouri / vouchere (plafon 10 % salariu mediu) ·
  tichete de masă (neimpozabile până la valoarea nominală) · diurnă (neimpozabilă în plafon) · indemnizația de maternitate /
  îngrijire copil (doar evidență, plătește CNAS)
- *Rețineri*: impozit pe venit (cu scutirile din cererea angajatului) · CNAM 9 % · cotizația sindicală · pensie alimentară
  (% sau sumă, titlu executoriu) · avans · împrumut · prejudiciu · reținere la cerere (asigurare, credit)
- *Angajator (nu se rețin, se calculează)*: CAS 24 %, fondul pentru plata primelor 5 zile de boală

#### 5.12.3 Cele trei documente lunare

1. **Calculul salariului** (pe lună, pe subdiviziune sau toată instituția): se completează automat din pontaj + ordine + sporuri +
   concedii + foi de boală + rețineri permanente; rânduri angajat × tip de calcul × sumă (editabile, cu „corectat manual”);
   calculează scutirile, impozitul, CNAM, CAS; starea: ciornă → verificat → aprobat (după aprobare nu se mai schimbă decât prin
   „recalcul” care face versiune nouă). Tipar: **stat de calcul** (расчётная ведомость) și **fișa de calcul** pe fiecare angajat.
2. **Plata salariului** (stat de plată, платёжная ведомость): din calculul aprobat, minus avansurile plătite, minus reținerile;
   pe modalități (card / numerar); sume de plătit pe angajat; tipar stat de plată cu semnături (pentru numerar) și **lista pentru
   bancă**.
3. **Achitarea** (ordin de plată / dispoziție de casă): data, suma, modalitatea, **fișierul pentru bancă** (format MAIB / Victoriabank
   / Moldindconbank / standard — se preia de la ei), legătura cu documentul de plată; **datoria rămasă** pe angajat; achitarea
   impozitelor și contribuțiilor (sumele pentru ordinele de plată la buget: IV, CAS, CNAM, pe conturi IBAN trezoreriale).

Plus **avans** (document de plată parțială) și **solduri inițiale** (datorii salariale la pornire, din Excel).

#### 5.12.4 Fișa personală a angajatului (salariu)

**Fișa personală de evidență a veniturilor sub formă de salariu și a altor plăți efectuate de către angajator în folosul
angajatului, precum și a impozitului pe venit reținut** (anexa nr. 8 la Regulamentul HG 697/2014, cu modificările din 2020):
se deschide anual pentru fiecare angajat, cu scutirile din cererea depusă (categoria: P, M, S, N, H — codul scutirii din
cerere), lunar: venitul calculat, scutirea acordată, CNAM, venitul impozabil cumulat, impozitul reținut cumulat. **Cartela
(fișa) de calcul** lunară = fluturașul cu toate acumulările și reținerile, soldul (se tipărește / se trimite pe e-mail / portal).

#### 5.12.5 Cererea de scutire

Documentul din 1C *CerereDeScutire* se preia: angajatul, tipul scutirii (personală / majorată / soț-soție / întreținuți cu
IDNP și documente), anul, data depunerii, documentele anexate; alimentează calculul impozitului.

#### 5.12.6 Formularele oficiale generate (structura din actele în vigoare, de verificat la fiecare modificare)

| Formular | Act | Periodicitate / termen | Ce facem |
|---|---|---|---|
| **IPC21** — Darea de seamă privind impozitul pe venit, primele de asigurare medicală și contribuțiile de asigurări sociale | Ordinul MF 94/2020, modificat prin **OMF 56/2026** (din 30.04.2026: codurile categoriilor de asigurați din anexa 3, cod 182 pentru învățământ dual) | lunar, până la 25 a lunii următoare | tabelul 1 (sume pe instituție), tabelul 2 (pe persoane: IDNP, categoria asiguratului, venitul, CAS, CNAM), tabelul 3 (pe funcție/locul de muncă?) → **export XML / Excel** în structura SFS (declarația electronică se depune de contabil) |
| **IALS21** — Nota de informare privind salariul și alte plăți efectuate de angajator în folosul angajaților și impozitul reținut | Ordinul MF 95/2020, modul de completare ajustat la 08.05.2026 | anual, până la **25 ianuarie** | pe persoane: codul sursei de venit (SAL etc.), venitul, scutirile, impozitul reținut → export |
| **Informația privind veniturile calculate și achitate în folosul persoanei fizice și impozitul reținut** | HG 697/2014, art. 92 CF | anual, până la **1 martie**, fiecărui angajat | tipar pe angajat |
| **Fișa personală de evidență a veniturilor** (anexa 8) | HG 697/2014 | anual, pe angajat | tipar |
| **IRM19** — informația privind angajarea / modificarea / încetarea raporturilor de muncă (CNAS) | Legea 489/1999 art. 5 (1¹) | în **10 zile lucrătoare** de la ordin | se generează din ordinele de angajare / modificare / eliberare / concediu de îngrijire a copilului / paternal → export; notificare „IRM19 nedepus” |
| Certificatele de concediu medical (digitale) | Legea 289/2004 | la primire | import / introducere, calculul celor 5 zile |
| **Munca 1** (lunar), **1-IM / Munca 2** (trimestrial), FORPRO, LM | BNS | lunar / trimestrial / anual | cifrele din calcul și din cadre, export Excel în structura formularului |
| Raport statistic pe cadre medicale (MS, nr. 17 / 30) | MS | anual | din modulul de cadre |
| **Stat de calcul**, **stat de plată**, **fișa de calcul**, **lista pentru bancă**, **registrul salariilor**, nota contabilă (export 1C Contabilitate) | interne | lunar | tipar / export |

Formularele exacte (coloanele) se iau din ordinele MF citate și se păstrează ca **șabloane versionate pe an**, ca la schimbarea
formularului să nu se piardă istoricul.

#### 5.12.7 Fluxul lunar

Pontajul închis pe secții → ordinele lunii (sporuri, premii, concedii) → **Calcul** (automat) → verificare pe secție (șeful,
contabilul) → aprobare → **Plată** (avans la 15, restul la sfârșit) → **Achitare** (fișier bancă, casă) → IPC21 → export în
contabilitate. Notificări: pontaj neînchis, calcul neaprobat la data X, IPC21 până la 25, IRM19 restante.

### 5.11 Integrări

- **Import din 1C Personal** (baza Lear / orice bază „Cadre”): angajați cu toate câmpurile, secții, funcții, istoricul ordinelor,
  graficele; prin OData sau Excel (modulul `imports` din CAI).
- **1C Salariu / Contabilitate**: export pontaj, ordine cu efect salarial, liste de angajați; import solduri de concediu la pornire.
- **CNAS / BNS / MS**: fișiere în structura formularelor (Excel), nu depunere directă.
- Viitor: **SIA REA** (Registrul electronic al angajaților), **MSign** pentru semnarea ordinelor, MConnect — când va exista acces.
- E-mail (SMTP).

---

## 6. Forme de tipar cu Stema

Toate formele au același antet: **Stema de Stat a Republicii Moldova** (SVG inclus în sistem, se poate înlocui cu stema / logo-ul
instituției), „REPUBLICA MOLDOVA”, fondatorul (ex. „MINISTERUL SĂNĂTĂȚII” / „CONSILIUL RAIONAL …”), denumirea IMSP, IDNO,
adresă, telefon, e-mail; subsol cu cine a întocmit. Lista formelor: ordinul (pe tipuri + colectiv), extrasul din ordin, statul de
personal, efectivul-limită, organigrama, fișa personală MR-2, adeverința de la locul de muncă, adeverința de vechime, CV, lista
angajaților, graficul concediilor, graficul lunar pe secție, tabela de pontaj, registrul ordinelor, registrul CIM, fișa de evidență
militară, lista documentelor din dosar, cererile-tip (concediu, demisie, transfer) — toate **editabile din interfață** ca în CAI.

---

## 7. Etapele de lucru (propunere)

| Etapa | Conținut | Durată estimată |
|---|---|---|
| **0. Nucleu** | copierea scheletului din CAI (setup, users, core, printing, reports, messaging, help, launcher, installer), redenumirea (CAI Personal, port 8030, ProgramData), tema, panoul de start, Stema în antet, modelul de date org / staff / orders (gol) | 1 săptămână |
| **1. Clasificatoare + state de personal** | toate nomenclatoarele din §4 cu date inițiale (CORM sănătate, articole CM, tipuri de ordine), subdiviziunile, statele de personal cu versiuni și ocuparea posturilor, tipar | 2 săptămâni |
| **2. Dosarul angajatului** | fișa cu toate tab-urile, lista cu filtre, istoricul periodic, documente atașate, checklist, fișa MR-2 și adeverințele la tipar, **importul din 1C Personal** | 3 săptămâni |
| **3. Ordinele** | modelul comun, stările, registrul și numerotarea, cele ~37 tipuri cu efecte asupra dosarului, șabloanele de tipar editabile, ordine colective, anulare / modificare | 4 săptămâni |
| **4. Concedii + timp de muncă** | dreptul și soldul de concediu, graficul anual, cererile, concediile sociale, foile de boală, graficele de lucru, graficul lunar pe secție, tabela de pontaj, export 1C Salariu | 3 săptămâni |
| **5. Rapoarte + notificări** | cele 15 rapoarte, panoul de start, notificările zilnice (sistem / e-mail), exporturile pentru CNAS / BNS / MS | 2 săptămâni |
| **6. Formare, atestare, sănătate, evidență militară** | EMC, atestare, examene medicale, vaccinări, registrul militar și raportul lunar | 1–2 săptămâni |
| **7. Portal angajat** | cabinetul personal, cereri, „am luat cunoștință”, aprobările șefului de secție | 2 săptămâni |
| **8. Livrare** | date demo (un spital fictiv), „Posibilități”, instrucțiuni RO / RU, installer, licență, actualizări, Docker, site de prezentare | 1 săptămână |

Total orientativ: **~4 luni** pentru versiunea 1 completă; prima versiune utilă (etapele 0–3) în ~2,5 luni.

---

## 8. Decizii (v2) și ce mai rămâne de clarificat

**Decise (2026-10-21):** numele **CAI CADRE** · pilot **SCTO Chișinău** · fără bază existentă → **import din Excel** (șabloane
Excel generate de sistem, completate de client, importate cu verificare) · **RO / RU / EN** · **salariul în produs** (§5.12),
bifa „cu / fără salariu” în Constante · etapele 0–4 din §7, apoi **Etapa 4b — Salariu** (3 săptămâni: constante, tipuri de
calcul, cererea de scutire, calcul / plată / achitare, fișa personală, fișa de calcul, IPC21, IALS21, IRM19, lista pentru bancă),
apoi 5–8.

**De clarificat pe parcurs (nu blochează pornirea):**
1. Exemplare de la SCTO: un ordin de fiecare fel, fișa MR-2, registrul ordinelor, statul de personal, statul de plată, fișa de
   calcul, formatul fișierului pentru bancă — ca să reproducem fidel.
2. Numerotarea ordinelor pe registre (ex. „-p” personal, „-c” concedii, „-b” de bază) — după modelul folosit la ei.
3. Uniforma / dulapul (din Lear) — tab opțional „Echipament”, dezactivat implicit.
4. Semnătura: olografă pe tipar în v1; MSign mai târziu.
5. Sporurile exacte de la SCTO (procente, trepte de vechime) — se introduc ca tipuri de calcul la instalare.

---

## 9. Surse consultate

- Configurația `Personal.cf` (despachetată cu `onec_dtools`; inventarul complet al obiectelor în scratchpad).
- CAI ERP Vânzări: `README.md`, `PLAN.md`, `backend/apps`, `backend/requirements.txt`, `frontend/package.json`.
- HG 172/2025 — Conceptul SI EMRU (calm.md, textul proiectului).
- IMSP SCR „T. Moșneaga” — POS-CEP-01 „Pregătirea și gestionarea dosarelor angajaților” (scr.md).
- Decizia CR Telenești 1/2026 — statele de personal IMSP CS Căzănești (telenesti.md) — formatul real al anexelor.
- Ordinele MS 100/2008 (+ 809/2025, 483/2026), 386/2018, 580/2026; HG 837/2016; HG 1223/2004; HG 631/2003 + Ordinul 46/2020;
  Codul muncii 154/2003; monitorul.fisc.md (carnetele de muncă, evidența militară); statistica.gov.md (formularele Munca 1, 1-IM);
  caiete de sarcini mtender.gov.md pentru „1C: Salariu și Managementul personalului”.

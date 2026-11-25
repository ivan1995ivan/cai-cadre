# CAI CADRE

Evidența cadrelor și salarizarea pentru **întreprinderile private** din Republica Moldova (SRL, SA, ÎI): state de personal,
dosarul angajatului (fișa MR-2), toate tipurile de ordine, concedii, timp de muncă, salariu (calcul, plată, achitare,
IPC21 / IALS21 / IRM19), rapoarte și notificări, forme de tipar cu antetul întreprinderii (logo, denumirea cu forma juridică,
IDNO, CAEM, adresa, contactele, contul bancar) și semnăturile din Constante. Interfață RO / RU / EN.
Remunerarea se pune pe fiecare funcție (raport de muncă): salariu lunar, tarif orar, tarife pe tipuri de ore (zbor,
instruire, examinare…) cu orele garantate sau mixt; cumularea funcțiilor / suplinirea pe același contract (CM art. 156) e
separată de cumul — [docs/ro/worktime/hour-types.md](docs/ro/worktime/hour-types.md).
Pentru fabrici — modulul opțional **Producția** (salarizarea în acord): grila tarifară, lucrările cu normele și tarifele lor,
brigăzile cu coeficienții de participare, rapoartele de producție (rebutul pe vinovați, acordul progresiv), din care se
calculează salariul — [docs/ro/production.md](docs/ro/production.md). Timpul fără producție — staționarea și șomajul tehnic
prin ordin, garanția la neîndeplinirea normei, sporul pentru condiții vătămătoare din subdiviziune / funcție, evidența globală a
timpului de muncă — [docs/ro/factory-time.md](docs/ro/factory-time.md); tichetele de masă (borderoul din pontaj, partea
impozabilă în salariu) — [docs/ro/payroll/meal-vouchers.md](docs/ro/payroll/meal-vouchers.md).
Pentru transportatori — modulul opțional **Transportul**: vehiculele, cursele (foaia de parcurs) cu țările parcurse, plata pe km
și diurna șoferilor pe zile și țări după HG 10/2012, în salariu; tahograful — descărcările cardului de conducător (.ddd), zilele
cu activitățile și încălcările limitelor de conducere / odihnă (AETR); GPS-ul vehiculelor (importul zilelor din orice sistem),
combustibilul cursei și KPI-ul șoferilor (fișa lunii, prima KPI în salariu) — [docs/ro/transport.md](docs/ro/transport.md).

Produsul a fost făcut la început pentru un spital de stat (vezi istoricul de mai jos și [PLAN.md](PLAN.md)); trecerea la
sectorul privat — [PLAN-SRL.md](PLAN-SRL.md) (etapa S1: fără Stemă, fondator și actele de stat).

Proiectul pornește din **CAI ERP Vânzări** (`D:\Proiecte Cloude\CAI ERP VInzari`) — același nucleu (asistent de instalare,
utilizatori și roluri, constante, forme de tipar editabile, jurnal de audit, licență, copii de rezervă, actualizări, platforma
cu mai multe baze, installer Windows) — și din configurația 1C `Personal.cf` („Cadre”, Lear Ungheni), analizată în
[PLAN.md](PLAN.md). Prima instalare (1.x): IMSP Spitalul Clinic de Traumatologie și Ortopedie.

**Planul de lucru și starea etapelor:** [PLAN-SRL.md](PLAN-SRL.md) (sectorul privat), [PLAN.md](PLAN.md) (istoricul 1.x).

## Starea actuală

**Versiunea 1.3.0** (2026-10-24): toate etapele din [PLAN.md](PLAN.md) sunt gata — instituția și statele de personal, dosarele,
ordinele, concediile și timpul de muncă, salarizarea (cu IPC21 / IALS21 / IRM19 în XML), termenele și rapoartele, formarea,
sănătatea în muncă, evidența militară, cabinetul angajatului. Notificările: în sistem și pe e-mail.

**Date demo** (întreprinderea privată fictivă „Demo Producție” SRL: 8 subdiviziuni, 67 de angajați de bază, 70 de persoane cu
cumulurile și prestările de servicii): bifa din asistentul de instalare sau `backend> ..\.venv\Scripts\python manage.py crm_demo`,
apoi, pentru un an întreg de evidență, `crm_demo_year`. Utilizatori: `cadre`, `inspector`, `director`, `sef.productie`,
`contabil`, `angajat` (și `admin`, dacă baza nu are administrator), parola `Demo-Cadre-2026`. Descrierea: `docs/instalare.md`
din rădăcina depozitului.

## Cerințe

- Python 3.12+ (testat pe 3.14)
- Node.js 20+ (doar pentru compilarea interfeței)

## Prima pornire (din codul sursă)

```bash
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
cd frontend
npm install
npm run build
cd ..
start.bat
```

Deschideți **http://localhost:8030**. Se pornește asistentul de instalare (limba, baza de date, datele întreprinderii —
denumirea, forma juridică, IDNO, CAEM, adresa, conducătorul, contul bancar —, administratorul). Din alte calculatoare din rețea: `http://<IP-ul serverului>:8030`.

Dezvoltare: `backend` — `..\.venv\Scripts\python manage.py runserver 8030`; `frontend` — `npm run dev` (Vite trimite `/api`
la 8030). Verificări: `npm run typecheck`, `pytest` în `backend`.

## Instalare la client

**Windows (installer):** `cadre-setup-<versiune>.exe` — Python inclus. Programul intră în *Program Files\CAI CADRE*, datele în
*%ProgramData%\CAI-Cadre*, serverul pornește odată cu Windows (sarcina „CAI Cadre Server”), portul 8030 se deschide în firewall,
scurtătura **CAI CADRE** pe desktopul comun. Construirea: `powershell -ExecutionPolicy Bypass -File installer\build.ps1`.

**Linux, Docker (cu PostgreSQL):** pachetul `powershell -ExecutionPolicy Bypass -File tools\make_docker_package.ps1` →
`releases\cai-cadre-docker-<versiune>.tar.gz`. Pe server: `tar xzf cai-cadre-docker-<versiune>.tar.gz`, `cd cai-cadre-<versiune>`,
`sh install.sh` (creează `.env` cu parolele, construiește imaginea, pornește), apoi asistentul de instalare în browser cu
datele PostgreSQL afișate de script. Actualizarea: arhiva nouă dezarhivată peste folder (`.env` rămâne), din nou `sh install.sh`.

## Structura

- `backend/` — Django 6 + DRF: `apps/core` (constantele întreprinderii, audit, licență), `apps/users` (utilizatori, roluri — catalogul
  modulelor în `registry.py`), `apps/setup` (asistentul de instalare, backup, întreținere), `apps/printing` (forme de tipar, antetul `{% company_header %}`),
  `apps/help` (instrucțiunile din `docs/`); modulele de cadre: `org` (subdiviziunile, clasificatoare, state), `staff` (dosarele),
  `orders`, `leave`, `worktime`, `payroll`, `alerts` (termene, e-mail, panoul de start), `reports` (catalogul de rapoarte),
  `training`, `health`, `military`, `portal` (cabinetul angajatului).
- `frontend/` — React 19 + TypeScript + Ant Design 6 (Vite); traducerile în `src/i18n` (`ro*.ts`, `ru*.ts`, `en*.ts`).
- `installer/` — Inno Setup; `tools/` — licențe, release; `docs/` — instrucțiuni RO / RU; `site/` — pagina de prezentare (statică).

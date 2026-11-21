# CAI CADRE

Evidența cadrelor și salarizarea pentru **întreprinderile private** din Republica Moldova (SRL, SA, ÎI): state de personal,
dosarul angajatului (fișa MR-2), toate tipurile de ordine, concedii, timp de muncă, salariu (calcul, plată, achitare,
IPC21 / IALS21 / IRM19), rapoarte și notificări, forme de tipar cu antetul întreprinderii (logo, denumirea cu forma juridică,
IDNO, CAEM, adresa, contactele, contul bancar) și semnăturile din Constante. Interfață RO / RU / EN.

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

**Date demo** (un spital fictiv cu ~50 de angajați): bifa din asistentul de instalare sau
`backend> ..\.venv\Scripts\python manage.py crm_demo`. Utilizatori: `cadre`, `inspector`, `director`, `sef.trauma`,
`contabil`, `angajat`, parola `Demo-Cadre-2026`.

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

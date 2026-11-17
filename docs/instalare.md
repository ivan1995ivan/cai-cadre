# CAI CADRE — instalarea și administrarea pe server (pentru cel care configurează)

Aplicația este **CAI CADRE** (evidența cadrelor și salarizarea pentru instituții
medicale, scrisă de Anatol; codul în `app/`), rulată în stiva Docker a acestui
server: Postgres 17 → `app` (Django + React, port 8000 în rețeaua compose) →
nginx (`127.0.0.1:3960`) → tunelul Cloudflare → `https://cai-cadre.integratii.md`.
Instrucțiunile pentru cine lucrează cu ecranul sunt în aplicație (meniul
**Ajutor**, textele din `app/docs/ro` și `app/docs/ru`).

## Prima pornire

Codul e în depozitul privat `git@github.com:ivan1995ivan/cai-cadre.git`. Pe un
server nou: `git clone git@github.com:ivan1995ivan/cai-cadre.git /srv/projects/cai-cadre`
(cu o cheie SSH care are acces la depozit), apoi pașii de mai jos.

1. `cp .env.example .env && chmod 660 .env`; parolele generate cu comenzile din
   șablon: `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `SECRET_KEY`,
   `CRM_CONSOLE_PASSWORD`; `APP_ORIGINS=http://127.0.0.1:3960` până la tunel.
2. `docker compose up -d --build` — construiește imaginea (npm + pip, câteva
   minute) și pornește tot. `docker compose ps`: `db`, `app`, `web`, `backup`
   trebuie să fie `healthy`.
3. Aplicația pornește în **modul instalare** (asistentul din browser, sau API-ul
   lui). Asistentul se deschide **doar local** — din internet `/api/setup/*`
   (în afară de `status/`) dă 404, altfel primul venit și-ar crea
   administratorul —, deci de pe calculatorul tău, printr-un tunel SSH:
   `ssh -L 3960:127.0.0.1:3960 <utilizator>@<server>`, apoi
   `http://127.0.0.1:3960` în browser. Valorile pentru pasul „Baza de date”: tip **PostgreSQL**, gazda `db`,
   portul `5432`, baza `caicadre`, utilizatorul `caicadre_app`, parola =
   `APP_DB_PASSWORD` din `.env`. Baza există deja (o creează Postgres la prima
   pornire, cu rolul `caicadre_app` proprietar — `deploy/db/10-app-role.sh`), deci
   se alege „Instalare nouă”, nu „Creează baza”.
4. La instalare se dau: limba, datele instituției (numele se schimbă oricând în
   **Administrare → Setări → Constante**), administratorul și, dacă e nevoie de o prezentare, bifa **date demo**.
   Instalarea rulează migrările, încarcă clasificatoarele și repornește serverul.

Această instalare e **curată** (fără date demo): instituția și administratorul
se dau în asistent. Cu bifa demo apar și utilizatorii `cadre`, `inspector`,
`director`, `sef.trauma`, `contabil`, `angajat` cu parola `Demo-Cadre-2026` —
doar pentru prezentări, niciodată pe o bază cu date reale.

## Datele demo pe un an (doar pentru prezentări)

`crm_demo` (bifa din asistent) pune structura, ~70 de angajați și o singură
lună de pontaj și salariu. Peste ea, **o singură dată**:

```bash
docker compose exec app python manage.py crm_demo_year
```

Comanda (codul: `app/backend/apps/core/demo_year.py`) completează evidența din **noiembrie anul trecut până în luna
curentă**, totul prin serviciile modulelor, în ordine cronologică:

- graficele de lucru: asistentele și infirmierele din secții pe ture de 12 ore
  (zi / noapte), medicii ATI pe gărzi de 24 de ore; graficele lunare (gărzi)
  aprobate, cel pe luna următoare — ciornă;
- tabelele de pontaj ale tuturor subdiviziunilor, închise (luna curentă —
  ciornă), cu noapte, sărbători, ore suplimentare și codurile absențelor;
- salariul: avansul pe 15 ale lunii (achitat), calculul lunar aprobat (luna
  curentă — ciornă), îndreptarea spre plată în baza calculului, în luna
  următoare (achitată; aici se rețin CNAM și impozitul), cu
  sporuri de vechime și categorie, condiții nocive, noapte, sărbători,
  suplimentare, indemnizații de concediu și de boală, premii, ajutor
  material, cotizația sindicală, o pensie alimentară, un împrumut, plata la
  contractul de prestări servicii; cererile de scutire pentru ~80 % din
  angajați; datele de bancă (IBAN) pentru plata pe card;
- ordinele anului, semnate și numerotate pe registre: concediile din graficul
  anual (ordine colective lunare), delegări, perfecționare (cu înregistrările
  EMC), premii trimestriale, ajutor material, sporuri pentru condiții nocive,
  majorări de salariu, conferirea categoriei (cu atestările), două angajări, o
  eliberare cu compensarea concediului, un concediu neplătit, zile libere
  plătite;
- foile de boală (2–4 pe lună), graficul concediilor pe subdiviziuni aprobat
  prin ordin, planul de formare pe an, atestările planificate.

Dacă baza are deja calcule lunare, comanda refuză; `--force` șterge calculele,
plățile, tabelele și graficele existente și le reface (ordinele și absențele
rămân). Pe o bază curată: `docker compose down`, ștergerea volumelor `cai-cadre-db`
și `cai-cadre-data`, `up`, asistentul cu bifa demo (local, prin tunelul SSH de la
„Prima pornire”), apoi comanda de mai sus.

## Tunelul (îl face Ion)

`TUNNEL_TOKEN` în `.env` (profilul `tunnel` se activează singur), în panoul
Cloudflare Zero Trust → Tunnels → Public Hostname: `cai-cadre.integratii.md` →
HTTP `cai-cadre-web:80`; `APP_ORIGINS=https://cai-cadre.integratii.md`; `docker compose
up -d`. Verificare: `nslookup cai-cadre.integratii.md 1.1.1.1`,
`curl -I https://cai-cadre.integratii.md/health` → 200.

## Rețeaua Docker

Stiva are subrețeaua fixă `10.219.0.0/28` (`networks` în `docker-compose.yml`),
fiindcă plajele implicite ale Docker de pe acest server sunt epuizate — fără ea
`up` cade cu „all predefined address pools have been fully subnetted”. Proba
restaurării folosește `10.219.0.16/28`, `deploy/nginx-test.sh` —
`10.219.0.32/29`. Pe alt server, dacă `10.219.0.0/28` e ocupată, se schimbă
acolo.

## Unde stau datele

- **Baza**: volumul `cai-cadre-db`.
- **Instanța aplicației**: volumul `cai-cadre-data`, montat în `/data`
  (`CRM_INSTANCE_DIR`): `config.json` (conexiunea la bază, parola criptată),
  `secret.json` (cheia Fernet care descifrează parola din `config.json` și
  parola SMTP din bază; `SECRET_KEY` vine din `.env`), `bases.json` și
  `platform-console.json` (platforma), `media/` (fișierele încărcate),
  `static/` (se reface la pornire), `backups/` (copiile aplicației, mai jos).
- Ștergerea volumului `cai-cadre-data` readuce aplicația în modul instalare și
  pierde cheia Fernet; ștergerea `cai-cadre-db` pierde datele. Ambele se refac
  doar din copie (mai jos).

## Copiile de siguranță

Serviciul `backup` (`backup.sh`), zilnic la 02:30 și la fiecare pornire a lui;
manual: `docker compose exec backup cai-cadre-backup`. O copie a zilei, în `./backups`:

| Fișier | Ce conține |
|---|---|
| `cai-cadre-AAAA-LL-ZZ.dump` | baza (`pg_dump -Fc`) |
| `cai-cadre-AAAA-LL-ZZ.instance.tar.gz` | fișierele instanței (`config.json`, `secret.json`, `bases.json`, `platform-console.json`) — cheile cu care se citește copia bazei din aceeași zi |
| `media/` | oglinda fișierelor încărcate, comună tuturor zilelor (numele sunt unice) |

- Se păstrează `BACKUP_KEEP_DAYS` zile (implicit 14).
- Copiile au date personale: folderul și fișierele sunt fără drepturi pentru
  „other” (`backup.sh` le pune la fiecare rulare) — le citesc doar Ion și
  Anatol (grupul `proj-cai-cadre`).
- `backup` e `healthy` doar dacă o rulare **completă** (baza + instanța +
  media) s-a terminat fără erori în ultimele 26 de ore (`backups/.last-ok`).
- `backup.sh` e montat ca fișier: după o editare,
  `docker compose up -d --no-deps --force-recreate backup`.
- **Copiile stau pe același server** — nu apără de pierderea serverului.
  Copia în afara serverului: de hotărât unde (vezi `CLAUDE.md`, „Următorii pași”).

Aplicația își face și ea o copie zilnică la 02:00 (`/data/backups/crm-daily-*.zip`,
cu `database.pgdump`, ultimele 14; setările în **Administrare → Întreținere**).
Merge (în imagine e `pg_dump` 17), dar stă în același volum `cai-cadre-data` și nu
are fișierele instanței — pentru restaurare se folosește copia din `./backups`.

## Restaurarea

`restore.sh`, rulat de serviciul de unică folosință `restore` (profilul
`restore`, nu pornește la `up`). Cu aplicația oprită:

```bash
docker compose stop app
docker compose run --rm restore                # lista copiilor din ./backups
docker compose run --rm restore 2026-10-26     # restaurează copia acelei zile
docker compose up -d
```

- Copia se restaurează într-o bază nouă și abia apoi numele se schimbă: baza
  de dinainte rămâne ca `caicadre_inainte_<data>_<ora>`. Dacă s-a ales copia
  greșită, se dă înapoi cu două `ALTER DATABASE … RENAME`; după verificare cea
  veche se șterge (comanda o afișează scriptul):
  `docker compose exec db dropdb -U caicadre caicadre_inainte_…`.
- Fișierele instanței din copie se pun peste cele din volum; `media/` se
  completează cu ce lipsește din oglindă (fișierele încărcate după data copiei
  rămân, fără legătură în bază).
- Scriptul refuză dacă aplicația rulează, dacă rolul `caicadre_app` lipsește sau
  dacă volumul `cai-cadre-data` nu a fost creat de aplicație; arhivele se citesc
  complet înainte de orice ștergere.

**Pe un server nou**: proiectul din git, `.env` (aceleași parole — parola
`caicadre_app` trebuie să fie cea din `config.json` al copiei), folderul `backups/`
copiat, apoi:

```bash
docker compose up -d --wait app      # baza goală cu rolul caicadre_app; aplicația creează volumul cai-cadre-data
docker compose stop app
docker compose run --rm restore AAAA-LL-ZZ
docker compose up -d
```

**Proba restaurării** — lunar și după orice schimbare în `backup.sh` /
`restore.sh`:

```bash
./restore-check.sh              # ultima copie (sau ./restore-check.sh AAAA-LL-ZZ)
```

Ridică alături o copie izolată a stivei (proiectul compose `cai-cadre-proba`:
volume proprii, fără tunel, fără nginx, fără port pe gazdă), restaurează în ea
copia exact ca mai sus, pornește aplicația și verifică că se citesc datele cu
cheile din copie; la final o șterge. Stiva `cai-cadre` nu e atinsă.

## Protecțiile din nginx (`deploy/nginx/default.conf`)

- **Din internet** (cererile prin tunel au antetul `CF-Connecting-IP`) dau 404:
  `/__platform/…` (lista bazelor și consola serverului) și `/api/setup/…` în
  afară de `status/` (asistentul de instalare). Local (`127.0.0.1:3960`, tunel
  SSH) merg.
- Căile cu segmente `.` / `..` (și `%2e`) → 400: browserele nu le trimit, iar
  fără refuz ar ocoli regula de mai sus.
- **Limita autentificării**: `POST /api/auth/login/` — 10 pe minut de pe un IP,
  cu 20 în rafală, apoi 429 cu mesajul „Prea multe încercări…” pe ecranul de
  intrare. E pe IP: tot spitalul poate ieși printr-un singur IP, dar tokenul
  ține 7 zile, deci intrările sunt rare. Dacă oamenii văd mesajul la
  începutul turei, se mărește `rate` / `burst`. Limita pe cont (blocarea după
  N parole greșite) ține de aplicație.
- **Content-Security-Policy** pe HTML și SVG: scripturi doar din fișierele
  aplicației, stiluri inline (Ant Design), `data:` / `blob:` pentru imagini și
  descărcări. Verificat în browser pe toate ecranele (51 de pagini, rolurile
  cadre / contabil / angajat, tiparul, service worker-ul) — nicio încălcare.
  Cloudflare adaugă singur în pagini scriptul Web Analytics
  (`static.cloudflareinsights.com/beacon.min.js`); CSP-ul îl blochează
  (un script străin n-are ce căuta pe pagini cu IDNP și salarii), deci în
  consola browserului apare o eroare — se oprește din panoul Cloudflare
  (Web Analytics / RUM pentru `cai-cadre.integratii.md`).
- `X-Forwarded-For` spre aplicație = doar IP-ul real al vizitatorului (nu
  lanțul primit, al cărui prim element îl scrie vizitatorul).

Înainte de `nginx -s reload` pe server (și în CI):

```bash
./deploy/nginx-test.sh     # nginx de unică folosință + aplicație-ecou; toate „ok”
```

## Actualizarea

`git pull && docker compose up -d --build`. Migrările rulează la pornirea
containerului (`manage.py crm_upgrade` în `app/backend/run.py`). Actualizarea
din interfața aplicației (Întreținere → Actualizări) e dezactivată în Docker
(`CRM_DOCKER=1`) — se face doar prin imagine nouă.

## Licența

Fără licență aplicația merge 30 de zile în regim de probă (toate modulele, max.
10 utilizatori), apoi rămâne **doar pentru citire**. Licența o emite Anatol cu
`app/tools/license_tool.py` (cheia privată nu e în depozit) și se introduce în
**Administrare → Licență**. Cele 30 de zile se numără de la instalare.

## Consola platformei

`/__platform/console` (starea serverului, bazele) se deschide **doar local** —
prin tunel dă 404 —, de pe calculatorul tău cu
`ssh -L 3960:127.0.0.1:3960 <utilizator>@<server>` și
`http://127.0.0.1:3960/__platform/console`; cere parola `CRM_CONSOLE_PASSWORD`
din `.env`.

## Verificări

```bash
docker compose ps                          # toate healthy
curl -s http://127.0.0.1:3960/health       # {"status": "ok", "version": "1.6.0", "installed": true}
docker compose logs -f app
curl -s -X POST http://127.0.0.1:3960/api/auth/login/ -H 'Content-Type: application/json' \
     -d '{"username":"admin","password":"…"}'   # întoarce access/refresh
curl -s -o /dev/null -w '%{http_code}\n' https://cai-cadre.integratii.md/__platform/console   # 404
./deploy/nginx-test.sh                     # comportamentul nginx
./restore-check.sh                         # proba restaurării ultimei copii
```

Testele aplicației, în container de unică folosință (ca în CI):

```bash
docker run --rm -v "$PWD/app:/src:ro" -e PYTHONDONTWRITEBYTECODE=1 -w /src/backend python:3.13-slim sh -c \
  'apt-get update -qq >/dev/null && apt-get install -y -qq unixodbc >/dev/null; grep -v ^mysqlclient requirements.txt > /tmp/r.txt && pip install -q -r /tmp/r.txt && pytest -q -p no:cacheprovider'
```

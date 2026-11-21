# CAI CADRE

Instalarea produsului **CAI CADRE** (evidența cadrelor și salarizarea pentru
întreprinderi private din Republica Moldova — SRL, cu profilurile IT Park, fabrică, aviație,
transport; Django + React, de Anatol — codul în `app/`, descrierea în
`app/README.md`) pe serverul `integratii.md`: `https://cai-cadre.integratii.md`.
Proiect de sine stătător, desprins la 2026-11-17 din instalarea SCTO
(`/srv/projects/scto`, CAI CADRE 1.6.0); de aici codul merge pe drumul lui. Starea și pașii
următori: `CLAUDE.md`, secțiunea **Status**; instalarea și administrarea pe
server: `docs/instalare.md`. Planul trecerii de la varianta de spital (IMSP) la cea pentru
întreprinderi private: `app/PLAN-SRL.md`.

Instalarea e **curată**: fără date demo, întreprinderea și administratorul se dau
în asistentul de instalare (doar local, prin tunel SSH).

## Rulare pe server

```bash
cd /srv/projects/cai-cadre
cp .env.example .env && chmod 660 .env     # o singură dată; completează parolele
docker compose up -d --build               # pornește / actualizează stiva
docker compose ps                          # toate serviciile: healthy
curl -s http://127.0.0.1:3960/health       # verificare locală, fără tunel
```

Stiva: Postgres 17 (`db`) + copie zilnică (`backup`, în `./backups`) +
aplicația (`app`, în `app/`) + nginx (`web`, doar `127.0.0.1:3960`) +
tunelul Cloudflare (`cloudflared`, pornit automat când `TUNNEL_TOKEN` e
completat în `.env`). Codul: `git@github.com:ivan1995ivan/cai-cadre.git` (privat).
Deploy = `git pull && docker compose up -d --build`.

Copia zilnică (baza + fișierele instanței cu cheile + fișierele încărcate) e
în `./backups`; la cerere: `docker compose exec backup cai-cadre-backup`.
Restaurarea: `docker compose stop app && docker compose run --rm restore
AAAA-LL-ZZ && docker compose up -d`; proba restaurării, izolat:
`./restore-check.sh`. Prima pornire trece prin asistentul de instalare al
aplicației, care se deschide doar local (tunel SSH), nu din internet; tot
local merge consola `/__platform/console`. Detalii: `docs/instalare.md`.

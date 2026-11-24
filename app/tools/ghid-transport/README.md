# Ghidul transportului: documentul Word și video-ul

Rezultatul stă în `app/docs/files/` (`transport-instructiune.docx`, `transport-video.webm`) și se deschide din program:
Ajutor (F1) → Transportul (`/api/help/files/…`). Se refac când se schimbă ecranele transportului.

Totul rulează în containere de unică folosință, într-o rețea izolată, pe o bază demo nouă — nu pe stiva `cai-cadre`.

1. **Copia de probă** (imaginea de test `cai-cadre-test`, frontend-ul construit în `FE/dist`, subrețea liberă din `10.219.0.0/24`):
   ```bash
   docker network create --subnet 10.219.0.40/29 cai-cadre-guide
   docker run -d --name cai-cadre-guide-app --network cai-cadre-guide --network-alias app -e CRM_INSTANCE_DIR=/tmp/inst \
     -v $APP/backend:/src/backend:ro -v $APP/docs:/src/docs:ro -v $FE:/src/frontend:ro -v $PWD:/work:ro -v $OUT:/out -w /src/backend \
     --entrypoint sh cai-cadre-test -c "S=config.test_settings; python manage.py migrate -v0 --settings=\$S && \
       python manage.py crm_seed --settings=\$S && python manage.py crm_demo --settings=\$S && \
       python manage.py crm_admin --username admin --password Parola-Sigura-2026 --settings=\$S && \
       python manage.py shell --settings=\$S < /work/setup.py && python manage.py runserver 0.0.0.0:8000 --noreload --settings=\$S"
   ```
   `setup.py` — modulul, cursul EUR, vehiculele, tarifele, actele șoferului, cursa internațională aprobată, fișierul .ddd (în `/out`),
   calculul lunii.
2. **Capturile**: `shots.py` (Playwright 1.49, imaginea `mcr.microsoft.com/playwright/python:v1.49.0-noble`, rețeaua de mai sus,
   `-v $OUT:/out:ro -v $SHOTS:/shots`).
3. **Video-ul**: `video.py` (același container, `-v $VIDEO:/video`) → `transport-video.webm`; comprimat în VP9:
   `ffmpeg -i transport-video.webm -c:v libvpx-vp9 -crf 40 -b:v 0 -an docs/files/transport-video.webm`.
4. **Documentul Word**: `npm install docx@9`, apoi `node build.js $SHOTS docs/files/transport-instructiune.docx` (node:22-slim).
5. La sfârșit: `docker rm -f cai-cadre-guide-app && docker network rm cai-cadre-guide`.

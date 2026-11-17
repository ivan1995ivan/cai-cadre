# Imaginea serverului CAI CADRE: interfața compilată + backend-ul Django servit de waitress.
#   docker compose up -d          (cu PostgreSQL, vezi docker-compose.yml)
# Datele instanței (configurația, cheile, fișierele încărcate, copiile de rezervă) stau în volumul /data.

FROM node:22-alpine AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    CRM_INSTANCE_DIR=/data \
    CRM_DOCKER=1
# pg_dump pentru copiile de rezervă PostgreSQL; unixODBC pentru MS SQL (driverul Microsoft se adaugă separat, dacă e nevoie)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client unixodbc \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
# mysqlclient cere compilator: în imagine MySQL merge prin PyMySQL; testele nu intră în imagine
RUN grep -v -E "^(mysqlclient|pytest)" backend/requirements.txt > /tmp/req.txt \
    && pip install -r /tmp/req.txt
COPY backend/ backend/
COPY docs/ docs/
COPY --from=web /app/frontend/dist frontend/dist
RUN rm -rf backend/tests && useradd --system --home /data cadre && mkdir -p /data && chown cadre /data
USER cadre
VOLUME /data
EXPOSE 8000
WORKDIR /app/backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/setup/status/', timeout=4)"
# platforma (launcher.py): bazele și consola serverului (/__platform/console; din rețea cu CRM_CONSOLE_PASSWORD)
CMD ["python", "launcher.py", "--host", "0.0.0.0", "--port", "8000"]

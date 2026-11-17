#!/bin/sh
# Proba restaurării: ridică alături o copie izolată a stivei — proiectul compose
# `cai-cadre-proba`, cu volume proprii, fără tunel, fără nginx, fără port pe gazdă și
# fără serviciul `backup` —, restaurează în ea o copie din ./backups (restore.sh,
# ca la o restaurare reală) și verifică că aplicația pornește pe ea: conexiunea
# la bază se descifrează cu cheile din copie, datele se citesc, fișierele
# instanței sunt ale aplicației. Stiva `cai-cadre` nu e atinsă; la final copia
# izolată se șterge cu tot cu volumele ei.
#   ./restore-check.sh              # ultima copie
#   ./restore-check.sh 2026-10-26   # copia unei zile
# O copie care n-a fost niciodată restaurată nu e o copie: proba se face lunar
# și după orice schimbare în backup.sh / restore.sh.
set -eu
cd "$(dirname "$0")"

PROJECT=cai-cadre-proba
STAMP=${1:-$(ls -1 backups | sed -n 's/^cai-cadre-\(.*\)\.dump$/\1/p' | sort | tail -n 1)}
if [ -z "$STAMP" ]; then
    echo "Nicio copie în ./backups." >&2
    exit 1
fi

# Fără tunel: cu TUNNEL_TOKEN un al doilea `cloudflared` ar primi trafic public.
# Variabilele din mediu au întâietate față de .env.
export TUNNEL_TOKEN= COMPOSE_PROFILES=
# subrețea proprie, alta decât a stivei (vezi `networks` în docker-compose.yml)
dc() { STACK_SUBNET=10.219.0.16/28 docker compose -p "$PROJECT" "$@"; }
cleanup() { dc down -v --remove-orphans > /dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 130' INT TERM
cleanup   # rămășițele unei probe întrerupte

echo "== proba restaurării copiei $STAMP (proiectul $PROJECT)"
# ca pe un server nou: baza goală (cu rolul caicadre_app) și aplicația în modul
# asistent, care creează volumul cai-cadre-data cu utilizatorul ei
dc up -d --wait app
dc stop app
dc run --rm restore "$STAMP"
dc up -d --wait app

echo "== verificări"
dc exec -T app python manage.py shell --no-imports -c '
import json, os
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.staff.models import Employee
from apps.orders.models import Order
assert not settings.SETUP_MODE, "aplicația a pornit în modul asistent: config.json nu a fost restaurat"
for name in ("config.json", "secret.json"):
    path = os.path.join(os.environ["CRM_INSTANCE_DIR"], name)
    assert os.access(path, os.W_OK), f"{name} nu poate fi scris de aplicație"
users, employees, orders = get_user_model().objects.count(), Employee.objects.count(), Order.objects.count()
assert users and employees, "baza restaurată e goală"
print(f"ok: utilizatori {users}, angajați {employees}, ordine {orders}")
'
echo "== proba a trecut: copia $STAMP se restaurează și aplicația pornește pe ea"

#!/bin/sh
# Restaurarea CAI CADRE dintr-o copie făcută de backup.sh: baza, fișierele instanței
# și media. Rulează în containerul de unică folosință `restore` (profilul
# `restore` din docker-compose.yml), cu aplicația OPRITĂ:
#   docker compose stop app
#   docker compose run --rm restore              # lista copiilor
#   docker compose run --rm restore 2026-10-26   # restaurează copia acelei zile
#   docker compose up -d
# Pașii, pe server nou și proba restaurării: docs/instalare.md, „Restaurarea”.
#
# Baza curentă NU se șterge: copia se restaurează într-o bază nouă și abia la
# final numele se schimbă — `caicadre` devine `caicadre_inainte_<data-ora>`, cea nouă
# devine `caicadre`. Dacă s-a ales copia greșită, se dă înapoi cu două redenumiri;
# după verificare cea veche se șterge de mână (comanda e afișată la final).
set -eu

DB=caicadre
APP_ROLE=caicadre_app
NEW="${DB}_restaurare"
DATA=/appdata

list() {
    echo "Copiile din ./backups:"
    ls -1 /backups | sed -n 's/^cai-cadre-\(.*\)\.dump$/  \1/p'
}
sql() { PGOPTIONS='-c client_min_messages=warning' psql -h db -U caicadre -d postgres -v ON_ERROR_STOP=1 -qAtc "$1"; }

if [ $# -ne 1 ]; then
    list
    echo "Folosire: docker compose run --rm restore AAAA-LL-ZZ" >&2
    exit 2
fi
STAMP=$1
DUMP="/backups/cai-cadre-$STAMP.dump"
INST="/backups/cai-cadre-$STAMP.instance.tar.gz"
if [ ! -f "$DUMP" ]; then
    echo "Nu există copia bazei $DUMP." >&2
    list >&2
    exit 1
fi

# --- verificări, înainte de a schimba ceva ---
# Aplicația pornită ar scrie în bază în timpul restaurării și ar rămâne cu
# cheile vechi în memorie (`up -d` nu repornește un container neschimbat).
# Conexiunile din pg_stat_activity nu ajung: Django închide conexiunea după
# fiecare cerere, deci o aplicație pornită dar liberă nu are niciuna. Numele
# `app` se rezolvă în rețeaua compose doar cât containerul rulează.
if wget -q -T 3 -O /dev/null http://app:8000/health 2> /dev/null; then
    echo "Aplicația rulează. Opriți-o întâi: docker compose stop app" >&2
    exit 1
fi
busy=$(sql "SELECT count(*) FROM pg_stat_activity WHERE usename = '$APP_ROLE'")
if [ "$busy" != 0 ]; then
    echo "Rolul $APP_ROLE are $busy conexiuni deschise la bază (alt container al aplicației?). Opriți-le întâi." >&2
    exit 1
fi
if [ "$(sql "SELECT count(*) FROM pg_roles WHERE rolname = '$APP_ROLE'")" != 1 ]; then
    echo "Rolul $APP_ROLE lipsește: baza nu a fost inițializată de deploy/db/10-app-role.sh." >&2
    exit 1
fi
# volumul îl creează aplicația la prima pornire, cu utilizatorul ei; restaurat
# într-un volum creat de acest container, fișierele ar fi ale lui root și
# aplicația nu le-ar putea scrie
OWNER=$(stat -c %u:%g "$DATA")
if [ "${OWNER%%:*}" = 0 ]; then
    echo "Volumul cai-cadre-data nu a fost creat de aplicație. Porniți-o o dată (docker compose up -d app)," >&2
    echo "opriți-o (docker compose stop app) și reluați restaurarea." >&2
    exit 1
fi
# arhivele se citesc complet: una deteriorată oprește totul înainte de ștergeri
pg_restore --list "$DUMP" > /dev/null
if [ -f "$INST" ]; then
    tar -tzf "$INST" > /dev/null
else
    echo "Atenție: lipsește $INST — rămân fișierele instanței din volum (config.json, secret.json)." >&2
fi

# --- baza: într-o bază nouă, apoi schimbarea numelor ---
sql "DROP DATABASE IF EXISTS $NEW"
sql "CREATE DATABASE $NEW OWNER $APP_ROLE"
# proprietarul obiectelor (caicadre_app) vine din copie
pg_restore -h db -U caicadre -d "$NEW" --exit-on-error --single-transaction "$DUMP"
OLD=""
if [ "$(sql "SELECT count(*) FROM pg_database WHERE datname = '$DB'")" = 1 ]; then
    OLD="${DB}_inainte_$(date +%Y%m%d_%H%M%S)"
    sql "ALTER DATABASE $DB RENAME TO $OLD"
fi
sql "ALTER DATABASE $NEW RENAME TO $DB"
echo "baza: restaurată din $DUMP"

# --- fișierele instanței ---
if [ -f "$INST" ]; then
    tar -xzf "$INST" -C "$DATA"
    (cd "$DATA" && tar -tzf "$INST" | xargs chown "$OWNER")
    echo "instanța: $(tar -tzf "$INST" | tr '\n' ' ')"
fi

# --- media: se completează ce lipsește din oglindă (numele sunt unice) ---
if [ -d /backups/media ]; then
    mkdir -p "$DATA/media"
    COPIED=$(cd /backups/media && find . -type f ! -name '*.part' | while read -r f; do
        if [ ! -e "$DATA/media/$f" ]; then
            mkdir -p "$DATA/media/$(dirname "$f")" && cp -p "$f" "$DATA/media/$f" || exit 1
            echo x
        fi
    done | wc -l)
    chown -R "$OWNER" "$DATA/media"
    echo "media: $COPIED fișiere puse la loc"
fi

echo
echo "Gata. Porniți aplicația: docker compose up -d"
if [ -n "$OLD" ]; then
    echo "Baza dinainte a rămas ca $OLD. După ce verificați aplicația, ștergeți-o:"
    echo "  docker compose exec db dropdb -U caicadre $OLD"
fi

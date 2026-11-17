#!/bin/sh
# Rolul cu care se conectează aplicația: `caicadre_app`, **fără** drepturi de
# superuser. Rulează o singură dată, la prima pornire a bazei (postgres:17
# îl ia din /docker-entrypoint-initdb.d/ doar când volumul e gol).
#
# `caicadre` (POSTGRES_USER) e superuser — rămâne pentru copii de siguranță și
# administrare; aplicația nu are nevoie de superuser, iar Row Level Security
# (dacă va fi folosit) nu se aplică superuserilor. `caicadre_app` e proprietarul
# bazei (deci și al schemei `public`, în care creează tabelele la migrare).
#
# APP_DB_CREATEDB=1 doar pentru baza de test / CI (testele își creează
# propria bază). Pe server nu se pune.
set -eu

: "${APP_DB_PASSWORD:?APP_DB_PASSWORD lipsește (parola rolului aplicației)}"
createdb=""
[ "${APP_DB_CREATEDB:-}" = "1" ] && createdb="CREATEDB"
# parola intră într-un literal SQL: un apostrof se dublează
password=$(printf '%s' "$APP_DB_PASSWORD" | sed "s/'/''/g")

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE caicadre_app LOGIN NOSUPERUSER NOCREATEROLE NOBYPASSRLS NOINHERIT $createdb PASSWORD '$password';
ALTER DATABASE "$POSTGRES_DB" OWNER TO caicadre_app;
EOSQL
echo "rol caicadre_app creat (NOSUPERUSER, NOBYPASSRLS), proprietar al bazei $POSTGRES_DB"

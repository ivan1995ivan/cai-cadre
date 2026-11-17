#!/bin/sh
# Copia de siguranță a CAI CADRE — rulată zilnic de cron în containerul `backup`
# (vezi docker-compose.yml) și manual cu:
#   docker compose exec backup cai-cadre-backup
#
# O copie a zilei = trei părți, toate în ./backups:
#   cai-cadre-AAAA-LL-ZZ.dump              baza (pg_dump -Fc)
#   cai-cadre-AAAA-LL-ZZ.instance.tar.gz   fișierele instanței: config.json (conexiunea),
#                                     secret.json (cheia care descifrează parolele din
#                                     config.json și din bază), setările platformei
#   media/                            oglinda fișierelor încărcate (comună tuturor zilelor)
# Restaurarea: restore.sh (docs/instalare.md, „Restaurarea”).
#
# Fiecare fișier se scrie întâi ca .part și se redenumește la final: o copie
# întreruptă la jumătate nu poate fi confundată cu una completă. La sfârșitul
# unei rulări reușite se atinge `.last-ok` — healthcheck-ul serviciului îl
# urmărește, deci orice parte eșuată face serviciul „unhealthy”.
set -eu

STAMP=$(date +%F)
FILE="/backups/cai-cadre-$STAMP.dump"
INST="/backups/cai-cadre-$STAMP.instance.tar.gz"
INSTANCE="${INSTANCE_SRC:-/appdata}"

# Copiile au date personale (IDNP, salarii, scanări de acte): le citesc doar
# proprietarul și grupul proj-cai-cadre. umask nu ajunge — folderul are ACL implicit
# care dă citire tuturor —, deci drepturile se pun explicit: întâi folderul (fără
# el nimic dinăuntru nu e accesibil), la final tot ce e în el.
chmod o= /backups

pg_dump -h db -U caicadre -Fc caicadre > "$FILE.part"
mv "$FILE.part" "$FILE"
echo "backup ok: $FILE ($(du -h "$FILE" | cut -f1))"

# fișierele instanței (volumul cai-cadre-data, montat read-only): o arhivă pe zi lângă
# copia bazei — o copie veche se restaurează cu cheile ei. Doar fișierele de pe
# primul nivel: media/ are oglinda de mai jos, static/ se reface la pornire,
# backups/ și updates/ sunt ale aplicației; fără jurnale și fișierele temporare
# ale asistentului. Până la instalare (asistentul) config.json nu există.
if [ -f "$INSTANCE/config.json" ]; then
    (cd "$INSTANCE" && find . -maxdepth 1 -type f ! -name '*.log' ! -name 'install-*.json' | tar -czf - -T -) > "$INST.part"
    mv "$INST.part" "$INST"
    echo "instanța ok: $INST ($(tar -tzf "$INST" | tr '\n' ' '))"
fi

# păstrăm ultimele BACKUP_KEEP_DAYS zile (implicit 14)
find /backups -maxdepth 1 \( -name 'cai-cadre-*.dump' -o -name 'cai-cadre-*.instance.tar.gz' \) -mtime +"${BACKUP_KEEP_DAYS:-14}" -delete
find /backups -maxdepth 1 -name 'cai-cadre-*.part' -mtime +1 -delete

# fișierele încărcate (MEDIA_SRC = folderul media din volumul aplicației): o
# oglindă în backups/media. Numele sunt unice și nu se rescriu, deci se copiază
# doar ce lipsește. Fișier cu fișier: `cp -a -n` din BusyBox nu copiază nimic
# într-un director existent și iese totuși cu 0. Până la prima încărcare
# folderul media nu există.
MEDIA="${MEDIA_SRC:-/media}"
if [ -d "$MEDIA" ]; then
    mkdir -p /backups/media
    COPIED=$(cd "$MEDIA" && find . -type f | while read -r f; do
        if [ ! -e "/backups/media/$f" ]; then
            mkdir -p "/backups/media/$(dirname "$f")" && cp -p "$f" "/backups/media/$f.part" \
                && mv "/backups/media/$f.part" "/backups/media/$f" || exit 1
            echo x
        fi
    done | wc -l)
    SOURCE=$(find "$MEDIA" -type f | wc -l)
    TOTAL=$(find /backups/media -type f ! -name '*.part' | wc -l)
    [ "$TOTAL" -ge "$SOURCE" ] || { echo "fișiere: copia are $TOTAL, volumul $SOURCE" >&2; exit 1; }
    echo "fișiere ok: $COPIED noi, $TOTAL în copie"
fi

touch /backups/.last-ok
chmod -R o= /backups

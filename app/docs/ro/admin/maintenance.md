# Copii de rezervă și actualizări

## Copii de rezervă
O copie este o arhivă ZIP cu **baza de date** și **fișierele încărcate** (fotografiile angajaților, actele scanate,
logo-urile, ștampila).
- Se face **singură în fiecare zi** după ora aleasă, **înainte de fiecare actualizare** și înainte de migrațiile bazei.
- **Fă o copie acum** — înainte de o operație importantă (import mare, închiderea lunii).
- Se păstrează ultimele *N* copii automate (setarea „păstrează ultimele”); copiile manuale nu se șterg singure.
- **Descărcați** copiile periodic și păstrați-le și în altă parte (alt calculator, disc extern, cloud): dacă se strică discul
  serverului, copiile de pe el se pierd odată cu el.

Cum se salvează baza:
- **SQLite** — copia exactă a fișierului bazei;
- **PostgreSQL** — `pg_dump` (dacă programul PostgreSQL este instalat pe server);
- **altă bază** (MS SQL, MySQL, Oracle) — exportul universal al datelor, care se poate încărca într-o bază nouă de orice tip.

**Restaurarea** se face de administratorul serverului: SQLite — se înlocuiește fișierul bazei cu cel din arhivă;
PostgreSQL — `pg_restore`; exportul universal — într-o bază nouă, `manage.py migrate` apoi `manage.py loaddata data.json.gz`;
dosarul `media` din arhivă se copiază în `instance/media`. Apelați la furnizor dacă nu sunteți sigur.

## Actualizări
Versiunile noi vin de la furnizor ca **pachet semnat** (`crm-update-<versiune>.zip`):
1. **Încarcă pachetul de actualizare** — sistemul verifică semnătura și versiunea. Un fișier modificat, de altă proveniență
   sau o versiune mai veche nu se acceptă.
2. **Instalează și repornește** — se face o copie de rezervă, serverul se oprește, înlocuiește fișierele programului,
   instalează bibliotecile noi (dacă e cazul), aduce baza la zi și pornește din nou. Durează de obicei 1–3 minute;
   pagina se reîncarcă singură.
3. Dacă ceva nu merge, sistemul **revine singur** la versiunea anterioară (fișierele vechi se păstrează în
   `instance/updates/rollback/`).

Dacă furnizorul v-a dat o **adresă de actualizări**, scrieți-o aici: **Verifică versiunea nouă** arată dacă există una, iar
**Descarcă** o pregătește pentru instalare.

Dacă sistemul rulează în Docker, se actualizează cu imaginea nouă (`docker compose pull && docker compose up -d`).

Datele instituției (baza, configurația, fișierele încărcate) nu se ating la actualizare.

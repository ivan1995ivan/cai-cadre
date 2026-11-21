# Roluri și drepturi

Rolul spune **ce poate face** un utilizator și **ce vede**.

## Rolurile predefinite
Administrator, Șef resurse umane, Inspector resurse umane, Director / administrator, Șef de subdiviziune,
Contabilitate (salarizare), Angajat (cabinetul personal).
Le puteți modifica, dar nu le puteți șterge. Puteți crea și roluri noi (**Rol nou**): denumirea și un cod din litere mici
latine, cifre, _ și -.

Comutatorul **Administrator** dă rolului toate drepturile; matricea nu mai trebuie bifată.

## Drepturi pe module
Pentru fiecare modul (întreprinderea și statele de personal, clasificatoarele, angajații, contractele, ordinele, concediile,
certificatele medicale, timpul de muncă, formarea profesională, sănătatea și securitatea în muncă, evidența militară (doar
cu modulul pornit în Constante → Module), salarizarea, raportările
fiscale, rapoartele, cabinetul angajatului, importul, utilizatorii, rolurile, constantele, jurnalul de audit) se bifează
acțiunile: **Vizualizare, Creare, Editare, Ștergere, Aprobare / semnare, Export**. La angajați mai este
**Date sensibile (IDNP, acte, sănătate)**.
Bifa din dreptul numelui modulului le pune sau le scoate pe toate.

## „Ce înregistrări vede”
Pentru angajați, contracte, ordine, concedii, certificate medicale, timpul de muncă, formare, sănătate, salarizare și
rapoarte:
- **Doar ale mele (subdiviziunea mea / eu)**: doar subdiviziunile legate de utilizator și datele lui;
- **Subdiviziunile mele**: la fel, împreună cu subdiviziunile din subordinea lor;
- **Toate**: toată întreprinderea.

Rolul „Șef de subdiviziune” are de la instalare „Doar ale mele”.

## Meniul principal
Ce secțiuni și funcții din meniu vede rolul și, în grupa **Setări** de la sfârșit, ce setări vede în lista
[Administrare → Setări](help:settings). Debifat = nu apare în meniu sau în listă; drepturile din tabel rămân cum sunt.
Vedeți [Meniul principal](help:admin/main-menu).

## Câmpuri ascunse
Ce informații sensibile nu vede rolul: **salariul de funcție și sporurile**, **IDNP și actele de identitate**,
**datele de sănătate**, **telefonul, e-mailul și adresa angajatului**, **familia**.

> Dacă un utilizator are mai multe roluri, un câmp e ascuns doar dacă e ascuns în **toate** rolurile lui.

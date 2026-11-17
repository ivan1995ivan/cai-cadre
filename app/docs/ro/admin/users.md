# Utilizatori

Lista persoanelor care lucrează în sistem. Căutare după nume și filtru după rol.

## Adăugarea unui utilizator
1. Apăsați **Adaugă**.
2. Completați numele, prenumele, patronimicul, **utilizatorul** (cu el se intră în sistem) și **parola** (minimum 8
   caractere, nu doar cifre, nu o parolă banală).
3. Dacă e nevoie: e-mailul, telefonul, funcția și **limba** în care lucrează.
4. Alegeți unul sau mai multe **roluri**. Drepturile rolurilor se adună.
5. Bifați **„Schimbă parola la prima intrare”** dacă ați dat o parolă temporară.
6. **Salvează**.

La editare, câmpul **Parolă nouă** se lasă gol ca parola să rămână aceeași.

## Subdiviziunile utilizatorului (șeful de secție)
Câmpul **Subdiviziunile lui** leagă utilizatorul de secțiile pe care le conduce (șeful de secție, asistentul medical
superior). Rolurile cu vizibilitatea „doar ale mele” văd angajații, concediile, graficele, pontajul și rapoartele doar din
aceste subdiviziuni; cu „subdiviziunile mele” — și din sub-subdiviziunile lor. Fără subdiviziuni, un șef de secție nu vede
niciun angajat. Lista arată în coloana **Subdiviziunile lui** cine de ce secție răspunde.

## Contul pentru cabinetul angajatului
Angajații care intră doar în [Cabinetul meu](help:portal) primesc contul din fișa angajatului: butonul **Cabinet**
creează utilizatorul cu rolul „Angajat” și o parolă temporară. Conturi pentru toți angajații fără cont se fac dintr-o
dată din lista angajaților (**Conturi pentru cabinet**).

## Dezactivare în loc de ștergere
Când un angajat pleacă, **dezactivați-l** (comutatorul „Activ”). Istoria lui (documentele, jurnalul) rămâne legată de el.
Ștergerea e posibilă, dar nu se recomandă.

## Protecții
- Nu vă puteți dezactiva sau șterge propriul cont.
- Ultimul administrator activ nu poate pierde rolul de administrator.
- Numărul de utilizatori activi este limitat de licență.

## Parola administratorului uitată
Pe server, în dosarul programului (*C:\Program Files\CAI CADRE*), porniți **crm-admin.cmd** cu clic dreapta →
*Run as administrator* și scrieți parola nouă de două ori. Contul **admin** primește parola nouă, sau se creează dacă nu
există. Pentru alt utilizator: `crm-admin.cmd nume` din Command Prompt pornit ca administrator.

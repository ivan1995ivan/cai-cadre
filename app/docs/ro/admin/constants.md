# Constante (întreprinderea)

Datele de bază ale întreprinderii, folosite peste tot: în antetul și la semnăturile formelor de tipar, în ordine, în
declarațiile IPC21 / IALS21 și la intrare. Ce nu e completat nu apare pe forme.

## Întreprinderea
- **Denumirea și codurile:** denumirea (în română și, dacă limbile sunt pornite, în rusă și engleză) — scrisă fără forma
  juridică, de exemplu „Exemplu”; **forma juridică** (SRL, SA, ÎI …) se adaugă singură pe forme: „Exemplu” SRL. Dacă forma
  juridică e scrisă deja în denumire, nu se mai adaugă. **IDNO** (13 cifre) și **codul CAEM** al genului principal de
  activitate (patru cifre, de exemplu 6201; „62.01” se primește și se păstrează ca 6201) — intră în antetul formelor și în
  declarațiile IPC21 / IALS21 (în setările declarațiilor CAEM nu se mai scrie).
- **Adresa și contactele:** adresa juridică, adresa poștală, telefonul, e-mailul, site-ul.
- **Semnăturile de pe forme:** **conducătorul** (numele și funcția — Director, Director general, Administrator …),
  **contabilul-șef** și **responsabilul de personal** (numele și funcția fiecăruia, în română și, dacă e pornită, în rusă).
  Funcția necompletată se tipărește cu denumirea obișnuită (Director, Contabil-șef, Șef resurse umane); funcția scrisă doar
  în română apare și pe forma în rusă.

**Antetul formelor de tipar** (ordine, extrase, adeverințe, fișa personală, statele de personal, pontajul, graficele,
statele de calcul și de plată, lista pentru bancă, fișa anuală, rapoartele): logo-ul (dacă e încărcat), denumirea cu forma
juridică, apoi rândurile cu IDNO, CAEM și adresa; telefonul, e-mailul și site-ul; contul bancar implicit (IBAN, banca, BIC).

## Logo și ștampilă
Logo-ul principal (pe pagina de intrare, în meniu și în antetul formelor), logo-ul mic, varianta pentru tema întunecată,
semnătura și ștampila (pentru formele proprii: variabilele `company.signature`, `company.stamp`). Formate: PNG, JPG, SVG,
WEBP, cel mult 3 MB. Imaginile se pun direct în pagina tipărită. Logo-ul se poate opri pe o anumită formă, în
**Forme de tipar** → fila „Simplu” → „Cu logo-ul firmei”.

## Conturi bancare
Conturile (IBAN) întreprinderii; contul **implicit** apare în antetul formelor.

## Module
- **Modulul Salarizare** — livrarea „cu salariu” sau „fără salariu”. Oprit: calculul, plata și raportările IPC21 / IALS21
  dispar din meniu.
- **Panoul funcțiilor (ca în 1C)** — pornit: secțiunile meniului stau sus ca file, iar secțiunea deschide panoul ei —
  schema de lucru (documentele), registrele, clasificatoarele și rapoartele; meniul din stânga dispare. Oprit (implicit):
  meniul ca până acum. Detalii: [Panoul funcțiilor](help:panel).
- **Limbile sistemului** — bifați limbile în care se lucrează: **Română**, **Русский**, **English**, în orice combinație
  (de exemplu doar RO, RO + RU sau RO + EN). Doar limbile bifate apar în comutatorul de limbă din antet, la intrare și în
  profil; cu o singură limbă comutatorul dispare. Câmpurile „Denumire (RU)” / „(EN)” din clasificatoare, roluri, meniu și
  forme de tipar se ascund pentru limbile oprite. Utilizatorii care lucrau într-o limbă oprită trec pe prima limbă bifată.

## Tema
Tema implicită pentru toți și, opțional, culoarea principală a întreprinderii.

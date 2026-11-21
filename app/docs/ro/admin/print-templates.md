# Forme de tipar

Aici administratorul modifică aspectul documentelor tipărite: ordinul și extrasul din ordin, registrul ordinelor, statele
de personal, fișa personală (MR-2), adeverințele, lista angajaților, graficul concediilor, tabelul de pontaj, graficul
lunar de lucru, statele de calcul și de plată, fișa de calcul, lista pentru bancă, fișa anuală a veniturilor,
rapoartele.

## Cum se lucrează
1. Alegeți tipul documentului și șablonul.
2. Fila **Simplu**: mărimea scrisului, **Cu logo-ul firmei** și, la unele forme, **Textele formularului** (în RO și RU,
   gol = textul implicit). Logo-ul, ștampila și semnătura se încarcă în *Constante → Logo și ștampilă*.
3. Pentru schimbări mai mari: **HTML** (structura) și **CSS** (aspectul). În dreapta vedeți imediat
   **previzualizarea cu date reale**, în RO sau RU.
4. **Salvează**.

Tot sus: **Implicită** (forma propusă la tipar), **Activ**, orientarea (**Portret** / **Peisaj**).

## Antetul și semnăturile
Toate formele încep cu `{% company_header %}` — antetul întreprinderii din *Constante*: logo-ul, denumirea cu forma
juridică, IDNO, CAEM, adresa, telefonul, e-mailul, site-ul și contul bancar implicit (doar ce e completat). Semnăturile
de jos iau numele și funcțiile din *Constante → Semnăturile de pe forme* (conducătorul, contabilul-șef, responsabilul de
personal). În **Textele formularului** se pot pune, în acolade, datele întreprinderii: `{întreprinderea}`,
`{conducătorul}`, `{funcția_conducătorului}`, `{contabilul}`, `{funcția_contabilului}`, `{resurse_umane}`,
`{funcția_resurse_umane}` (lista completă e sub titlul „Textele formularului”). De exemplu, mențiunea „Aprob” din graficul
concediilor e implicit `APROB` / `{funcția_conducătorului} ______ {conducătorul}`.

## Variabile
Valorile se pun cu `{{ variabilă }}`, de ex. `{{ company.full_name }}`, `{{ company.director_position }}`,
`{{ emp.full_name }}`; lista datelor întreprinderii e în „Variabile disponibile”, sub editor.
Condiții: `{% if options.show_idnp %} ... {% endif %}`. Repetare: `{% for ... %} ... {% endfor %}`.
Formatare bani: `{{ valoare|money }}` → 1 234,50.

## Opțiuni
Bifele (de ex. cu fotografie, cu salariul, cu IDNP) sunt valorile **implicite** propuse la tipărire; utilizatorul le
poate schimba în dialogul de tipar.

## Siguranță
- **Restaurează originalul**: șabloanele livrate cu sistemul revin oricând la forma inițială.
- **Copie**: faceți o variantă proprie și păstrați originalul neatins.
- Șablonul primește doar datele documentului; nu poate citi parole sau alte date din sistem și nu poate rula scripturi.

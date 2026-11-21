# Setări

Toate setările programului sunt într-un singur loc: **Administrare → Setări**. În secțiunile meniului nu mai sunt setări,
doar registre și rapoarte.

## Găsirea setării
Pagina arată setările **în ordine alfabetică**. Scrieți în câmpul de căutare o parte din denumire: lista se strânge pe
măsură ce scrieți. Diacriticele și majusculele nu contează („campuri” găsește *Câmpuri obligatorii*, „localitati” —
*Localități*). Când a rămas o singură setare, **Enter** o deschide. Clic pe denumire deschide setarea într-o filă nouă din
bara de jos; în meniu rămâne evidențiat rândul **Setări**.

Fiecare vede doar setările la care are drept (de ex. clasificatoarele — dreptul *Clasificatoare*, tipurile de calcul —
*Setările salariului*). Cine nu are drept la nicio setare nu vede rândul **Setări** în meniu. Când întreprinderea lucrează fără
salarizare (*Constante → Module*), setările salarizării nu apar.

Administratorul poate ascunde setări anume pentru un rol: [Roluri și drepturi](help:admin/roles) → *Meniul principal*,
grupa **Setări** de la sfârșit. Setarea debifată nu apare în lista rolului; cu toate debifate nu apare nici rândul
**Setări** din meniu. Ca la funcțiile din meniu, bifa nu ia dreptul: drepturile rămân cele din tabelul rolului.

## Ce este în listă
- **Întreprinderea și programul**: Constante (datele întreprinderii, logo, conturi, module, tema), Valute, Bănci, Localități,
  Numerotare, Forme de tipar, Câmpuri obligatorii, Meniul principal, Utilizatori, Roluri și drepturi.
- **Clasificatoarele**, fiecare separat: Funcții (CORM), Specialități, Temeiuri legale, Tipuri de ordine, Categorii de
  calificare, Grade științifice, Titluri științifico-didactice, Nivelul studiilor, Forma de învățământ, Tipuri de acte,
  Gradul de rudenie, Starea familială, Naționalitatea, Motivele încetării CIM, Sancțiuni disciplinare, Tipuri de stimulare,
  Tipul angajării, Evidența militară (grupa, grade, centre militare), Lista de verificare la angajare / eliberare,
  Vaccinuri. Cum se lucrează cu ele — [Clasificatoare](help:dictionaries).
- **Timpul de muncă**: Grafice de lucru, Ture, Calendarul de producție, Odihna între ture și turele de noapte pe lună — vezi
  [Grafice de lucru și ture](help:worktime).
- **Concediile**: Evidența concediilor (data pornirii evidenței, perioadele care nu dau dreptul la concediu) — vezi
  [Concedii](help:leave).
- **Salarizarea**: Tipuri de calcul, Constantele salarizării, Raportări fiscale: datele plătitorului — vezi
  [Calculul salariului](help:payroll) și [Raportări](help:tax-reports).
- **Termene și alerte**: ce se urmărește și cu câte zile înainte; Poșta (e-mail) pentru notificări și fluturași — vezi
  [Termene și alerte](help:alerts).

## Adresele vechi
La actualizarea de la o versiune de dinainte de 1.4.0, favoritele, meniul principal salvat și bifele de meniu ale rolurilor
trec singure pe setările noi: rolul vede ce vedea înainte (cine nu vedea *Clasificatoarele* nu vede niciun clasificator,
cine nu vedea *Concediile* nu vede nici *Evidența concediilor*). Filele deschise și legăturile vechi (de ex.
*Clasificatoare → Alte clasificatoare*, fila *Setări* de la Concedii sau de la Termene și alerte) duc singure la setarea
nouă.

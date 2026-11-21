# Îndreptarea spre plată

**Îndreptarea spre plată** (meniul *Îndreptările spre plată*) e al doilea document al salariului, după calcul: **aici se
rețin CNAM 9 %, scutirea și impozitul pe venit 12 %.** Pe fiecare rând: **brutul** (venitul plătit), **scutirea**,
**CNAM**, **impozitul**, alte rețineri și **suma de plată**.

**Îndreptare nouă**: ce se plătește (avans sau salariu), baza, modalitatea (card și numerar, doar card, doar numerar) și
data. Din calculul aprobat se face direct cu butonul **„Îndreptare spre plată”**.
- **Salariul în baza calculului**: doar angajații calculului ales, cel mult suma lui; luna e a calculului.
- **Salariul pe sold**: fără calcul de bază — tot ce a rămas de plătit în lună, din toate calculele aprobate ale lunii.
- În ambele cazuri **brutul** e cel calculat minus ce s-a plătit deja în lună. **Impozitele se socotesc cumulat pe lună**:
  pe tot venitul plătit în lună până acum (avansul inclus) — CNAM din baza CNAM, scutirea lunii (1/12 din scutirea anuală
  din **cererea de scutire**: personală, majorată, soț / soție, întreținuți), impozitul din baza impozitului minus CNAM minus
  scutirea — și se reține **diferența** față de ce s-a reținut deja. Așa avansul și salariul împreună rețin exact impozitul
  lunii.
- **Avansul**: procentul din constante („Avansul”, implicit 40 %) × salariul de funcție × norma raportului de bază, rotunjit
  la leu — brut; din el se rețin CNAM 9 % și impozitul 12 % din rest (scutirea lunii se ia la salariu). Avansul nu se face
  în baza unui calcul.

**Forma**: sus titlul — *Îndreptarea spre plată nr. … din …* —, felul (salariu / avans), starea și legătura spre calculul
de bază (clic — se deschide calculul). În dreapta sus acțiunile; **✕** e ultimul și închide forma. În ciornă **antetul se
scrie de mână**: data, felul, calculul de bază (sau *pe sold*), luna (la *pe sold*), modalitatea, observațiile; **Salvează**
îl păstrează. Altă bază, alt fel, altă lună sau altă modalitate **completează rândurile din nou** (dacă sunt corectări de
mână, programul întreabă întâi). Dacă plecați din formă cu antetul nesalvat, programul întreabă **„Salvați
modificările?”** — *Da*, *Nu*, *Anulare*.

**Corectarea de mână** (în ciornă): scrieți **brutul** — impozitele se refac (la salariu în aceeași proporție, cu scutirea);
scrieți **suma de plată** — programul află brutul care dă exact acest net; scrieți **scutirea, CNAM sau impozitul** direct —
rămân cum sunt scrise și se reface doar suma de plată. Rândul corectat are semnul ✎. Cardul se alege pentru angajații care
au IBAN în dosar; ceilalți primesc numerar. Un rând se poate scoate, iar „Completează din nou” recalculează totul.

**Fluxul**: ciornă → **aprobat** → **achitat** (data și documentul de plată: ordinul de plată pentru bancă sau dispoziția de
casă). Redeschiderea o face cine are dreptul de aprobare la salarizare. Cât în baza unui calcul e o îndreptare aprobată
sau achitată, calculul nu se redeschide.

**Tipar și bancă**: **statul de plată** (cu coloana de semnătură pentru numerar și calculul de bază în antet), **lista
pentru bancă** (doar cardurile: numele, IDNP, IBAN, suma) și **fișierul pentru bancă** (CSV cu „;”: IBAN, numele, IDNP,
suma, destinația plății). Formatul exact cerut de bancă (MAIB, Victoriabank, Moldindconbank) se reglează la instalare.

**Fluturașii** (fișele de calcul), din îndreptarea pe salariu, pentru angajații ei: fiecare fluturaș are toată luna
angajatului — raporturile lui de muncă din calculele aprobate ale lunii (acumulările, reținerile), apoi decontarea: CNAM,
scutirea și impozitul, netul, avansul și salariul achitate, restul. **Fluturașii** tipărește toți fluturașii, iconița de pe
rând — al unui angajat; **Fluturașii în PDF** îi descarcă (fiecare angajat pe pagina lui). **Trimite fluturașii pe e-mail**
(din îndreptarea aprobată sau achitată) trimite fiecărui angajat o **arhivă ZIP cu fluturașul în PDF**; **parola arhivei
sunt ultimele 5 cifre ale codului fiscal (IDNP)**. Se trimite doar celor cu e-mail și IDNP în dosar; ceilalți apar cu
motivul. Trimiterea arată progresul și rezultatul fiecăruia, iar data ultimei trimiteri rămâne. Serverul de e-mail se pune
în Administrare → Setări → Poșta (e-mail). Arhiva se deschide fără programe în plus în Windows, macOS și pe telefon. Din
avans nu se fac fluturași. Angajatul își vede fluturașul fiecărei luni și în cabinetul lui.

**Datorii salariale** (a doua filă): la sfârșitul lunii alese, pe angajat, **înainte de impozit** — calculat (brutul
calculelor aprobate minus celelalte rețineri), achitat (brutul plătit, salariu și avans) și datoria. Negativ înseamnă
plătit în plus.

**Fișa personală anuală a veniturilor** (anexa nr. 8, forma din 2018) se tipărește din fișa angajatului → fila „Salariu”:
datele angajatorului și ale angajatului, scutirea din cerere, apoi **pe fiecare îndreptare achitată** — data, venitul
achitat (curent și cumulat), scutirea, primele CNAM, venitul impozabil, impozitul calculat și cel reținut (+/−).
Fără îndreptări achitate în an fișa nu are rânduri.

**IPC21, tabelul 1** și **IALS21** (venitul achitat, scutirile, impozitul și CNAM reținute) se fac din îndreptările
**achitate**, după data achitării (vezi *Raportări*).


**Luna în regimul IT Park**: pentru salariul din CIM nu se rețin CNAM și impozitul și nu se dă scutirea — de plată e brutul
minus celelalte rețineri; avansul se plătește întreg. Regimul e al **lunii calculului**, nu al datei plății (salariul lui
iunie plătit în iulie — după regimul lui iunie). Contractele de prestări servicii — cu reținerile obișnuite. Partea
impozitată final a fiecărei plăți se ține separat (pentru IPC21, IALS21, ISAPTI17). Vezi [Regimul IT Park](help:payroll/it-park).

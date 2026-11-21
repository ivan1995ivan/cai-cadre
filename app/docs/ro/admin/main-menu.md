# Meniul principal

Secțiunile meniului și, în fiecare, grupele **Registre** și **Rapoarte**, ca în 1C. Așezarea e una pentru toată
întreprinderea; cine ce vede se hotărăște la fiecare rol. Setările nu stau în secțiuni: toate sunt la
[Administrare → Setări](help:settings).

## Așezarea implicită
**Principal**, **Întreprinderea**, **Angajați**, **Ordine**, **Concedii și timp de muncă**, **Salarizare**,
**Formare și evidențe**, **Rapoarte**, **Administrare**. În fiecare secțiune:
- **Registre** — documentele secțiunii (angajații, ordinele, concediile, pontajul...);
- **Rapoarte** — rapoartele secțiunii, care se deschid direct (de ex. la Angajați: mișcarea cadrelor, vechimea, pensionările).

La **Administrare**: Setări, Cine e online, Importul din Excel, Jurnalul de audit, copiile de rezervă, ștergerea obiectelor
marcate, licența.

Aceeași funcție poate sta în mai multe locuri (MUNCA-1 — la Salarizare și la Rapoarte). Funcțiile noi, apărute în
program după ce ați salvat meniul, intră singure în grupa lor din secțiunea implicită.

Dacă întreprinderea lucrează fără salarizare (*Constante → Module*), funcțiile din **Salarizare** nu apar.

## Mutarea
În arbore trageți cu mouse-ul:
- o **funcție** în altă grupă sau secțiune (pusă pe grupă, devine prima în ea; pusă pe secțiune — prima la Registre)
  sau mai sus / mai jos între funcții; se mută doar din grupa de unde a fost luată, în celelalte locuri rămâne;
- o **secțiune** mai sus sau mai jos, între celelalte secțiuni.

## Funcții neafișate
La sfârșitul arborelui stau funcțiile care nu sunt nicăieri în meniu. Trageți-le într-o grupă ca să apară. O funcție trasă
la **Funcții neafișate** dispare din grupa din care a fost luată; ea rămâne în program (din favorite sau după adresă).

## Secțiunea
Clic pe o secțiune din arbore → în dreapta:
- denumirea în **RO** și **RU** (goală = denumirea standard; câmpul RU apare doar dacă limba rusă e pornită);
- iconița;
- **Șterge secțiunea** — doar secțiunea goală: mutați întâi funcțiile în alte secțiuni.

**Secțiune nouă** adaugă o secțiune la sfârșit; o redenumiți și trageți funcții în ea.

## Salvarea
**Salvează** (activ după o schimbare) păstrează meniul pentru toți. **Așezarea implicită** întoarce meniul standard.
Pagina se deschide doar pentru cine are dreptul de a modifica constantele și setările.

## Sus sau în stânga
**Așezarea meniului pentru toți**:
- **sus** — secțiunile sus, iar în stânga grupele secțiunii alese;
- **în stânga** — tot meniul în stânga, ca arbore: secțiunile se deschid cu un clic, cu grupele și funcțiile lor.

Fiecare utilizator își poate schimba așezarea din butonul cu paleta de culori (sus, dreapta).

Cu [Panoul funcțiilor](help:panel) pornit (*Constante → Module*) secțiunile stau sus ca file, fiecare cu panoul ei, iar
alegerea „sus / în stânga” nu se mai arată; așezarea secțiunilor și a funcțiilor de aici se păstrează.

## Ferestrele deschise
Bara de jos ține paginile deschise, ca în 1C. **Închide toate** le închide pe toate și rămâne doar Pagina de start.

## Cine ce vede
În [Roluri](help:admin/roles), la fiecare rol, blocul **Meniul principal**: bifele secțiunilor și funcțiilor. Debifat =
nu apare în meniu; drepturile rolului rămân cum sunt. Funcția din mai multe secțiuni se ascunde doar dacă e debifată
peste tot. Funcția apare doar dacă rolul are și dreptul de a o deschide (rapoartele evidenței militare — dreptul pe
evidența militară). Secțiunea fără nicio funcție vizibilă nu se arată, iar grupa goală nu apare în meniu.

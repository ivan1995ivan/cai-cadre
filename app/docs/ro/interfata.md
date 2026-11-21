# Aspectul programului: „Clasic de birou”

CAI CADRE arată implicit ca un **program clasic de birou**: o fereastră cu bara de titlu, bara de meniu, bara de unelte,
ferestrele deschise ca file și bara de stare jos. Ferestrele și panourile sunt gri deschis, câmpurile și tabelele albe cu
chenar subțire, rândurile tabelelor dese, cu linii de grilă, iar rândul ales se evidențiază albastru, ca în Windows.

## Ce e pe ecran, de sus în jos

1. **Bara de titlu**: *CAI CADRE — denumirea întreprinderii* (pe platforma cu mai multe baze — și numele bazei).
2. **Bara de meniu**:
   - **Fișier** — Pagina de start, Termene și alerte, Cabinetul meu, **Favorite** (și *Pune fereastra la favorite*),
     Profilul meu, **Tema**, **Limba**, Schimbă baza (pe platformă), **Ieșire**;
   - **secțiunile meniului principal** (Întreprinderea, Angajați, Ordine, Concedii și timp de muncă, Salarizare, Formare și
     evidențe, Rapoarte, Administrare): în fiecare — registrele, apoi rapoartele secțiunii și submeniul **Clasificatoare**.
     Se vede exact ce aveți în meniu: drepturile rolului, bifele din [Roluri → Meniul principal](help:admin/roles),
     modulele oprite în [Constante → Module](help:admin/constants) nu apar. Așezarea și denumirile secțiunilor sunt cele din
     [Meniul principal](help:admin/main-menu). Secțiunea paginii deschise e scrisă îngroșat;
   - **Ferestre** — lista ferestrelor deschise (`` Alt+` ``), *Închide fereastra* (Esc), *Închide toate*, Înapoi / Înainte
     și ferestrele deschise, numerotate;
   - **Ajutor** — instrucțiunea ecranului (F1) și *Despre program*.
3. **Bara de unelte** (iconițe mici; ținând mouse-ul pe una apare denumirea):

   | Buton | Ce face |
   |---|---|
   | ← → | Înapoi / Înainte (Alt+← / Alt+→) |
   | Casa | Pagina de start |
   | **Nou** | Butonul „nou” al ferestrei deschise: *Angajat nou*, *Ordin nou*, *Calcul nou*, *Adaugă* în clasificatoare |
   | **Salvează** (Ctrl+S) | Salvează forma deschisă, la fel ca butonul ei *Salvează* (sau *Da* la „Salvați modificările?”); activ doar cu modificări nesalvate |
   | **Tipar** | Butonul de tipar al ferestrei: dialogul de tipărire (lista angajaților, ordinul, pontajul, statul de calcul...) |
   | **Excel** | Salvează în Excel lista ferestrei (aceeași comandă ca iconița din colțul tabelului) |
   | **Reîmprospătează** | Cere din nou datele ferestrei de la server; cu modificări nesalvate — întâi salvați |
   | **Căutare** | Duce cursorul în câmpul de căutare al ferestrei |
   | **Ferestrele deschise** | Lista ferestrelor deschise (`` Alt+` ``) |
   | ? | Instrucțiunea ecranului (F1) |

   Butonul pe care fereastra deschisă nu-l are (de exemplu *Nou* în dosarul angajatului sau *Excel* într-o formă fără
   listă) e gri, iar indicația lui spune de ce.
4. **Ferestrele deschise ca file**: fiecare pagină deschisă rămâne o filă; ✕ pe filă (sau clic cu rotița mouse-ului) o
   închide, **Esc** închide fereastra activă. Cu modificări nesalvate programul întreabă întâi „Salvați modificările?”.
5. **Fereastra activă**.
6. **Bara de stare**: legătura cu serverul (*Conectat* / *Fără legătură cu serverul*, cu roșu), utilizatorul, rolul,
   unde vă aflați (secțiunea → ecranul), **clopoțelul** notificărilor cu numărul lor, **cine e online** (pentru cine vede
   utilizatorii) și versiunea programului.

## Meniul din tastatură

- **Alt** (apăsat și lăsat) alege bara de meniu: literele de acces se subliniază; **←/→** trec între meniuri,
  **↓** sau **Enter** deschide meniul.
- **Alt + litera subliniată** deschide direct meniul (de exemplu Alt+F — Fișier, Alt+O — Ordine).
- În meniu: **↑/↓** mută, **→** intră în submeniu (sau trece la meniul următor), **←** iese din submeniu, **Enter**
  alege, **Home / End** — primul / ultimul rând, o literă — rândul care începe cu ea.
- **Esc** închide submeniul, apoi meniul, apoi bara de meniu (abia după aceea Esc închide fereastra deschisă).

## Formele, tabelele, dialogurile

- În forme eticheta stă **în stânga câmpului**, pe o coloană de aceeași lățime; grupele de câmpuri au **chenar și
  titlu** (ca un *GroupBox*).
- Tabelele au grilă pe toate celulele, antetul gri și rânduri de ~24 px; rândul ales e albastru deschis.
- Ferestrele de dialog au **bara lor de titlu** cu ✕, iar butoanele **OK / Anulare** stau în dreapta jos.
- Fără colțuri rotunde, umbre mari și animații; butoanele sunt dreptunghiulare, cu relief discret (în
  [Profilul meu](help:profile) — *Plate (2D)* pentru butoane fără relief).

## Tema: cum se alege

- **Pentru toată întreprinderea**: [Administrare → Setări → Constante](help:admin/constants), fila *Tema* (și în
  asistentul de instalare). Tema implicită a instalărilor noi este **Clasic de birou**.
- **Pentru dvs.**: [Profilul meu](help:profile) → *Tema*, sau meniul **Fișier → Tema**. *Tema întreprinderii* — urmați
  alegerea din Constante.
- Teme:
  - **Clasic de birou** și **Clasic de birou, întunecat** — aspectul de mai sus;
  - **Verde prospețime**, **Turcoaz**, **Albastru**, **Întunecată**, **Ca în 1C (galben)** — aspectul cu meniul în
    stânga (secțiunile sus sau tot meniul în stânga) și bara ferestrelor deschise jos, ca până acum;
  - **Automat** — după setarea calculatorului: ziua tema întreprinderii, noaptea varianta ei întunecată (la *Clasic de
    birou* — *Clasic de birou, întunecat*).

## Panoul funcțiilor

Cu [Panoul funcțiilor](help:panel) pornit, secțiunile nu mai stau și ca rând de file sub antet (ar dubla bara de meniu):
primul rând din meniul fiecărei secțiuni este **Panoul funcțiilor**, care deschide panoul secțiunii (schema de lucru,
registrele, clasificatoarele, rapoartele).

## Pe telefon

Pe ecranul îngust bara de meniu se strânge în butonul **☰** din bara de unelte (secțiunile cu funcțiile lor,
favoritele, profilul, tema, limba, ajutorul, ieșirea). Bara de unelte păstrează butoanele de bază (Înapoi, Start, Nou,
Salvează, Tipar, Reîmprospătează, Ferestrele deschise), iar bara de stare — legătura, utilizatorul, notificările.

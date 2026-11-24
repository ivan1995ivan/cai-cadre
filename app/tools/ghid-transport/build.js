// Instrucțiunea pentru firma de transport (RO): de la angajat la salariu, cu capturile din copia de probă.
const fs = require('fs')
const {
  AlignmentType, BorderStyle, Document, Footer, Header, HeadingLevel, ImageRun, LevelFormat, Packer, PageBreak, PageNumber,
  Paragraph, ShadingType, Table, TableCell, TableRow, TextRun, WidthType,
} = require('docx')

const SHOTS = process.argv[2]
const OUT = process.argv[3]
const FONT = 'Arial'
const BLUE = '1F4E8C'
let fig = 0

// **gras** în text
function runs(text, extra = {}) {
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((part) => (part.startsWith('**')
    ? new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, ...extra })
    : new TextRun({ text: part, font: FONT, ...extra })))
}
const p = (text, opts = {}) => new Paragraph({ children: runs(text), spacing: { after: 120 }, ...opts })
const h1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font: FONT })], pageBreakBefore: true })
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: FONT })] })
const bullet = (text, level = 0) => new Paragraph({ children: runs(text), numbering: { reference: 'bullets', level }, spacing: { after: 60 } })
let listNo = 0
function steps(items) {
  listNo += 1
  const ref = `steps${listNo}`
  numberingConfigs.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 400, hanging: 300 } } } }] })
  return items.map((t) => new Paragraph({ children: runs(t), numbering: { reference: ref, level: 0 }, spacing: { after: 60 } }))
}
function img(name, caption, width = 620) {
  const png = fs.readFileSync(`${SHOTS}/${name}.png`)
  const w = png.readUInt32BE(16), h = png.readUInt32BE(20)
  fig += 1
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new ImageRun({ type: 'png', data: png, transformation: { width, height: Math.round(width * h / w) },
        altText: { title: caption, description: caption, name } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: `Figura ${fig}. ${caption}`, italics: true, size: 18, color: '555555', font: FONT })] }),
  ]
}
function note(text, color = 'EAF2FB', border = '4A86C5') {
  return new Paragraph({ children: runs(text), spacing: { before: 120, after: 160 },
    shading: { type: ShadingType.CLEAR, color: 'auto', fill: color },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: border, space: 8 } }, indent: { left: 120, right: 120 } })
}
const warn = (text) => note(text, 'FFF4E5', 'E08A1E')
const TABLE_W = 9026
function table(head, rows, widths) {
  const mk = (cells, bold, fill) => new TableRow({ tableHeader: bold, cantSplit: true, children: cells.map((c, i) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined,
    children: [new Paragraph({ children: runs(c, { size: 19, ...(bold ? { bold: true } : {}) }) })] })) })
  return new Table({ width: { size: TABLE_W, type: WidthType.DXA }, columnWidths: widths,
    rows: [mk(head, true, 'D9E5F3'), ...rows.map((r) => mk(r, false))] })
}
const spacer = () => new Paragraph({ children: [], spacing: { after: 80 } })

const numberingConfigs = [{ reference: 'bullets', levels: [
  { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 260 } } } },
  { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 800, hanging: 260 } } } },
] }]

const body = []
const add = (...xs) => xs.flat().forEach((x) => body.push(x))

// --- coperta -----------------------------------------------------------------------------------------------------------
add(
  new Paragraph({ spacing: { before: 2200, after: 200 }, children: [new TextRun({ text: 'CAI CADRE', font: FONT, size: 28, color: '6B7A90', bold: true })] }),
  new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: 'Transportul: de la angajat la salariu', font: FONT, size: 56, bold: true, color: BLUE })] }),
  new Paragraph({ spacing: { after: 600 }, children: [new TextRun({ text: 'Instrucțiune pas cu pas pentru firma de transport', font: FONT, size: 30, color: '333333' })] }),
  p('Pentru cine: **cadrele** (angajarea, actele șoferilor), **dispecerul / șeful coloanei** (cursele, tahograful), **contabilul** (constantele, diurna, salariul) și **administratorul programului** (pornirea modulului, setările).'),
  p('Ce găsiți aici: cum se pregătește programul o singură dată, cum se angajează șoferul și i se țin actele, cum se scrie foaia de parcurs cu țările, cum se socotesc plata pe km și diurna după HG nr. 10/2012, cum se încarcă fișierele tahografului și cum ajunge totul în calculul salariului.'),
  note('Capturile sunt făcute pe datele demonstrative „Demo Producție” SRL (șoferul Gheorghiță Radu, cursa Chișinău – München și înapoi, noiembrie 2026). La dvs. numele, sumele și datele vor fi altele.'),
  p('Video-ul cu aceiași pași și instrucțiunea din program: meniul **Ajutor** (tasta **F1**) pe ecranul Curse → Transportul.'),
)

// --- cuprins -----------------------------------------------------------------------------------------------------------
add(h1('Cuprins și drumul pe scurt'),
  p('Drumul de la angajat la salariu, în ordinea în care se face:'),
  ...steps([
    '**Pregătirea (o singură dată)** — pornirea modulului, constantele, cursul BNM, vehiculele, tarifele pe km, țările și diurnele, utilizatorii (partea 1).',
    '**Angajatul** — fișa, ordinul de angajare, raportul de muncă, actele șoferului cu termenele lor (partea 2).',
    '**Cursa** — foaia de parcurs, țările parcurse, plata pe km și diurna, aprobarea, tiparul, importul din Excel (partea 3).',
    '**Tahograful** — descărcările cardului, zilele șoferului, încălcările, timpii în foaia de parcurs (partea 4).',
    '**Salariul** — pontajul, calculul lunii cu KM și DIURNA, plata (partea 5).',
    '**Alertele și ajutorul** — termenele, întrebări frecvente, lista lunară de verificare (partea 6).',
  ]),
  spacer(),
  table(['Cine', 'Ce face în program'], [
    ['Administratorul', 'Pornește modulul, face utilizatorii și rolurile, setările (vehicule, tarife, țări).'],
    ['Cadrele (resurse umane)', 'Angajează prin ordin, ține fișa și actele șoferului, urmărește termenele.'],
    ['Dispecerul / șeful coloanei', 'Scrie cursele șoferilor săi, încarcă fișierele de pe cardul tahografului, vede încălcările.'],
    ['Contabilul', 'Constantele diurnei, cursul BNM, aprobarea curselor, calculul salariului și plata.'],
    ['Directorul', 'Vede cursele și le aprobă (după drepturile date).'],
  ], [2600, 6426]),
)

// --- 1. pregătirea -------------------------------------------------------------------------------------------------------
add(h1('Partea 1. Pregătirea programului (o singură dată)'),
  h2('1.1. Pornirea modulului „Transportul”'),
  ...steps([
    'Meniul **Administrare → Setări → Constante (întreprinderea)**, fila **Module**.',
    'Bifați **„Modulul Transportul (cursele, diurnele, plata pe km)”** și apăsați **Salvează**.',
    'Reîncărcați pagina (F5): apar **Salarizare → Curse (foi de parcurs)**, **Salarizare → Tahograful** și în setări **Vehiculele**, **Tarife pe km**, **Țările și diurnele**.',
  ]),
  img('01-modules', 'Constante → Module: modulul Transportul'),
  note('Modulul face parte din livrarea cu salariu. Oprit, meniurile transportului nu apar și nimeni nu are drepturile lui.'),

  h2('1.2. Constantele salarizării (ce se plătește și cât)'),
  p('Meniul **Administrare → Setări → Constantele salarizării**. Fiecare constantă are **codul**, **valoarea**, **„În vigoare din”** și **temeiul**. Pentru transport contează:'),
  table(['Codul', 'Valoarea livrată', 'Ce înseamnă'], [
    ['per_diem_pct', '100 %', 'Cât din norma diurnei plătește întreprinderea. Peste 100 % — partea în plus e venit impozabil (DIURNAEX).'],
    ['per_diem_private_min_pct', '70 %', 'Minimul pentru firmele private (HG 10/2012 pct. 22¹). Sub el cursa nu se aprobă.'],
    ['per_diem_short_pct', '20 %', 'Șoferul a stat peste hotare până la 8 ore (pct. 31 lit. a).'],
    ['per_diem_day_pct', '40 %', 'Peste hotare 8–24 de ore fără întrerupere (pct. 31 lit. b).'],
    ['per_diem_meals_pct', '20 %', 'Masa asigurată de beneficiar, peste 8 ore în ziua aceea (pct. 33).'],
    ['per_diem_domestic_pay', '0', 'Diurna la cursele în țară: 0 — nu se plătește (munca pe drum nu e deplasare, pct. 3); 1 — 250 lei pe zi, doar la cursele de mai multe zile.'],
    ['min_salary', '6 300 lei', 'Salariul minim: plata pe km intră în comparația cu el (completarea până la minim).'],
  ], [2300, 1500, 5226]),
  spacer(),
  img('02-constants', 'Constantele salarizării: rândurile diurnei (per_diem_…)'),
  h2('Cum se schimbă o constantă'),
  ...steps([
    'Nu modificați rândul vechi: apăsați **Adaugă**.',
    'Alegeți același **cod**, scrieți **valoarea nouă**, data **„În vigoare din”** și **temeiul** (ordinul, regulamentul de salarizare).',
    'Salvați. Lunile și cursele de dinainte de dată rămân cu valoarea veche; cele de după — cu cea nouă.',
  ]),
  note('Exemplu: întreprinderea hotărăște să plătească diurna la 80 % din normă începând cu 1 ianuarie 2027 — rând nou: per_diem_pct = 80, în vigoare din 01.01.2027, temeiul „Ordinul nr. … din …”. Procentul unei singure curse se poate scrie și direct pe cursă („Diurna, % din normă”).'),

  h2('1.3. Cursul BNM'),
  p('Diurna e în valută (EUR, USD); în lei se socotește la **cursul oficial BNM din ziua dinaintea plecării** (pct. 41). Meniul **Administrare → Setări → Valute, cursuri, TVA**: butonul de preluare a cursului BNM aduce cursurile zilelor. Fără cursul zilei, cursa nu se aprobă (programul spune ce lipsește).'),
  img('03-currencies', 'Valutele și cursurile BNM'),

  h2('1.4. Vehiculele'),
  p('Meniul **Administrare → Setări → Vehiculele** → **Adaugă**: numărul de înmatriculare, felul (cap tractor, camion, semiremorcă / remorcă, autobuz, microbuz, autoutilitară, autoturism), marca, modelul, categoria permisului cerută, **tahograful** (atunci se cere cardul șoferului), consumul normat, coloana / subdiviziunea. Remorca se trece ca vehicul separat, cu felul „Semiremorcă / remorcă”.'),
  img('04-vehicles', 'Vehiculele și remorcile firmei'),
  note('Un vehicul cu curse nu se șterge — se debifează „Activ”.'),

  h2('1.5. Tarifele pe km'),
  p('Meniul **Administrare → Setări → Tarife pe km** → **Adaugă**: tariful în lei / km, **„În vigoare din”**, iar pentru cine se aplică — felul cursei (marfă / pasageri), aria (în țară / internațional), felul vehiculului. Gol = oricare.'),
  p('La o cursă programul ia rândul în vigoare la data plecării cu **cele mai multe potriviri exacte**: „marfă + internațional + cap tractor” bate „internațional”, care bate „oricare”. Exemplul din figură: 1,20 lei/km în general și 1,50 lei/km pentru marfă internațional cu cap tractor.'),
  img('05-kmrates', 'Tarifele pe km'),
  p('Tariful nou: rând nou cu data lui. Cursele vechi rămân cu tariful vechi; cursele aprobate își păstrează tariful fixat la aprobare.'),

  h2('1.6. Țările și normele diurnei'),
  p('Meniul **Administrare → Setări → Țările și diurnele**: 186 de țări cu normele pe zi din anexa nr. 2 la HG nr. 10/2012 (redacția HG 1058/2023), categoria I, în valuta lor. Butonul **„Normele diurnei”** arată istoria normelor unei țări; o normă nouă — rând nou cu data ei.'),
  img('06-countries', 'Țările și diurnele'),
  img('07-norms', 'Istoria normelor unei țări'),
  warn('Verificați normele țărilor în care mergeți cu textul în vigoare al HG nr. 10/2012. Federația Rusă are norme separate pe orașe (Moscova, Sankt Petersburg — 70 EUR); programul are doar norma generală (65 EUR).'),

  h2('1.7. Utilizatorii și drepturile'),
  p('Meniul **Administrare → Utilizatori** și **Roluri**. Drepturile transportului se numesc „Transportul: cursele, diurnele, plata pe km”: vizualizare, creare, editare, ștergere, aprobare, export, cu filtrul „doar subdiviziunea mea”. Rolurile livrate:'),
  bullet('**contabilitatea** — tot;'),
  bullet('**directorul** — vizualizare și aprobare;'),
  bullet('**șeful de subdiviziune** (de ex. șeful coloanei auto) — cursele și tahograful doar pentru șoferii subdiviziunii lui, fără aprobare;'),
  bullet('**cadrele** — vizualizare.'),
)

// --- 2. angajatul --------------------------------------------------------------------------------------------------------
add(h1('Partea 2. Angajatul: fișa, ordinul, actele'),
  h2('2.1. Fișa angajatului'),
  p('Meniul **Angajați → Angajații** → angajatul (sau **Adaugă** pentru unul nou). Fila **Date personale**: numele, prenumele, IDNP, **data nașterii** (după ea programul recunoaște și cardul de tahograf), telefonul, adresa, IBAN-ul cardului salarial.'),
  img('08-employee', 'Fișa angajatului'),

  h2('2.2. Ordinul de angajare'),
  p('Angajarea, transferul, concediile și eliberarea se fac **prin ordin**. Meniul **Ordine → Ordine** → **Ordin nou**:'),
  ...steps([
    'Tipul ordinului **„Angajare”**, data, angajatul.',
    'În punctul ordinului: subdiviziunea (de ex. „Transportul”), funcția (**Conducător de autocamion** — cod CORM 833202), norma, salariul de funcție, data angajării, perioada de probă, felul contractului.',
    'Salvați, verificați textul ordinului, **Semnați**. Semnat, ordinul creează singur **raportul de muncă** al angajatului.',
    'Tipăriți ordinul și contractul individual de muncă (butonul **Tipar**).',
  ]),
  img('12-order', 'Ordin nou: tipul „Angajare”'),
  img('11-orders', 'Lista ordinelor'),

  h2('2.3. Raportul de muncă'),
  p('Fila **Raporturi de muncă** din fișa angajatului arată ce a pus ordinul: funcția, subdiviziunea, salariul de funcție, modalitatea de remunerare și istoria lor. Plata pe km și diurna nu se scriu aici — vin singure din cursele aprobate.'),
  img('10-jobs', 'Raportul de muncă al șoferului'),

  h2('2.4. Actele șoferului'),
  p('Fila **Acte** → **Adaugă**: tipul actului, seria, numărul, cine l-a eliberat, data eliberării și **„Valabil până la”**. Pentru șofer:'),
  table(['Actul', 'Când se cere', 'Termenul obișnuit'], [
    ['Permis de conducere', 'la orice cursă', 'după permis'],
    ['Certificat medical', 'la orice cursă', 'de regulă 2 ani (de verificat)'],
    ['Certificat de competență profesională (CPC)', 'la orice cursă', '5 ani'],
    ['Cardul de conducător auto pentru tahograf', 'vehiculul are tahograf', '5 ani; numărul exact de pe card (16 caractere)'],
    ['Certificatul ADR', 'cursa cu mărfuri periculoase', '5 ani'],
  ], [3400, 2800, 2826]),
  spacer(),
  img('09-documents', 'Actele șoferului cu termenele'),
  note('Actul care lipsește sau expiră până la întoarcerea din cursă apare în foaia de parcurs ca **avertisment** (nu oprește aprobarea). Alerta „Expiră actul” anunță din timp (implicit cu 30 de zile).'),
)

// --- 3. cursa ------------------------------------------------------------------------------------------------------------
add(h1('Partea 3. Cursa (foaia de parcurs)'),
  h2('3.1. Lista curselor'),
  p('Meniul **Salarizare → Curse (foi de parcurs)**. Lista arată cursele cu **întoarcerea** în luna aleasă, cu starea (ciornă / aprobată), șoferul, vehiculul, țările, km, plata pe km și diurna; jos — totalul curselor aprobate.'),
  img('13-trips', 'Cursele lunii'),

  h2('3.2. Cursa nouă'),
  p('Butonul **„Cursă nouă”** (seria **FP**). Se completează:'),
  bullet('**Șoferul** și, la nevoie, **al doilea șofer** — raportul lor de muncă activ la data plecării;'),
  bullet('**Vehiculul** (cap tractor, camion, autobuz) și **remorca**;'),
  bullet('**Felul** (marfă / pasageri) și **aria** (în țară / internațional);'),
  bullet('**Plecarea** și **întoarcerea** — data și ora. Cursa intră în salariul **lunii întoarcerii**;'),
  bullet('**Kilometrajul** la plecare și la întoarcere — km se socotesc singuri; sau km de mână;'),
  bullet('ruta, ADR (mărfuri periculoase), masa asigurată pe toată cursa, observațiile;'),
  bullet('**Diurna, % din normă** — gol înseamnă procentul întreprinderii din Constante.'),
  img('14-trip-new', 'Foaia de parcurs nouă'),

  h2('3.3. Țările parcurse'),
  p('La cursa internațională — **câte un rând pe fiecare țară străină**, în ordinea parcursului: țara, **intrarea** și **ieșirea** (ora trecerii frontierei, după documente), **încărcare** / **descărcare** acolo, **masa asigurată** acolo. Butonul **„Adaugă țara”** pune intrarea noii țări la ieșirea din cea de dinainte. Timpul din afara rândurilor e în Republica Moldova.'),
  img('16-trip-legs', 'Țările parcurse cu ora trecerii frontierei'),
  note('Dacă vehiculul are tahograf „smart 2” și cardul șoferului a fost încărcat (partea 4), butonul **„Țările din tahograf”** completează rândurile singur, din trecerile frontierei înregistrate pe card. Verificați-le și salvați.'),

  h2('3.4. Salvarea: plata pe km și diurna'),
  p('La **Salvează** programul socotește: km × tariful pe km (explicația sus, de ex. „3840 km × 1,5 lei/km = 5760 lei”) și **diurna pe zile** pentru fiecare șofer: țara zilei, orele, procentul, norma, cursul BNM, suma în lei și partea peste normă.'),
  img('15-trip', 'Cursa aprobată'),
  img('17-trip-diem', 'Plata pe km și diurna pe zile, cu explicația fiecărui rând'),
  p('Regulile diurnei (Regulamentul aprobat prin HG nr. 10/2012):'),
  table(['Situația', 'Cât se plătește'], [
    ['Peste hotare până la 8 ore', '20 % din norma țării, o dată (pct. 31 lit. a)'],
    ['Peste hotare 8–24 de ore fără întrerupere', '40 % din normă, o dată (pct. 31 lit. b)'],
    ['Peste 24 de ore', '100 % pe fiecare zi, de la ziua plecării până la ziua sosirii (pct. 31 lit. c, pct. 24)'],
    ['Trecerea dintr-o țară în alta în aceeași zi', 'norma țării de destinație (pct. 26)'],
    ['Tranzit (fără încărcare / descărcare) sub 24 de ore', 'norma țării de destinație a cursei (pct. 23)'],
    ['Masa asigurată, peste 8 ore în ziua aceea', '20 % din normă (pct. 33)'],
    ['Procentul întreprinderii', 'peste toate de mai sus; cel puțin 70 % în privat (pct. 22¹)'],
    ['Cursa în țară', 'fără diurnă; cu per_diem_domestic_pay = 1 — 250 lei pe zi, doar la cursele de mai multe zile'],
  ], [4200, 4826]),
  spacer(),
  h2('3.5. Problemele, avertismentele, aprobarea'),
  bullet('**„De corectat înainte de aprobare”** (galben): întoarcerea înaintea plecării, cursa fără km, remorca pe locul vehiculului, alt drum al aceluiași șofer în aceeași perioadă, concediul / boala șoferului în timpul cursei, lipsa tarifului, a normei sau a cursului BNM, procentul diurnei sub minim.'),
  bullet('**„Actele șoferilor”** (albastru): actele lipsă sau expirate, lipsa descărcărilor de pe card, încălcările timpului de conducere. Nu opresc aprobarea.'),
  bullet('**Aprobă** (dreptul de aprobare): verifică totul încă o dată și **fixează** tariful, cursurile și diurna. Cursa intră în salariul lunii întoarcerii.'),
  bullet('**Anulează aprobarea**: cursa revine la ciornă, doar cât calculul salariului pe luna aceea nu e aprobat. După aprobare / anulare — **recalculați** luna (partea 5).'),

  h2('3.6. Importul curselor din Excel'),
  p('Butonul **„Curse din Excel”**: descărcați șablonul, completați câte un rând pe fiecare țară străină a cursei; rândurile cu același **„Nr. cursei”** fac o cursă. Primul rând al cursei are șoferul (nr. de tabel), vehiculul, plecarea, întoarcerea, km. Ora — „zz.ll.aaaa hh:mm”. Întâi **Verifică** (arată rândurile greșite), apoi **Importă**: cursele noi sunt ciorne deja socotite, se aprobă din ecran.'),
  img('18-trip-import', 'Importul curselor din Excel'),

  h2('3.7. Tiparul foii de parcurs'),
  p('Butonul **Tipar** din cursă: foaia de parcurs cu șoferii, vehiculul, kilometrajul și plata pe km, țările cu ora frontierei, calculul diurnei pe zile și semnăturile (șoferul, dispecerul, contabilul-șef). Forma se poate schimba în **Administrare → Setări → Șabloane de tipar → Foaia de parcurs**.'),
  img('19-print', 'Foaia de parcurs tipărită'),
)

// --- 4. tahograful -------------------------------------------------------------------------------------------------------
add(h1('Partea 4. Tahograful'),
  h2('4.1. Încărcarea fișierelor de pe cardul șoferului'),
  ...steps([
    'Descărcați cardul șoferului cu cititorul de carduri și programul lui (fișierul **.ddd**, de ex. C_…ddd). Programul amintește descărcarea la 28 de zile de la cea de dinainte.',
    'Meniul **Salarizare → Tahograful**, fila **Descărcările cardului** → **„Încarcă fișierele .ddd”**; se pot alege mai multe fișiere deodată.',
    'Fiecare fișier se citește și se leagă singur de șofer: după **numărul cardului** din acte, altfel după nume și data nașterii (atunci cardul se adaugă în acte).',
    'Dacă șoferul nu se găsește, rândul e „nelegat” — butonul cu omulețul: **„Leagă de angajat”**.',
  ]),
  img('20-tacho-upload', 'Fișierul de pe card, citit și legat de șofer'),
  note('Fișierul original se păstrează în program (butonul de descărcare din rând), pentru control. Același fișier încărcat a doua oară e recunoscut. Descărcarea vehiculului (V_…ddd) sau cardul de atelier se resping, cu motivul.'),

  h2('4.2. Zilele șoferului'),
  p('Fila **Zilele șoferului**: alegeți șoferul și luna. Pe fiecare zi — bara celor 24 de ore (roșu — conducerea, albastru — altă muncă, galben — disponibilitatea, verde — odihna, gri — fără card), totalurile, km, țările, vehiculul și numărul încălcărilor (rândul se deschide cu „+”).'),
  img('21-tacho-days', 'Zilele șoferului cu activitățile de pe card'),

  h2('4.3. Încălcările limitelor'),
  p('Fila **Încălcările lunii** arată, pentru toți șoferii pe care îi vedeți, ce limite au fost depășite (Codul transporturilor rutiere nr. 150/2014; Acordul AETR art. 6–8):'),
  table(['Regula', 'Limita'], [
    ['Conducerea continuă', 'după 4 h 30 min — pauză de 45 min (sau 15 min, apoi 30 min)'],
    ['Conducerea zilnică', '9 h; de cel mult două ori pe săptămână 10 h'],
    ['Conducerea săptămânală', '56 h; în două săptămâni la rând — 90 h'],
    ['Odihna zilnică', '11 h în 24 de ore (sau 3 h + 9 h); redusă 9 h de cel mult 3 ori între odihnele săptămânale; în echipaj — 9 h în 30 de ore'],
    ['Odihna săptămânală', 'cel târziu după 6 × 24 h; normală 45 h, redusă 24 h; reducerea se compensează până la sfârșitul săptămânii a treia'],
  ], [3000, 6026]),
  spacer(),
  img('22-tacho-findings', 'Încălcările lunii'),
  warn('Timpul fără card în tahograf programul îl socotește odihnă — conducerea fără card nu se vede de pe card. Pontajul nu se schimbă din tahograf: el rămâne după graficul de lucru / de mână.'),

  h2('4.4. Tahograful în foaia de parcurs'),
  p('În cursă, secțiunea **„Tahograful în timpul cursei”** arată timpii fiecărui șofer de pe card (conducere, altă muncă, disponibilitate, odihnă), dacă descărcările acoperă toată cursa și încălcările din timpul ei.'),
  img('23-trip-tacho', 'Timpii de pe card în timpul cursei'),
)

// --- 5. salariul ---------------------------------------------------------------------------------------------------------
add(h1('Partea 5. Salariul'),
  h2('5.1. Pontajul'),
  p('Salariul de funcție, orele de noapte, suplimentarele și sărbătorile se socotesc ca la toți angajații, din **pontaj**: meniul **Concedii și timp de muncă → Tabele de pontaj** — se completează din graficul de lucru, se corectează și se închide la sfârșitul lunii.'),
  img('24-timesheets', 'Tabelele de pontaj'),

  h2('5.2. Calculul salariului'),
  ...steps([
    'Aprobați toate cursele cu întoarcerea în lună (partea 3).',
    'Meniul **Salarizare → Calculul salariului** → calculul lunii (nou sau existent) → **Recalculează**.',
    'Deschideți rândul șoferului cu „+”: salariul de funcție, **Plata pe km (transport)** — KM, **Diurna (în limita normelor)** — DIURNA, și după caz **Diurna peste norme** — DIURNAEX, cu explicația fiecărui rând.',
    'Verificați, apoi **Verificat** și **Aprobă**. După aprobarea calculului cursele lunii nu se mai pot anula.',
  ]),
  img('25-payroll', 'Calculul salariului pe lună'),
  img('26-payroll-line', 'Rândul șoferului: salariul, KM și DIURNA'),
  table(['Rândul', 'Impozit / CAS / CNAM', 'Altele'], [
    ['KM — plata pe km', 'impozabilă, cu CAS și CNAM', 'intră în medie și în comparația cu salariul minim (dacă salariul + KM e sub minim, se completează)'],
    ['DIURNA — în limita normelor', 'neimpozabilă, fără CAS și CNAM', 'nu intră în medie'],
    ['DIURNAEX — peste norme', 'impozabilă', 'apare doar când procentul întreprinderii e peste 100 %'],
  ], [2600, 2800, 3626]),
  spacer(),
  h2('5.3. Plata'),
  p('Din calculul aprobat: **Salarizare → Îndreptările spre plată** — aici se rețin impozitul pe venit și CNAM, se tipăresc fluturașii și se face fișierul pentru bancă. Raportările (IPC21 și celelalte) se fac din **Rapoarte**.'),
)

// --- 6. alertele, ajutorul, verificarea ------------------------------------------------------------------------------------
add(h1('Partea 6. Alertele, ajutorul, lista lunară'),
  h2('6.1. Termene și alerte'),
  p('Meniul **Termene și alerte** (și clopoțelul de sus): actele care expiră (permis, CPC, medical, card, ADR), **cardul de tahograf de descărcat** (la 28 de zile de la ultima descărcare) și **încălcările** timpului de conducere din ultimele 14 zile. Ce se urmărește și cu câte zile înainte — **Administrare → Setări → Termene și alerte: ce se urmărește**.'),
  img('27-alerts', 'Termene și alerte'),
  h2('6.2. Ajutorul din program'),
  p('Pe orice ecran tasta **F1** (sau „?” sus în dreapta) deschide instrucțiunea ecranului. Pe ecranele transportului sunt și legăturile spre acest document și spre video.'),
  img('28-help', 'Ajutorul (F1) pe ecranul curselor'),
  h2('6.3. Lista de verificare a lunii'),
  ...steps([
    'Cursul BNM este preluat pentru zilele plecărilor.',
    'Toate cursele lunii sunt scrise, cu țările și orele frontierei; problemele galbene sunt corectate.',
    'Fișierele de pe cardurile șoferilor sunt încărcate; încălcările sunt văzute și discutate cu șoferii.',
    'Cursele cu întoarcerea în lună sunt **aprobate**.',
    'Pontajul lunii este închis.',
    'Calculul salariului este **recalculat**, verificat (KM, DIURNA) și aprobat.',
    'Îndreptarea spre plată și raportările sunt făcute.',
  ]),
  h2('6.4. Întrebări frecvente'),
  p('**Cursa începe în octombrie și se termină în noiembrie — în ce lună intră?** În luna întoarcerii (noiembrie).'),
  p('**Am greșit o oră la frontieră într-o cursă aprobată.** Anulați aprobarea (cât calculul lunii nu e aprobat), corectați, salvați, aprobați din nou și recalculați luna.'),
  p('**Am schimbat tariful pe km.** Rând nou cu data lui în Tarife pe km. Cursele deja aprobate rămân cu tariful vechi.'),
  p('**Diurna nu se socotește: „lipsește cursul BNM”.** Preluați cursul pentru ziua dinaintea plecării (partea 1.3) și salvați cursa din nou.'),
  p('**Fișierul de tahograf e „nelegat”.** Scrieți în actele șoferului cardul cu numărul exact de pe card sau legați fișierul de mână („Leagă de angajat”).'),
  h2('6.5. De stabilit cu contabilitatea'),
  bullet('dacă minimul de 70 % se aplică și peste 20 % / 40 % (programul îl aplică);'),
  bullet('cursul BNM la avansul în valută (programul ia ziua dinaintea plecării);'),
  bullet('normele Federației Ruse pe orașe;'),
  bullet('regimul fiscal al diurnei în limita / peste norme — după textul în vigoare al Codului fiscal.'),
)

const doc = new Document({
  creator: 'CAI CADRE', title: 'Transportul: de la angajat la salariu', description: 'Instrucțiune pentru firma de transport',
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 32, bold: true, color: BLUE }, paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 25, bold: true, color: '2E5C99' }, paragraph: { spacing: { before: 280, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: numberingConfigs },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: 'CAI CADRE — Transportul: de la angajat la salariu', size: 16, color: '888888', font: FONT })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: ['Pagina ', PageNumber.CURRENT, ' din ', PageNumber.TOTAL_PAGES], size: 16, color: '888888', font: FONT })] })] }) },
    children: body,
  }],
})
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log('ok', buf.length, 'figuri', fig) })

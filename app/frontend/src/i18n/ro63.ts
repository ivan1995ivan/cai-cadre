// S6b (pasul b): tahograful — descărcările cardului de conducător (.ddd), zilele cu activitățile, încălcările limitelor.
export default {
  menu: { tachograph: 'Tahograful' },
  al: { kinds: { tacho_download: 'Descărcarea cardului de tahograf (la 28 de zile)', tacho_infringement: 'Încălcări ale timpului de conducere / odihnă' } },
  tr: {
    tacho: {
      files: 'Descărcările cardului', days: 'Zilele șoferului', findings: 'Încălcările lunii',
      upload: 'Încarcă fișierele .ddd', uploadHint: 'Fișierele descărcate de pe cardul de conducător (generația 1 și 2, „smart”); se pot alege mai multe deodată. Originalul se păstrează pentru control.',
      allFiles: 'Toate descărcările', unmatched: 'Fără angajat', uploaded: 'Fișiere noi citite: {{n}}',
      status: { created: 'citit', duplicate: 'era deja', error: 'eroare' },
      downloaded: 'Descărcat', holder: 'Titularul cardului', card: 'Cardul', expiry: 'Valabil până la', period: 'Perioada', daysCount: 'Zile',
      employee: 'Angajatul', byName: 'după nume', noEmployee: 'nelegat — alegeți angajatul', assign: 'Leagă de angajat',
      assignHint: 'Cardul nu s-a găsit în dosare (actul „Cardul de conducător auto pentru tahograf”) și nici după nume și data nașterii. Alegeți angajatul — zilele lui se refac.',
      original: 'Fișierul original', removeConfirm: 'Ștergeți descărcarea? Zilele șoferului se refac din celelalte descărcări.',
      driver: 'Șoferul', daysHint: 'Ora Moldovei. Pe bară: conducerea (pe toată înălțimea), altă muncă, disponibilitatea, odihna, fără card. Limitele se verifică pe ora UTC a tahografului, cu săptămâna de luni 00:00 până duminică 24:00.',
      foundN: 'Încălcări: {{n}}', day: 'Ziua', timeline: '00:00 – 24:00', noData: 'nu sunt date de pe card',
      sum: { driving: 'Conducere', work: 'Altă muncă', availability: 'Disponibil', rest: 'Odihnă', unknown: 'Fără card' },
      km: 'Km', countries: 'Țările', vehicles: 'Vehiculele',
      findingsHint: 'Constatările din datele de pe card pentru șoferii pe care îi vedeți: încălcările (roșu) și ce e de urmărit (galben — compensarea odihnei reduse).',
      from: 'De la', to: 'Până la', rule: 'Regula', what: 'Ce s-a găsit', level: { error: 'încălcare', info: 'de urmărit' },
      act: { D: 'conducere', W: 'altă muncă', A: 'disponibilitate', R: 'pauză / odihnă', U: 'fără card' },
      inTrip: 'Tahograful în timpul cursei', noFiles: 'nu sunt descărcări ale cardului', partial: 'descărcările nu acoperă toată cursa',
      openDays: 'zilele șoferului', legs: 'Țările din tahograf', legsConfirm: 'Înlocuiți țările cursei cu cele din trecerile frontierei de pe cardul șoferului (tahograful „smart 2”)?',
      legsDone: 'Țări puse din tahograf: {{n}} — verificați și salvați.',
    },
  },
}

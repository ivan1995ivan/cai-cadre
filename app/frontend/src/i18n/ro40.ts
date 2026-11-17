// CAI CADRE — Etapa 6, partea 1: formarea (EMC), atestarea, planul anual de formare.
export default {
  al: { kinds: { credits_missing: 'Credite EMC insuficiente înainte de atestare' } },
  tr: {
    tabs: { records: 'Registrul EMC', credits: 'Creditele', attestation: 'Atestarea', plans: 'Planul anual' },
    kind: 'Tipul', title: 'Cursul / activitatea', provider: 'Organizatorul', hours: 'Ore', credits: 'Credite', certificate: 'Certificatul',
    certificateDate: 'Data certificatului', order: 'Ordinul', searchHint: 'Nume, curs, organizator', periodFrom: 'Perioada de la',
    expiry: 'Expiră la', missing: 'Lipsesc', statusAll: 'Toate situațiile', norms: 'Normele de credite',
    summary: '{{people}} persoane · {{hours}} ore · {{credits}} credite',
    kinds: {
      course: 'Curs de perfecționare', thematic: 'Curs tematic / de specializare', conference: 'Conferință / congres',
      seminar: 'Seminar / atelier', internship: 'Stagiu', online: 'Curs online', publication: 'Publicație / prezentare', other: 'Altă activitate',
    },
    status: { risk: 'Risc: atestarea fără credite', behind: 'În urmă', ok: 'În grafic', done: 'Acumulate' },
    rec: { new: 'Activitate nouă' },
    creditsHint: 'Creditele se numără de la data conferirii categoriei actuale (sau pe ultimii ani ai perioadei, dacă nu are categorie). „În urmă” — mai puține decât cere perioada scursă; „Risc” — categoria expiră curând, iar creditele nu ajung.',
    normsHint: 'Câte credite EMC se cer pe perioada de atestare, pe categorii de personal — după regulamentul EMFC în vigoare.',
    periodYears: 'Perioada de atestare (ani)', warnMonths: 'Avertizare cu (luni) înainte',
    cardTitle: 'Educația medicală continuă (EMC)', cardCredits: '{{credits}} din {{required}} credite din {{from}}', cardExpiry: 'categoria expiră la {{date}}',
    att: {
      dueTitle: 'Calendarul atestării — categoriile care expiră', months: 'Luni înainte', session: 'Data comisiei',
      include: 'Include în lista pentru atestare ({{count}})', added: 'Adăugați în listă: {{count}}', inList: 'în listă',
      listTitle: 'Lista pentru atestare', open: 'Deschise', all: 'Toate', printList: 'Lista candidaților (tipar)',
      makeOrder: 'Ordinul de conferire ({{count}})', orderMade: 'Ordinul a fost creat — verificați-l și semnați-l.',
      current: 'Categoria actuală', requested: 'Categoria solicitată', statusCol: 'Starea', result: 'Rezultatul',
      submitted: 'Dosarul depus la', decision: 'Decizia comisiei (nr.)', resultCategory: 'Categoria obținută', resultDate: 'Data deciziei',
      locked: 'Ordinul {{order}} este făcut — rezultatul nu se mai schimbă.',
      st: { planned: 'Planificat', submitted: 'Dosarul depus', awarded: 'Categorie conferită', confirmed: 'Categorie confirmată',
        refused: 'Respins', postponed: 'Amânat' },
    },
    plan: {
      choose: 'Alegeți anul', new: 'Plan nou', fill: 'Completează din credite', approve: 'Aprobă', reopen: 'Întoarce în ciornă',
      filled: 'Rânduri adăugate: {{count}}', stats: '{{lines}} rânduri · realizate {{done}} · {{credits}} credite', course: 'Cursul / tematica',
      month: 'Luna', done: 'Realizat', st: { draft: 'Ciornă', approved: 'Aprobat' },
    },
  },
}

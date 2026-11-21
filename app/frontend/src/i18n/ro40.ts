// CAI CADRE — formarea profesională: registrul cursurilor / instruirilor și planul anual de formare.
export default {
  al: { kinds: { training_expiry: 'Expirarea certificatului de formare' } },
  tr: {
    tabs: { records: 'Registrul formării', plans: 'Planul anual' },
    kind: 'Tipul', title: 'Cursul / activitatea', provider: 'Organizatorul', hours: 'Ore', certificate: 'Certificatul',
    certificateDate: 'Data certificatului', validUntil: 'Valabil până la',
    validUntilHint: 'Doar la certificatele cu termen (de ex. lucrul la înălțime, stivuitorul): aproape de expirare apare alerta.',
    order: 'Ordinul', searchHint: 'Nume, curs, organizator',
    summary: '{{people}} persoane · {{hours}} ore',
    kinds: {
      course: 'Curs de perfecționare', thematic: 'Curs de specializare / calificare', internal: 'Instruire internă', conference: 'Conferință',
      seminar: 'Seminar / atelier', internship: 'Stagiu', online: 'Curs online', other: 'Altă activitate',
    },
    rec: { new: 'Activitate nouă' },
    cardTitle: 'Formarea profesională (cursuri, instruiri, certificate)',
    plan: {
      choose: 'Alegeți anul', new: 'Plan nou', fill: 'Completează din certificatele care expiră',
      fillHint: 'Câte un rând pentru fiecare certificat care expiră în anul planului (reînnoirea lui), în luna expirării.',
      approve: 'Aprobă', reopen: 'Întoarce în ciornă',
      filled: 'Rânduri adăugate: {{count}}', stats: '{{lines}} rânduri · realizate {{done}} · {{hours}} ore', course: 'Cursul / tematica',
      month: 'Luna', done: 'Realizat', st: { draft: 'Ciornă', approved: 'Aprobat' },
    },
  },
}

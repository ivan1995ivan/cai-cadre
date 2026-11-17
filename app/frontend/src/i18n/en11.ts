// CAI CADRE — Stage 6, part 1: training (CME), attestation, annual training plan.
export default {
  al: { kinds: { credits_missing: 'Insufficient CME credits before attestation' } },
  tr: {
    tabs: { records: 'CME register', credits: 'Credits', attestation: 'Attestation', plans: 'Annual plan' },
    kind: 'Type', title: 'Course / activity', provider: 'Provider', hours: 'Hours', credits: 'Credits', certificate: 'Certificate',
    certificateDate: 'Certificate date', order: 'Order', searchHint: 'Name, course, provider', periodFrom: 'Period from',
    expiry: 'Expires', missing: 'Missing', statusAll: 'All statuses', norms: 'Credit norms',
    summary: '{{people}} people · {{hours}} hours · {{credits}} credits',
    kinds: {
      course: 'Training course', thematic: 'Thematic / specialisation course', conference: 'Conference / congress', seminar: 'Seminar / workshop',
      internship: 'Internship', online: 'Online course', publication: 'Publication / talk', other: 'Other activity',
    },
    status: { risk: 'At risk', behind: 'Behind', ok: 'On track', done: 'Done' },
    rec: { new: 'New activity' },
    creditsHint: 'Credits are counted from the date the current category was awarded. "Behind" — fewer than the elapsed period requires; "At risk" — the category expires soon without enough credits.',
    normsHint: 'CME credits required per attestation period, by staff category.',
    periodYears: 'Attestation period (years)', warnMonths: 'Warn (months) before',
    cardTitle: 'Continuing medical education (CME)', cardCredits: '{{credits}} of {{required}} credits since {{from}}', cardExpiry: 'category expires {{date}}',
    att: {
      dueTitle: 'Attestation calendar — expiring categories', months: 'Months ahead', session: 'Commission date',
      include: 'Add to attestation list ({{count}})', added: 'Added: {{count}}', inList: 'in list',
      listTitle: 'Attestation list', open: 'Open', all: 'All', printList: 'Candidate list (print)',
      makeOrder: 'Award order ({{count}})', orderMade: 'The order was created — check and sign it.',
      current: 'Current category', requested: 'Requested category', statusCol: 'Status', result: 'Result',
      submitted: 'Submitted on', decision: 'Commission decision (no.)', resultCategory: 'Category obtained', resultDate: 'Decision date',
      locked: 'Order {{order}} exists — the result can no longer change.',
      st: { planned: 'Planned', submitted: 'Submitted', awarded: 'Awarded', confirmed: 'Confirmed', refused: 'Refused', postponed: 'Postponed' },
    },
    plan: {
      choose: 'Choose the year', new: 'New plan', fill: 'Fill from credits', approve: 'Approve', reopen: 'Back to draft',
      filled: 'Rows added: {{count}}', stats: '{{lines}} rows · done {{done}} · {{credits}} credits', course: 'Course / topic',
      month: 'Month', done: 'Done', st: { draft: 'Draft', approved: 'Approved' },
    },
  },
}

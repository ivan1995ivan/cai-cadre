// CAI CADRE — staff training: the register of courses / trainings and the annual training plan.
export default {
  al: { kinds: { training_expiry: 'Training certificate expiry' } },
  tr: {
    tabs: { records: 'Training register', plans: 'Annual plan' },
    kind: 'Type', title: 'Course / activity', provider: 'Provider', hours: 'Hours', certificate: 'Certificate',
    certificateDate: 'Certificate date', validUntil: 'Valid until',
    validUntilHint: 'Only for certificates with a term (work at height, forklift, etc.): an alert appears before it expires.',
    order: 'Order', searchHint: 'Name, course, provider',
    summary: '{{people}} people · {{hours}} hours',
    kinds: {
      course: 'Training course', thematic: 'Specialisation / qualification course', internal: 'In-house training', conference: 'Conference',
      seminar: 'Seminar / workshop', internship: 'Internship', online: 'Online course', other: 'Other activity',
    },
    rec: { new: 'New activity' },
    cardTitle: 'Training (courses, in-house trainings, certificates)',
    plan: {
      choose: 'Choose the year', new: 'New plan', fill: 'Fill from expiring certificates',
      fillHint: 'One row for each certificate expiring in the plan year (its renewal), in the month it expires.',
      approve: 'Approve', reopen: 'Back to draft',
      filled: 'Rows added: {{count}}', stats: '{{lines}} rows · done {{done}} · {{hours}} hours', course: 'Course / topic',
      month: 'Month', done: 'Done', st: { draft: 'Draft', approved: 'Approved' },
    },
  },
}

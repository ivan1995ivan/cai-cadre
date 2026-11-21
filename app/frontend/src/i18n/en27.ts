// S2: 2026 payroll figures and rules — exemption request with dependants, minimum wage, minimum CAS base.
export default {
  pay: {
    ex: {
      hint: 'Fiscal Code, art. 33–35: personal exemption (P) or increased (M), for the spouse (Sm — only a spouse in the art. 33(2) categories who does not use their own exemption; “S” abolished since 2021), for dependants (N; H — disabled since childhood, severe or pronounced disability). The request is not renewed yearly: it applies from the month after it is filed until a new request (any change — within 10 days). Monthly: annual amount / 12, at most the month’s income.',
      dateFrom: 'Applies from',
    },
    ex2: {
      number: 'Registration no.', dateTo: 'Valid until', dateFromHint: 'Empty — from the month after filing.',
      dateToHint: 'Empty — until a new request (a new request closes the old one by itself).',
      majorCategory: 'Increased exemption category (M)', majorHint: 'Fiscal Code, art. 33(2): the category letter.', majorDocument: 'Document for M',
      category: 'art. 33(2) letter {{c}})', spouseMajor: 'Spouse exemption (Sm)',
      spouseMajorHint: 'Only if the spouse falls in the art. 33(2) categories and does not use their own exemption (FC art. 34(2)).',
      spouseName: 'Spouse (full name)', spouseCategory: 'Spouse category', spouseDocument: 'Spouse document',
      waiver: 'Waiver of P / M — request date', waiverHint: 'Annual income over 360 000 lei: P / M stop from the month after the request; past months are not recalculated.',
      needsReview: 'To be checked', codeNow: 'Code this month',
      fromFamily: 'From “Family”', birthDate: 'Date of birth', rightFrom: 'Right from', rightTo: 'Right until',
      document: 'Document (birth certificate...)', incomeOk: 'Income ≤ 12 400 lei / year',
      dependentsHint: 'The exemption for a person applies from the month after the right arises (FC art. 35(4)). Brother / sister — only with a disability.',
      rel: { child: 'Child', parent: 'Parent', sibling: 'Brother / sister', other: 'Other person' },
      dis: { none: 'No disability (N)', childhood: 'Since childhood (H)', severe: 'Severe (H)', accentuated: 'Pronounced (H)', medium: 'Medium (N)' },
    },
    type: { autos: { sick_accident: 'Work accident: employer days', min_wage: 'Top-up to the minimum wage', cas_min: 'CAS on the gap to the minimum base' } },
    const: { check: 'to be checked' },
  },
  wt: { ts: { overtimeSplit: 'Overtime: {{first}} h (first 2 hours / day) + {{next}} h (following); holidays / rest days: {{inNorm}} h within the norm + {{over}} h over the norm' } },
  al: { kinds: { min_wage: 'Salary below the minimum wage', exemption_limit: 'Income close to the exemption limit (360 000 lei)' } },
}

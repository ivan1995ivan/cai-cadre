// CAI CADRE — electronic XML returns (IPC21, IALS21, IRM19) following the State Tax Service schemas.
export default {
  pay: { ex: { spouseIdnp: 'Spouse IDNP', spouseIdnpHint: 'For IALS21 (col. 4), with the spouse exemption (Sm).' } },
  tax: {
    exportXml: 'XML return (SFS)', xmlHint: 'The XML file following the official schema, for upload to the State Tax Service (e-Cabinet / e-returns).',
    headerMissing: 'Header data missing: {{list}} — fill them in Administration → Settings → Tax reports: payer details (and IDNO in Constants).',
    missingCode: '{{count}} people without a position code (CORM) — fill it in Administration → Settings → Positions (CORM); it is mandatory in IPC21.',
    table1: 'Table 1 — salary payments (code 11, SAL)', table2: 'Table 2 — nominal record of insured persons',
    period: 'Period', occupationCode: 'Position code', spouseIdnp: 'Spouse IDNP',
    irmCategory: 'Category', irmCode: 'Relation code', irmReason: 'Reason',
    dependents: 'Dependents in the annex: {{count}}.',
    cols: { base: 'Social insurance base', sick: 'Sick pay', P: 'P', M: 'M', Sm: 'Sm', N: 'N', H: 'H' },
    ipcHint: 'Monthly return (by the 25th of the next month) from approved calculations: table 1 (SAL), annex by CUATM, table 2 by person and category — 101 employment contract, 123 external second job, 105 civil contract, 160 annual leave, 15311 employer-paid sick leave, 157 / 158 / 159 / 165 unpaid and social leave; row 1.1 b) 24% rate (healthcare institutions).',
    ialsHint: 'Annual information note (by 25 January): the year’s income, exemptions by code P / M / Sm / N / H (from the requests), health insurance and tax; control sum = total tax; annex with dependents.',
    irmHint: 'Entries from signed orders: col. 8 — 01 indefinite hiring, 05 fixed-term, 02 termination (col. 9 reason: 113–116), 03 suspension, 04 resumption; cols 5–7 — 157 / 158 childcare, 165 paternity leave. Filed within 10 working days (overdue in red).',
    set: {
      hint: 'Header data of the electronic returns. Name, IDNO, director and chief accountant come from Constants.',
      cnas_code: 'CNAS code (of the payer)', cnasHint: 'Registration code assigned by CNAS (up to 7 digits).',
      sfs_code: 'State Tax Service code', sfsHint: 'The SFS office serving you (2 characters).',
      cuatm: 'Locality code (CUATM)', cuatmHint: 'Code of the head office (4 characters) per the CUATM classifier.',
      caem: 'Main activity code (CAEM)', caemHint: 'Four-digit code; usually 8610 for hospitals.',
      email: 'Contact e-mail', phone: 'Contact phone', income_source: 'Income source code',
    },
  },
}

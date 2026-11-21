// CAI CADRE — Stage 8: administration texts without CRM leftovers; user's departments.
export default {
  users: {
    subdivisions: 'Departments',
    subdivisionsHint: 'For unit heads: roles with "own / my departments" see employees, leave, rosters and reports only of these departments (including sub-departments for "my departments").',
  },
  roles: { hiddenFieldsHint: 'Which sensitive data this role does not see (e.g. salary or health data for unit heads).' },
  localities: {
    loadHint: 'Tick the countries whose localities you use and press "Load". Unticked = the country\'s localities are removed from the list (manually added ones stay). Addresses in personal files do not change.',
  },
  requiredFields: {
    hint: 'Tick which fields must be filled in the personal file, documents and education. Checked on save: a record with an empty ticked field is not saved.',
  },
}

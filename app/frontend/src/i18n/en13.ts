// CAI CADRE — system languages, e-mail-only notifications, classifier picker ("…").
export default {
  constants: {
    languages: 'System languages', languagesMin: 'Tick at least one language.',
    languagesHint: 'Only the ticked languages appear in the language switcher, at login and in the profile; RU / EN name fields are hidden for disabled languages. Users of a disabled language move to the first ticked one.',
  },
  profile: {
    emailTitle: 'E-mail notifications', emailOn: 'The digest of new deadlines is sent to {{email}} (when e-mail is on in Deadlines and alerts).',
    emailOff: 'Add your e-mail address to the profile to receive the digest of new deadlines.',
  },
  picker: {
    search: 'Search', choose: 'Choose', open: 'Open the classifier', title: 'Choose from the classifier',
    hint: 'Double-click or "Choose" puts the item in the field; add a new item with "Add".',
  },
}

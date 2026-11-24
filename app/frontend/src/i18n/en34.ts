// S6b (step b): the tachograph — driver card downloads (.ddd), days with activities, infringements of the limits.
export default {
  menu: { tachograph: 'Tachograph' },
  al: { kinds: { tacho_download: 'Driver card download (every 28 days)', tacho_infringement: 'Driving / rest time infringements' } },
  tr: {
    tacho: {
      files: 'Card downloads', days: 'Driver days', findings: 'Infringements of the month',
      upload: 'Upload .ddd files', uploadHint: 'Files downloaded from the driver card (generation 1 and 2, “smart”); several at once. The original is kept for inspection.',
      allFiles: 'All downloads', unmatched: 'Without employee', uploaded: 'New files read: {{n}}',
      status: { created: 'read', duplicate: 'already there', error: 'error' },
      downloaded: 'Downloaded', holder: 'Card holder', card: 'Card', expiry: 'Valid until', period: 'Period', daysCount: 'Days',
      employee: 'Employee', byName: 'by name', noEmployee: 'not linked — choose the employee', assign: 'Link to employee',
      assignHint: 'The card was not found in the files (document “Driver tachograph card”) nor by name and birth date. Choose the employee — their days are rebuilt.',
      original: 'Original file', removeConfirm: 'Delete the download? The driver’s days are rebuilt from the other downloads.',
      driver: 'Driver', daysHint: 'Moldova time. On the bar: driving (full height), other work, availability, rest, no card. Limits are checked on the tachograph’s UTC time, the week from Monday 00:00 to Sunday 24:00.',
      foundN: 'Infringements: {{n}}', day: 'Day', timeline: '00:00 – 24:00', noData: 'no card data',
      sum: { driving: 'Driving', work: 'Other work', availability: 'Available', rest: 'Rest', unknown: 'No card' },
      km: 'Km', countries: 'Countries', vehicles: 'Vehicles',
      findingsHint: 'Findings from the card data for the drivers you see: infringements (red) and what to follow (yellow — compensation of a reduced rest).',
      from: 'From', to: 'To', rule: 'Rule', what: 'What was found', level: { error: 'infringement', info: 'to follow' },
      act: { D: 'driving', W: 'other work', A: 'availability', R: 'break / rest', U: 'no card' },
      inTrip: 'Tachograph during the trip', noFiles: 'no card downloads', partial: 'the downloads do not cover the whole trip',
      openDays: 'driver days', legs: 'Countries from the tachograph', legsConfirm: 'Replace the trip countries with the border crossings from the driver card (“smart 2” tachograph)?',
      legsDone: 'Countries from the tachograph: {{n}} — check and save.',
    },
  },
}

// CAI CADRE — Stage 5: deadlines and alerts, notifications, home dashboard.
export default {
  menu: { alerts: 'Deadlines and alerts' },
  dashboard: {
    title: 'Home', welcome: 'Hello, {{name}}!', travel: 'On a trip / training today', alertsMonth: 'Deadlines within 30 days',
    leaveRequests: 'New leave requests', ordersDraft: 'Unsigned orders', unacknowledged: 'Orders not acknowledged',
    units: 'Staff list', approved: 'Approved units', occupied: 'Occupied', nearest: 'Nearest deadlines',
    allAlerts: 'All ({{count}})', noAlerts: 'No upcoming deadlines.', birthdays: 'Birthdays (7 days)',
  },
  al: {
    tabs: { list: 'To do', settings: 'Settings', email: 'E-mail' },
    today: 'today', ago_one: '{{count}} day ago', ago_other: '{{count}} days ago', in_one: 'in {{count}} day', in_other: 'in {{count}} days',
    allKinds: 'All kinds', listHint: 'The list is built every day; double-click opens the record or document.',
    due: 'Due', kind: 'Kind', what: 'What to do', enabled: 'On', days: 'Days before', audience: 'Recipients',
    settingsHint: 'How many days before the deadline the alert appears. Notifications (in-app and e-mail) are sent at night, once per deadline.',
    retMen: 'Retirement age — men', retWomen: 'Retirement age — women',
    emailDigest: 'E-mail digest', emailDigestHint: 'Send an e-mail with new alerts to users who have an address',
    runNow: 'Send notifications now', sent: 'Notifications sent: {{count}}, e-mails: {{emails}}.',
    aud: { hr: 'HR', accounting: 'Accounting', head: 'Head of unit' },
    kinds: {
      probation_end: 'End of probation', contract_end: 'Fixed-term contract expiry', document_expiry: 'ID document expiry',
      childcare_end: 'End of childcare leave',
      maternity_end: 'End of maternity leave', leave_unused: 'Unused leave (art. 118 LC)', sanction_expiry: 'Disciplinary sanction expiry',
      retirement: 'Reaching retirement age', birthday: 'Birthdays and jubilees',
      order_unacknowledged: 'Order not acknowledged', payroll_orders: 'Orders for accounting', leave_requests: 'Leave requests to review',
      next_month_leave: 'Next month leave', roster_missing: 'Next month roster missing', irm19_due: 'IRM19 deadline',
    },
    smtp: {
      hint: 'The company mail server used to send notifications. The password is stored encrypted.',
      enabled: 'E-mail sending is on', host: 'SMTP server', port: 'Port', username: 'User', password: 'Password',
      from: 'Sender address', testTo: 'Test address', test: 'Send test', testOk: 'Test sent to {{to}}.',
    },
  },
}

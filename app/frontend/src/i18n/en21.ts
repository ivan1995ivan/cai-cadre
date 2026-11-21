// CAI CADRE 1.3.0: marking for deletion (as in 1C) and deleting marked objects in Administration.
export default {
  menu: { markedObjects: 'Delete marked objects' },
  marks: {
    models: { core_Locality: 'Locality', core_Bank: 'Bank', org_Occupation: 'Position (CORM)',
      org_Specialty: 'Specialty', org_DictItem: 'Classifier item', org_LegalBasis: 'Legal basis',
      org_OrderType: 'Order type', org_Subdivision: 'Subdivision', org_StaffList: 'Staff list',
      staff_Employee: 'Employee', leave_LeaveSchedule: 'Leave schedule', leave_LeaveRequest: 'Leave request',
      leave_SickLeave: 'Sick leave certificate', orders_Order: 'Order', worktime_ShiftType: 'Shift',
      worktime_WorkSchedule: 'Work schedule', worktime_Roster: 'Duty roster', worktime_Timesheet: 'Timesheet',
      payroll_PayType: 'Pay type', payroll_Payroll: 'Payroll', payroll_Payment: 'Salary payment',
      training_TrainingRecord: 'Training activity', training_TrainingPlan: 'Annual training plan',
      health_MedicalExam: 'Medical exam',
      health_SafetyBriefing: 'Safety briefing' },
    mark: 'Mark for deletion', unmark: 'Remove deletion mark', short: 'marked for deletion',
    markConfirm: 'Mark for deletion? It is deleted for good only from Administration, if nothing uses it.',
    unmarkConfirm: 'Remove the deletion mark?',
    banner: 'Marked for deletion: it can no longer be changed. Deleted for good in Administration → Delete marked objects.',
    hint: 'All objects marked for deletion. "Check references" shows where they are still used; "Delete" removes for good only '
      + 'those nothing refers to (objects chosen together are deleted in the right order); the others stay marked, with their '
      + 'references. With nothing ticked, the whole list is taken. Make a backup first.',
    allTypes: 'All types', refresh: 'Refresh', check: 'Check references',
    deleteAll: 'Delete unused', deleteSelected: 'Delete ticked (unused)',
    deleteConfirm: 'Delete the unused objects for good ({{count}} chosen)? This cannot be undone.',
    unmarkSelected: 'Remove mark', unmarkSelectedConfirm: 'Remove the mark from {{count}} objects?',
    unmarked: 'Mark removed: {{count}}', deleted: 'Deleted for good: {{count}}', checked: 'Unused: {{free}}, used: {{used}}',
    empty: 'No objects are marked for deletion.',
    type: 'Type', object: 'Object', refs: 'Where it is used', free: 'unused — can be deleted', used: 'used ({{count}})',
  },
}

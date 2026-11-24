// S6b (step a): transport — vehicles, rates per km, countries with per diem norms, trips (waybills).
export default {
  menu: { trips: 'Trips (waybills)', vehicles: 'Vehicles', kmRates: 'Rates per km', countries: 'Countries and per diems' },
  desk: { tab: { trip: 'Trip {{number}}' } },
  constants: {
    transport_enabled: 'Transport module (trips, per diems, pay per km)',
    transport_enabledHint: 'For carriers (goods, passengers; domestic and international): vehicles, trips with the countries crossed, drivers’ per diems by country and pay per km, which go into payroll. Off — the transport menu, settings and API are hidden.',
  },
  pay: { type: { autos: { trip_km: 'Transport: pay per km (approved trips)', per_diem: 'Transport: per diem within the norms', per_diem_excess: 'Transport: per diem above the norms (taxable)' } } },
  tr: {
    any: 'any',
    status: { draft: 'Draft', approved: 'Approved' },
    kinds: { goods: 'Goods', passengers: 'Passengers' },
    scopes: { domestic: 'Domestic', international: 'International' },
    vehicleKinds: { tractor: 'Tractor unit', truck: 'Truck', trailer: 'Semi-trailer / trailer', bus: 'Bus', minibus: 'Minibus', van: 'Van', car: 'Car', other: 'Other' },
    veh: {
      plate: 'Plate number', kind: 'Kind', brand: 'Make', model: 'Model', category: 'Category', tachograph: 'Tachograph',
      fuelNorm: 'Fuel, l/100 km', subdivision: 'Fleet / department',
      hint: 'The company’s vehicles and trailers: plate, kind, required licence category, tachograph (needs the driver card). The trailer is chosen separately in the trip.',
    },
    rate: {
      dateFrom: 'In force from', rate: 'Rate, lei/km', document: 'Basis (collective agreement, pay regulation)',
      hint: 'The driver’s rate per km from the given date. Empty trip kind / scope / vehicle = any; a trip takes the best-matching row in force on departure. Pay per km counts towards the minimum wage (RTC art. 142: distance-based pay only with the minimum wage guaranteed).',
    },
    country: {
      code: 'Code', current: 'Per diem now', noNorm: 'no norm', norms: 'Per diem norms', dateFrom: 'In force from', amount: 'Daily norm',
      currency: 'Currency', document: 'Basis', checkTag: 'to check',
      hint: 'Countries crossed on trips and daily per diem norms (GD 10/2012), with history. Delivered norms must be checked against the text in force; a new norm — a new row from its date.',
      normsHint: 'Daily norm in the country’s currency from the given date; a trip uses the norm in force on that day. Amount in lei — at the NBM rate.',
    },
    trip: {
      title: 'Waybill', new: 'New trip', import: 'Trips from Excel',
      importHint: 'One row per foreign country of the trip; rows with the same “Trip no.” make one trip (draft). Time: dd.mm.yyyy hh:mm — border crossing time.',
      hint: 'An approved trip goes into the payroll of the return month: pay per km and the drivers’ per diems.',
      driver: 'Driver', coDriver: 'Second driver', vehicle: 'Vehicle', trailer: 'Trailer', kind: 'Trip kind', scope: 'Scope',
      departure: 'Departure', arrival: 'Return', arrivalHint: 'The trip goes into the payroll of the return month.',
      odometerOut: 'Odometer at departure', odometerIn: 'Odometer at return', km: 'Km', kmHint: 'With the odometer — counted automatically.',
      perDiemPct: 'Per diem, % of norm', perDiemPctHint: 'Empty — the percent from Constants.', route: 'Route', adr: 'Dangerous goods (ADR)',
      meals: 'Meals provided', mealsHint: 'For the whole trip; for one country — on its leg.',
      countries: 'Countries', kmAmount: 'Pay per km', perDiem: 'Per diem', approvedTotal: 'Approved total for the month', pay: 'Pay per km and per diem',
      problems: 'To fix before approval', warnings: 'Drivers’ documents',
      approve: 'Approve', approveConfirm: 'Approve the trip? The rate, exchange rates and per diem are frozen and the trip goes into payroll.',
      unapprove: 'Cancel approval', unapproveConfirm: 'Cancel the approval? The trip leaves payroll (recalculate the month).',
      approvedHint: 'The trip is approved and goes into the payroll of the return month. To correct it, cancel the approval (while the month’s payroll is not approved).',
      done: { approve: 'The trip is approved.', unapprove: 'The approval is cancelled.' },
    },
    leg: {
      title: 'Countries crossed', add: 'Add country', country: 'Country', entered: 'Entry', left: 'Exit', loading: 'Loading',
      unloading: 'Unloading', meals: 'Meals provided', km: 'Km',
      hint: 'One row per foreign country, with the border crossing time at entry and exit, in route order. Time outside them is in the Republic of Moldova.',
    },
    diem: {
      person: 'Driver', day: 'Day', country: 'Country', hours: 'Hours', norm: 'Norm', fx: 'NBM rate', amount: 'Amount, lei', taxable: 'Above norm',
      how: 'How it was counted', total: 'Total', none: 'The per diem is counted on save.',
    },
  },
}

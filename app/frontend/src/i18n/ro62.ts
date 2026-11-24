// S6b (pasul a): transportul — vehiculele, tarifele pe km, țările cu normele diurnei, cursele (foile de parcurs).
export default {
  menu: { trips: 'Curse (foi de parcurs)', vehicles: 'Vehiculele', kmRates: 'Tarife pe km', countries: 'Țările și diurnele' },
  desk: { tab: { trip: 'Cursa {{number}}' } },
  constants: {
    transport_enabled: 'Modulul Transportul (cursele, diurnele, plata pe km)',
    transport_enabledHint: 'Pentru transportatori (marfă, pasageri; în țară și internațional): vehiculele, cursele cu țările parcurse, diurnele șoferilor pe țări și plata pe km, care intră în calculul salariului. Oprit — meniul, setările și API-ul transportului nu apar.',
  },
  pay: { type: { autos: { trip_km: 'Transport: plata pe km (cursele aprobate)', per_diem: 'Transport: diurna în limita normelor', per_diem_excess: 'Transport: diurna peste norme (impozabilă)' } } },
  tr: {
    any: 'oricare',
    status: { draft: 'Ciornă', approved: 'Aprobată' },
    kinds: { goods: 'Marfă', passengers: 'Pasageri' },
    scopes: { domestic: 'În țară', international: 'Internațional' },
    vehicleKinds: { tractor: 'Cap tractor', truck: 'Camion', trailer: 'Semiremorcă / remorcă', bus: 'Autobuz', minibus: 'Microbuz', van: 'Autoutilitară', car: 'Autoturism', other: 'Alta' },
    veh: {
      plate: 'Nr. de înmatriculare', kind: 'Felul', brand: 'Marca', model: 'Modelul', category: 'Categoria', tachograph: 'Tahograf',
      fuelNorm: 'Consum, l/100 km', subdivision: 'Coloana / subdiviziunea',
      hint: 'Vehiculele și remorcile firmei: numărul, felul, categoria permisului cerută, tahograful (cere cardul șoferului). Remorca se alege separat în cursă.',
    },
    rate: {
      dateFrom: 'În vigoare din', rate: 'Tariful, lei/km', document: 'Temeiul (contractul colectiv, regulamentul de salarizare)',
      hint: 'Tariful pe km al șoferului, din data dată. Gol la felul cursei / arie / vehicul = oricare; la o cursă se ia rândul cel mai potrivit, în vigoare la plecare. Plata pe km intră în comparația cu salariul minim (CTR art. 142: plata pe distanță — doar cu salariul minim garantat).',
    },
    country: {
      code: 'Codul', current: 'Diurna acum', noNorm: 'fără normă', norms: 'Normele diurnei', dateFrom: 'În vigoare din', amount: 'Norma pe zi',
      currency: 'Valuta', document: 'Temeiul', checkTag: 'de verificat',
      hint: 'Țările parcurse în curse și normele diurnei pe zi (HG nr. 10/2012), cu istoric. Normele livrate se verifică cu textul în vigoare; o normă nouă — rând nou din data ei.',
      normsHint: 'Norma pe zi în valuta țării, din data dată; cursa ia norma în vigoare în ziua respectivă. Suma în lei — la cursul BNM.',
    },
    trip: {
      title: 'Foaia de parcurs', new: 'Cursă nouă', import: 'Curse din Excel',
      importHint: 'Un rând pe fiecare țară străină a cursei; rândurile cu același „Nr. cursei” fac o cursă (ciornă). Ora: zz.ll.aaaa hh:mm — ora trecerii frontierei.',
      hint: 'Cursa aprobată intră în calculul salariului lunii întoarcerii: plata pe km și diurna șoferilor.',
      driver: 'Șoferul', coDriver: 'Al doilea șofer', vehicle: 'Vehiculul', trailer: 'Remorca', kind: 'Felul cursei', scope: 'Aria',
      departure: 'Plecarea', arrival: 'Întoarcerea', arrivalHint: 'Cursa intră în salariul lunii întoarcerii.',
      odometerOut: 'Kilometrajul la plecare', odometerIn: 'Kilometrajul la întoarcere', km: 'Km', kmHint: 'Cu kilometrajul — se socotesc singuri.',
      perDiemPct: 'Diurna, % din normă', perDiemPctHint: 'Gol — procentul din Constante.', route: 'Ruta', adr: 'Mărfuri periculoase (ADR)',
      meals: 'Masa asigurată', mealsHint: 'Pe toată cursa; pe o țară — la segment.',
      countries: 'Țările', kmAmount: 'Plata pe km', perDiem: 'Diurna', approvedTotal: 'Total aprobat în lună', pay: 'Plata pe km și diurna',
      problems: 'De corectat înainte de aprobare', warnings: 'Actele șoferilor',
      approve: 'Aprobă', approveConfirm: 'Aprobați cursa? Tariful, cursurile valutare și diurna se fixează, iar cursa intră în calculul salariului.',
      unapprove: 'Anulează aprobarea', unapproveConfirm: 'Anulați aprobarea? Cursa iese din calculul salariului (recalculați luna).',
      approvedHint: 'Cursa este aprobată și intră în calculul salariului lunii întoarcerii. Pentru corecturi — anulați aprobarea (cât calculul lunii nu e aprobat).',
      done: { approve: 'Cursa este aprobată.', unapprove: 'Aprobarea este anulată.' },
    },
    leg: {
      title: 'Țările parcurse', add: 'Adaugă țara', country: 'Țara', entered: 'Intrarea', left: 'Ieșirea', loading: 'Încărcare',
      unloading: 'Descărcare', meals: 'Masa asigurată', km: 'Km',
      hint: 'Câte un rând pe fiecare țară străină, cu ora trecerii frontierei la intrare și la ieșire, în ordinea parcursului. Timpul în afara lor e în Republica Moldova.',
    },
    diem: {
      person: 'Șoferul', day: 'Ziua', country: 'Țara', hours: 'Ore', norm: 'Norma', fx: 'Cursul BNM', amount: 'Suma, lei', taxable: 'Peste normă',
      how: 'Cum s-a socotit', total: 'Total', none: 'Diurna se socotește la salvare.',
    },
  },
}

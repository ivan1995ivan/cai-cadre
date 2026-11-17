// Textele pentru Etapa 3b: WMS (depozitul pe adrese) și terminalul.
const ro5 = {
  wms: {
    tabs: { map: 'Harta depozitului', topology: 'Zone și celule', stock: 'Stoc pe celule', tasks: 'Sarcini', movements: 'Mutări' },
    zoneKinds: {
      receiving: 'Recepție', quarantine: 'Carantină', coil: 'Stocare role', cantilever: 'Cantilever (foi lungi)', shelving: 'Rafturi accesorii',
      floor: 'La podea', production: 'Lângă linia de producție', shipping: 'Expediție', scrap: 'Deșeuri', returns: 'Retururi',
    },
    taskKinds: { putaway: 'Plasare', move: 'Mutare', feed: 'Alimentarea producției', count: 'Inventar celulă', pick: 'Colectare' },
    taskStatus: { open: 'Deschisă', in_progress: 'În lucru', done: 'Executată', cancelled: 'Anulată' },
    enableHint: 'Niciun depozit nu lucrează pe adrese. Activați „Lucru pe adrese (WMS)” la depozit (Stocuri → Setări → Depozite), apoi creați zonele și celulele.',
    terminal: 'Terminal (TSD)', cellsUsed: 'Celule ocupate', unplacedLots: 'Loturi neplasate', openTasks: 'Sarcini deschise',
    sync: 'Sarcini pentru loturile existente', synced: 'Verificate loturi: {{count}}',
    noZones: 'Depozitul nu are încă zone. Creați-le în „Zone și celule”.',
    maxKg: 'Max. kg', maxUnits: 'Max. loturi', maxLength: 'Max. lungime (mm)', blocked: 'Blocată', emptyCell: 'Celula este goală',
    placedAt: 'Plasat', zones: 'Zone', zone: 'Zona', cells: 'Celule', address: 'Adresa', aisle: 'Rând', level: 'Nivel', position: 'Poziție',
    zonesHint: 'Zonele depozitului: recepție, stocare role, rafturi, lângă linia de producție, expediție... Tipul zonei decide ce marfă i se propune.',
    generate: 'Generează celule', generated: 'Celule create: {{count}}', chooseZone: 'Alegeți zona ca să vedeți celulele ei.',
    generateHint: 'Adresa celulei: DEPOZIT-ZONĂ-RÂND-NIVEL-POZIȚIE (de ex. RAW-A-03-2-05). Celulele existente nu se dublează.',
    aisles: 'Rânduri / rafturi', aislesHint: 'De ex. „A-C”, „1-12” sau „A,B,F”. Gol = fără rânduri.', levels: 'Niveluri', positions: 'Poziții pe nivel',
    unplaced: 'Neplasat', stockByCell: 'Marfa pe celule', stockSearch: 'Adresă, lot, nr. rolă, denumire',
    openOnly: 'Doar deschise', tasksHint: 'Sarcinile se execută pe terminal, prin scanare.', route: 'De unde → unde', assigned: 'Cine',
    cancelTask: 'Anulează',
    tsd: {
      modes: { tasks: 'Sarcinile mele', move: 'Mută / plasează', find: 'Unde este?', count: 'Inventar celulă' },
      refresh: 'Actualizează', noTasks: 'Nu sunt sarcini deschise.', lotOk: 'Lot corect', wrongLot: 'Alt lot! Se așteaptă {{lot}}.',
      done: 'Executat', from: 'De la', to: 'La', scanLot: 'Scanați lotul / rola', scanTarget: 'Scanați celula de destinație',
      scanLotFirst: 'Scanați întâi lotul (rola).', scanSource: 'scanați celula de unde luați', fromOk: 'Luat de pe {{cell}}',
      moved: 'Pus pe {{cell}}', suggested: 'Propus', scanAny: 'Scanați o celulă sau un lot', notPlaced: 'Lotul nu este pe nicio celulă.',
      scanCell: 'Scanați celula', scanCellFirst: 'Scanați întâi celula.', cellOk: 'Celula {{cell}}: scanați loturile de pe ea',
      already: 'Deja scanat', extraLot: '{{lot}} nu figura aici: va fi mutat pe această celulă',
      extraCount: 'Loturi în plus găsite: {{count}}', finishCount: 'Confirmă inventarul celulei',
      countResult: 'Corecte: {{ok}}, lipsă: {{missing}}, găsite în plus: {{found}}',
    },
  },
}

export default ro5

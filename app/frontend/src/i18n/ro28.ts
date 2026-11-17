// Mesaje: Facebook Messenger, Instagram Direct, lead-urile din Meta Lead Ads, răspunsurile rapide și setările Meta.
const ro28 = {
  messaging: {
    title: 'Mesaje', tabs: { conversations: 'Conversații', leads: 'Lead-uri', quickReplies: 'Răspunsuri rapide' },
    settings: 'Setări Meta', search: 'Nume, client, text', mine: 'Doar ale mele', unread: 'Necitite',
    status: { active: 'Deschise', new: 'Noi', open: 'În lucru', closed: 'Închise', all: 'Toate' },
    allChannels: 'Toate canalele', empty: 'Nicio conversație', choose: 'Alegeți o conversație din stânga',
    client: 'Client', linkClient: 'Legați de client', openClient: 'Fișa clientului', newOffer: 'Ofertă nouă',
    manager: 'Manager', assign: 'Dați managerului', close: 'Închide', reopen: 'Redeschide', back: 'Înapoi la listă',
    reply: 'Răspuns', replyPlaceholder: 'Scrieți răspunsul… (Ctrl+Enter — trimite)', send: 'Trimite',
    quickReplies: 'Răspunsuri rapide', noQuickReplies: 'Nu sunt răspunsuri rapide (fila Răspunsuri rapide)',
    windowClosed: 'Au trecut peste 24 de ore de la ultimul mesaj al clientului: Meta nu permite răspunsul din pagină până nu scrie el din nou. Sunați-l sau scrieți-i pe altă cale.',
    failed: 'Netrimis', attachment: 'Atașament', you: 'Pagina', lastMessage: 'Ultimul mesaj',
    leads: {
      date: 'Data', channel: 'Canalul', form: 'Formularul', name: 'Numele', phone: 'Telefon', email: 'E-mail', client: 'Client',
      newClient: 'client nou', manager: 'Manager', refetch: 'Citește din nou din Meta', fields: 'Toate câmpurile', error: 'Eroare',
    },
    qr: { title: 'Titlul', text: 'Textul (română)', textRu: 'Textul (rusă)', sort: 'Ordinea', active: 'Activ',
      hint: 'Răspunsurile gata la întrebările dese (prețul, livrarea, montajul, plata): în conversație se aleg din „Răspunsuri rapide” și se pun în câmpul de răspuns.' },
  },
  messagingSettings: {
    title: 'Mesaje: Facebook și Instagram', app: 'Aplicația Meta', appId: 'App ID', appSecret: 'App Secret',
    secretKept: 'Secretul e salvat; scrieți altul doar ca să-l schimbați.', verifyToken: 'Verify token (tokenul de verificare)',
    regenerate: 'Generează altul', webhookUrl: 'Callback URL (adresa webhook-ului)', publicUrl: 'Adresa publică a CRM-ului',
    publicUrlHint: 'Gol = adresa din care ați deschis acum programul. Meta cere o adresă publică HTTPS.',
    notHttps: 'Adresa nu este HTTPS: Meta nu trimite evenimentele la ea. Serverul are nevoie de o adresă publică cu certificat (HTTPS).',
    copied: 'Copiat', channels: 'Canalele (paginile Facebook / conturile Instagram)', addChannel: 'Adaugă canal',
    kind: 'Tipul', name: 'Denumirea', pageId: 'ID-ul paginii / contului Instagram', pageIdHint: 'Gol = se ia din token (pagina Facebook). La Instagram — ID-ul contului Instagram Business.',
    token: 'Page Access Token', tokenKept: 'Tokenul e salvat; scrieți altul doar ca să-l schimbați.', defaultManager: 'Managerul conversațiilor noi',
    defaultManagerHint: 'Gol = pe rând între managerii de vânzări (bifa „Manager de vânzări” din Utilizatori).', active: 'Activ',
    test: 'Probează și abonează', testOk: 'Pagina „{{name}}” răspunde; abonarea la webhook: {{sub}}', lastError: 'Ultima eroare',
    kinds: { facebook: 'Facebook Messenger', instagram: 'Instagram Direct', whatsapp: 'WhatsApp', tiktok: 'TikTok' },
    guide: 'Cum se leagă (pas cu pas)',
    steps: [
      'Pe developers.facebook.com → My Apps → Create App, tipul „Business”. Aplicația trebuie legată de Business Manager-ul firmei, iar pagina Facebook (și contul Instagram Business, legat de pagină) — să fie ale aceluiași Business.',
      'În aplicație adăugați produsele Messenger, Instagram (Instagram Graph API / Messaging) și Webhooks. App ID și App Secret (App settings → Basic) se scriu mai sus.',
      'Webhooks: pentru obiectul Page și pentru Instagram puneți Callback URL și Verify token de mai sus → Verify and save. Bifați câmpurile messages, messaging_postbacks, message_echoes (și leadgen la Page — pentru Lead Ads).',
      'Messenger → Settings → Access Tokens: generați Page Access Token pentru pagină și adăugați-l aici ca canal (Facebook). Pentru Instagram adăugați un canal Instagram cu ID-ul contului Instagram Business și același token al paginii.',
      'Apăsați „Probează și abonează” la fiecare canal: CRM-ul verifică tokenul și abonează pagina la webhook.',
      'Permisiunile cerute: pages_messaging, pages_manage_metadata, pages_read_engagement, leads_retrieval, instagram_basic, instagram_manage_messages. Până la App Review aplicația lucrează doar cu administratorii / testerii ei; pentru clienți reali trimiteți aplicația la App Review (cu descrierea și filmulețul folosirii) și treceți-o în modul Live.',
      'Serverul CRM trebuie să aibă o adresă publică HTTPS (domeniu cu certificat): Meta nu trimite evenimente la adrese locale sau HTTP.',
    ],
  },
}

export default ro28

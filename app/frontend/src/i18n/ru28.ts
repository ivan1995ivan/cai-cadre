// Сообщения: Facebook Messenger, Instagram Direct, лиды из Meta Lead Ads, быстрые ответы и настройки Meta.
const ru28 = {
  messaging: {
    title: 'Сообщения', tabs: { conversations: 'Диалоги', leads: 'Лиды', quickReplies: 'Быстрые ответы' },
    settings: 'Настройки Meta', search: 'Имя, клиент, текст', mine: 'Только мои', unread: 'Непрочитанные',
    status: { active: 'Открытые', new: 'Новые', open: 'В работе', closed: 'Закрытые', all: 'Все' },
    allChannels: 'Все каналы', empty: 'Нет диалогов', choose: 'Выберите диалог слева',
    client: 'Клиент', linkClient: 'Привязать к клиенту', openClient: 'Карточка клиента', newOffer: 'Новое предложение',
    manager: 'Менеджер', assign: 'Передать менеджеру', close: 'Закрыть', reopen: 'Открыть снова', back: 'Назад к списку',
    reply: 'Ответ', replyPlaceholder: 'Напишите ответ… (Ctrl+Enter — отправить)', send: 'Отправить',
    quickReplies: 'Быстрые ответы', noQuickReplies: 'Нет быстрых ответов (вкладка «Быстрые ответы»)',
    windowClosed: 'С последнего сообщения клиента прошло больше 24 часов: Meta не разрешает отвечать со страницы, пока клиент не напишет снова. Позвоните ему или напишите другим способом.',
    failed: 'Не отправлено', attachment: 'Вложение', you: 'Страница', lastMessage: 'Последнее сообщение',
    leads: {
      date: 'Дата', channel: 'Канал', form: 'Форма', name: 'Имя', phone: 'Телефон', email: 'E-mail', client: 'Клиент',
      newClient: 'новый клиент', manager: 'Менеджер', refetch: 'Прочитать заново из Meta', fields: 'Все поля', error: 'Ошибка',
    },
    qr: { title: 'Название', text: 'Текст (румынский)', textRu: 'Текст (русский)', sort: 'Порядок', active: 'Активен',
      hint: 'Готовые ответы на частые вопросы (цена, доставка, монтаж, оплата): в диалоге выбираются в «Быстрые ответы» и вставляются в поле ответа.' },
  },
  messagingSettings: {
    title: 'Сообщения: Facebook и Instagram', app: 'Приложение Meta', appId: 'App ID', appSecret: 'App Secret',
    secretKept: 'Секрет сохранён; вводите новый только чтобы заменить.', verifyToken: 'Verify token (токен проверки)',
    regenerate: 'Сгенерировать новый', webhookUrl: 'Callback URL (адрес вебхука)', publicUrl: 'Публичный адрес CRM',
    publicUrlHint: 'Пусто = адрес, с которого сейчас открыта программа. Meta требует публичный адрес HTTPS.',
    notHttps: 'Адрес не HTTPS: Meta не будет присылать на него события. Серверу нужен публичный адрес с сертификатом (HTTPS).',
    copied: 'Скопировано', channels: 'Каналы (страницы Facebook / аккаунты Instagram)', addChannel: 'Добавить канал',
    kind: 'Тип', name: 'Название', pageId: 'ID страницы / аккаунта Instagram', pageIdHint: 'Пусто = берётся из токена (страница Facebook). Для Instagram — ID аккаунта Instagram Business.',
    token: 'Page Access Token', tokenKept: 'Токен сохранён; вводите новый только чтобы заменить.', defaultManager: 'Менеджер новых диалогов',
    defaultManagerHint: 'Пусто = по очереди между менеджерами по продажам (галочка «Менеджер по продажам» в Пользователях).', active: 'Активен',
    test: 'Проверить и подписать', testOk: 'Страница «{{name}}» отвечает; подписка на вебхук: {{sub}}', lastError: 'Последняя ошибка',
    kinds: { facebook: 'Facebook Messenger', instagram: 'Instagram Direct', whatsapp: 'WhatsApp', tiktok: 'TikTok' },
    guide: 'Как подключить (по шагам)',
    steps: [
      'На developers.facebook.com → My Apps → Create App, тип «Business». Приложение должно быть привязано к Business Manager фирмы, а страница Facebook (и аккаунт Instagram Business, привязанный к странице) — принадлежать тому же Business.',
      'В приложении добавьте продукты Messenger, Instagram (Instagram Graph API / Messaging) и Webhooks. App ID и App Secret (App settings → Basic) впишите выше.',
      'Webhooks: для объекта Page и для Instagram укажите Callback URL и Verify token отсюда → Verify and save. Отметьте поля messages, messaging_postbacks, message_echoes (и leadgen у Page — для Lead Ads).',
      'Messenger → Settings → Access Tokens: сгенерируйте Page Access Token страницы и добавьте его здесь как канал (Facebook). Для Instagram добавьте канал Instagram с ID аккаунта Instagram Business и тем же токеном страницы.',
      'Нажмите «Проверить и подписать» у каждого канала: CRM проверит токен и подпишет страницу на вебхук.',
      'Нужные разрешения: pages_messaging, pages_manage_metadata, pages_read_engagement, leads_retrieval, instagram_basic, instagram_manage_messages. До App Review приложение работает только с его администраторами / тестировщиками; для реальных клиентов отправьте приложение на App Review (с описанием и видео использования) и переведите в режим Live.',
      'У сервера CRM должен быть публичный адрес HTTPS (домен с сертификатом): Meta не отправляет события на локальные адреса или HTTP.',
    ],
  },
}

export default ru28

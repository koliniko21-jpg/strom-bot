import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "1327283301:AAHKJGjr-QWWvyBMjXCeapICFTf-Clu52gI"
CHAT_ID_CONSULTANT = 773441776  # Ваш личный Telegram Chat ID
WHATSAPP_NUMBER = "+4915788348961"
TELEGRAM_USERNAME = "@nikolajnujkinfit"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- СТЕЙТЫ (СОСТОЯНИЯ ДЛЯ ВОРОНКИ) ---
(
    LANGUAGE_SELECT,
    MAIN_MENU,
    START_CHECK,
    NAME,
    CITY_PLZ,
    PROVIDER,
    CONSUMPTION,
    CONTRACT_PHOTO,
    CONTACT_INFO,
    CALCULATE_INPUT,
) = range(10)

# --- ТЕКСТЫ И КНОПКИ БОТА ---
TEXTS = {
    'start': {
        'RU': "Привет! Меня зовут **Nikolaj Nujkin** — энергетический консультант с 8-летним опытом. Я помогу тебе проверить твой контракт на электроэнергию или газ и найти способы сэкономить.\n\nВыбери язык:",
        'DE': "Hallo! Ich heiße **Nikolaj Nujkin** — Energieberater mit 8 Jahren Erfahrung. Ich helfe Ihnen, Ihren Strom- oder Gasvertrag zu überprüfen und Einsparmöglichkeiten zu finden.\n\nBitte wähle die Sprache:",
    },
    'main_menu': {
        'RU': "**Отлично!** Выбери, что ты хочешь сделать прямо сейчас:",
        'DE': "**Perfekt!** Wählen Sie, was Sie tun möchten:",
    },
    'menu_buttons': {
        'RU': {
            'CHECK': "🔍 Проверить мой контракт",
            'CALC': "💰 Рассчитать экономию",
            'TIPS': "💡 Советы по экономии энергии",
            'REVIEW': "⭐ Отзывы клиентов",
            'CONTACT': "🧑‍💼 Связаться с экспертом",
        },
        'DE': {
            'CHECK': "🔍 Vertrag prüfen",
            'CALC': "💰 Einsparung berechnen",
            'TIPS': "💡 Energiespartipps",
            'REVIEW': "⭐ Kundenbewertungen",
            'CONTACT': "🧑‍💼 Kontakt zum Experten",
        },
    },
    'check_start': {
        'RU': "**Экспертная оценка.** Бесплатная проверка твоего контракта позволит точно узнать, переплачиваешь ли ты за электроэнергию или газ. Я проведу точный расчёт и дам персональные рекомендации — **всё бесплатно** и без обязательств.",
        'DE': "**Expertenschätzung.** Eine kostenlose Vertragsprüfung zeigt Ihnen genau, ob Sie zu viel für Strom oder Gas bezahlen. Ich werde eine genaue Berechnung und persönliche Empfehlungen geben – **alles kostenlos** und unverbindlich.",
    },
    'check_start_button': {'RU': "Начать проверку 🚀", 'DE': "Prüfung starten 🚀"},
    'questions': {
        '1_NAME': {'RU': "Как тебя зовут?", 'DE': "Wie heißen Sie?"},
        '2_CITY': {
            'RU': "В каком городе/PLZ ты живёшь? (Это важно для поиска региональных тарифов).",
            'DE': "In welcher Stadt/PLZ wohnen Sie? (Dies ist wichtig für die Suche nach regionalen Tarifen).",
        },
        '3_PROVIDER': {
            'RU': "Кто твой текущий поставщик энергии (Strom- und/oder Gasanbieter)?",
            'DE': "Wer ist Ihr aktueller Energieanbieter (Strom- und/oder Gasanbieter)?",
        },
        '4_CONSUMPTION': {
            'RU': "Сколько электроэнергии и/или газа ты потребляешь в год (в кВт⋅ч)? (Укажи число).",
            'DE': "Wie hoch ist Ihr Strom- und/oder Gasverbrauch pro Jahr (in kWh)? (Geben Sie die Zahl ein).",
        },
        '5_PHOTO': {
            'RU': "Для максимально точного анализа пришли фото контракта или PDF. Если не хочешь, просто отправь «Нет» или нажми кнопку ниже.",
            'DE': "Für eine möglichst genaue Analyse senden Sie uns bitte ein Foto oder PDF Ihres Vertrags. Wenn Sie dies nicht möchten, senden Sie einfach «Nein» oder klicken Sie auf die Schaltfläche unten.",
        },
        '6_CONTACT': {
            'RU': "Отлично, почти готово! Укажи номер телефона или Telegram-логин, чтобы я лично (Nikolaj) мог прислать тебе результаты проверки и персональные рекомендации.",
            'DE': "Wunderbar, fast fertig! Bitte geben Sie Ihre Telefonnummer oder Ihren Telegram-Benutzernamen an, damit ich (Nikolaj) Ihnen die Prüfungsergebnisse und persönlichen Empfehlungen zusenden kann.",
        },
    },
    'skip_photo_button': {'RU': "Пропустить", 'DE': "Überspringen"},
    'lead_thanks': {
        'RU': "**🚀 Данные приняты!** Спасибо за информацию. Я лично, как эксперт, проанализирую твой текущий контракт, проведу расчёт потенциальной экономии и дам точные рекомендации.\n\n**Ожидай сообщение от меня в Telegram или WhatsApp** в ближайшие 24 часа. До связи!",
        'DE': "**🚀 Daten erhalten!** Vielen Dank für die Informationen. Ich werde Ihren aktuellen Vertrag persönlich als Experte analysieren, die potenziellen Einsparungen berechnen und Ihnen genaue Empfehlungen geben.\n\n**Sie erhalten in Kürze (innerhalb von 24 Stunden) eine persönliche Nachricht von mir (Nikolaj) über Telegram oder WhatsApp.** Bis bald!",
    },
    'tips_content': {
        'RU': "💡 **ТОП-3 простых совета от эксперта:** Ты можешь начать экономить уже сейчас, следуя этим простым правилам:\n\n– Выключай приборы полностью, а не оставляй их в режиме ожидания (Standby).\n– Используй современные светодиодные (LED) лампы.\n– Настрой термостат на оптимальную температуру (каждый градус — это +6% к расходу).",
        'DE': "💡 **TOP-3 einfache Expertentipps:** Sie können sofort mit dem Sparen beginnen, indem Sie diese einfachen Regeln befolgen:\n\n– Geräte vollständig ausschalten, nicht im Standby-Modus lassen.\n– Verwenden Sie moderne LED-Lampen.\n– Stellen Sie den Thermostat auf die optimale Temperatur ein (jedes Grad ist eine Erhöhung des Verbrauchs um 6%).",
    },
    'calc_prompt': {
        'RU': "**💰 Быстрая оценка экономии.** Чтобы примерно оценить твою потенциальную выгоду, введи текущие расходы на электроэнергию/газ в месяц (только число, в евро):",
        'DE': "**💰 Schnelle Einsparungsschätzung.** Geben Sie Ihre aktuellen monatlichen Strom-/Gaszahlungen (nur die Zahl, in Euro) ein, um Ihre möglichen Einsparungen zu berechnen:",
    },
    'contact_menu_text': {
        'RU': "**Давай оформим выгоду.** Если ты готов(а) к реальной экономии, я могу составить персональный энергоплан и помочь оформить контракт с поставщиком. Таким образом, ты будешь экономить каждый месяц без лишних хлопот. Просто напиши мне или выбери удобное время.",
        'DE': "**Lassen Sie uns Ihre Vorteile sichern.** Wenn Sie bereit für echte Einsparungen sind, kann ich einen persönlichen Energieplan erstellen und Ihnen helfen, einen Vertrag beim besten Anbieter abzuschließen. So sparen Sie jeden Monat ohne unnötigen Aufwand. Schreiben Sie mir einfach oder wählen Sie einen passenden Termin.",
    },
    'reviews_content': {
        'RU': "**⭐ Результаты говорят сами за себя.** Клиенты, с которыми я работал, экономят до 30% на счетах за электроэнергию и газ. Вот что они говорят:\n\n> *“Благодаря Николаю мы снизили расходы на газ почти вдвое! Он настоящий эксперт.”*\n> *“Все объяснил понятно, очень доволен! Проверку провёл быстро и с максимальной выгодой.”*\n> *“Уже порекомендовала всем друзьям. Спасибо за ежегодную экономию!”*",
        'DE': "**⭐ Die Ergebnisse sprechen für sich.** Kunden, mit denen ich zusammengearbeitet habe, sparen bis zu 30 % bei ihren Strom- und Gasrechnungen. Hier ist, was sie sagen:\n\n> *„Dank Nikolaj haben wir unsere Gasrechnung fast halbiert! Er ist ein echter Experte.”*\n> *„Alles klar erklärt, sehr zufrieden! Die Prüfung wurde schnell und mit maximalem Nutzen durchgeführt.”*\n> *„Ich habe es bereits allen meinen Freunden empfohlen. Vielen Dank für die jährlichen Einsparungen!”*",
    },
}


def get_text(lang, key):
    return TEXTS.get(key, {}).get(lang, 'Text error')


def build_menu(lang):
    buttons = TEXTS['menu_buttons'][lang]
    keyboard = [
        [buttons['CHECK']],
        [buttons['CALC'], buttons['TIPS']],
        [buttons['REVIEW'], buttons['CONTACT']],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context):
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_RU'),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data='lang_DE'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        TEXTS['start']['RU'] + "\n\n" + TEXTS['start']['DE'],
        reply_markup=reply_markup,
        parse_mode='Markdown',
    )
    return LANGUAGE_SELECT


async def set_language(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    await show_main_menu(update, context, message_source=query)
    return MAIN_MENU


async def show_main_menu(update: Update, context, message_source=None):
    lang = context.user_data.get('lang', 'RU')
    menu_text = get_text(lang, 'main_menu')
    reply_markup = build_menu(lang)

    if message_source and isinstance(message_source, Update.CallbackQuery):
        await message_source.edit_message_text(
            menu_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    elif update.message:
        await update.message.reply_text(
            menu_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=menu_text,
            reply_markup=reply_markup,
            parse_mode='Markdown',
        )
    return MAIN_MENU


async def handle_menu_choice(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text
    menu_actions = {v: k for k, v in TEXTS['menu_buttons'][lang].items()}
    action = menu_actions.get(text)

    if action == 'CHECK':
        return await start_contract_check(update, context)
    elif action == 'CALC':
        return await calculate_economy_prompt(update, context)
    elif action == 'TIPS':
        return await show_tips(update, context)
    elif action == 'REVIEW':
        return await show_reviews(update, context)
    elif action == 'CONTACT':
        return await show_contact_menu(update, context)
    else:
        await update.message.reply_text(
            get_text(lang, 'main_menu'),
            reply_markup=build_menu(lang),
            parse_mode='Markdown',
        )
        return MAIN_MENU


# --- ВОРОНКА СБОРА ДАННЫХ ---
async def start_contract_check(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data'] = {}
    check_text = get_text(lang, 'check_start')
    keyboard = [
        [
            InlineKeyboardButton(
                get_text(lang, 'check_start_button'), callback_data='start_lead'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        check_text, reply_markup=reply_markup, parse_mode='Markdown'
    )
    return START_CHECK


async def ask_name(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'RU')
    await query.edit_message_text(
        get_text(lang, 'questions')['1_NAME'],
        reply_markup=None,
        parse_mode='Markdown',
    )
    return NAME


async def collect_name(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Имя / Name'] = update.message.text
    await update.message.reply_text(
        get_text(lang, 'questions')['2_CITY'], parse_mode='Markdown'
    )
    return CITY_PLZ


async def collect_city_plz(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Город/PLZ'] = update.message.text
    await update.message.reply_text(
        get_text(lang, 'questions')['3_PROVIDER'], parse_mode='Markdown'
    )
    return PROVIDER


async def collect_provider(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Поставщик'] = update.message.text
    await update.message.reply_text(
        get_text(lang, 'questions')['4_CONSUMPTION'], parse_mode='Markdown'
    )
    return CONSUMPTION


async def collect_consumption(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text.replace(',', '.')

    if not re.match(r'^\d+(\.\d+)?$', text):
        await update.message.reply_text(
            f"❌ {'Пожалуйста, введи только число (в кВт⋅ч).' if lang == 'RU' else 'Bitte geben Sie nur eine Zahl (in kWh) ein.'}",
            parse_mode='Markdown',
        )
        return CONSUMPTION

    context.user_data['lead_data']['Потребление (кВт⋅ч)'] = text
    keyboard = [
        [
            InlineKeyboardButton(
                get_text(lang, 'skip_photo_button'), callback_data='skip_photo'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_text(lang, 'questions')['5_PHOTO'],
        reply_markup=reply_markup,
        parse_mode='Markdown',
    )
    return CONTRACT_PHOTO


async def collect_photo(update: Update, context):
    lang = context.user_data.get('lang', 'RU')

    if update.message.photo or update.message.document:
        file_type = (
            'Фото контракта' if update.message.photo else 'Документ (PDF)'
        )
        context.user_data['lead_data'][
            'Контракт'
        ] = f"{file_type} прикреплен ниже."
        context.user_data['lead_file_id'] = (
            update.message.photo[-1].file_id
            if update.message.photo
            else update.message.document.file_id
        )
    elif update.message.text and update.message.text.lower() in (
        'нет',
        'nein',
        get_text('RU', 'skip_photo_button').lower(),
        get_text('DE', 'skip_photo_button').lower(),
    ):
        context.user_data['lead_data']['Контракт'] = 'Пропущено клиентом'
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    get_text(lang, 'skip_photo_button'),
                    callback_data='skip_photo',
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ {'Пожалуйста, пришлите фото/PDF или нажмите «Пропустить».' if lang == 'RU' else 'Bitte senden Sie ein Foto/PDF oder klicken Sie auf «Überspringen».'}",
            reply_markup=reply_markup,
            parse_mode='Markdown',
        )
        return CONTRACT_PHOTO

    await update.message.reply_text(
        get_text(lang, 'questions')['6_CONTACT'], parse_mode='Markdown'
    )
    return CONTACT_INFO


async def skip_photo(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Контракт'] = 'Пропущено кнопкой'
    await query.edit_message_text(
        get_text(lang, 'questions')['6_CONTACT'],
        reply_markup=None,
        parse_mode='Markdown',
    )
    return CONTACT_INFO


async def send_lead(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Контакт'] = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "нет username"

    lead_info = context.user_data['lead_data']

    # Формирование сообщения с лидом для Николая
    telegram_notification = f"🔔 **НОВЫЙ ЛИД ИЗ ТЕЛЕГРАМ-БОТА** 🔔\n\n"
    telegram_notification += (
        f"**Клиент:** @{username} (ID: `{user_id}`)\n"
    )
    telegram_notification += f"**Язык общения:** {lang}\n"
    telegram_notification += "-----------------------------------\n"
    for key, value in lead_info.items():
        telegram_notification += f"**{key}:** {value}\n"

    try:
        # Отправка уведомления эксперту в Telegram
        await context.bot.send_message(
            chat_id=CHAT_ID_CONSULTANT,
            text=telegram_notification,
            parse_mode='Markdown',
        )

        # Пересылка фото/документа, если клиент прикрепил
        file_id = context.user_data.get('lead_file_id')
        if file_id:
            try:
                await context.bot.send_photo(
                    chat_id=CHAT_ID_CONSULTANT, photo=file_id
                )
            except Exception:
                await context.bot.send_document(
                    chat_id=CHAT_ID_CONSULTANT, document=file_id
                )
        logger.info(f"Лид от пользователя {user_id} отправлен консультанту.")
    except Exception as e:
        logger.error(
            f"Не удалось отправить лид консультанту {CHAT_ID_CONSULTANT}: {e}"
        )

    # Ответ клиенту
    await update.message.reply_text(
        get_text(lang, 'lead_thanks'),
        reply_markup=build_menu(lang),
        parse_mode='Markdown',
    )
    return MAIN_MENU


# --- ДОПОЛНИТЕЛЬНЫЕ РАЗДЕЛЫ ---
async def calculate_economy_prompt(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(
        get_text(lang, 'calc_prompt'), reply_markup=None, parse_mode='Markdown'
    )
    return CALCULATE_INPUT


async def calculate_economy(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text.replace(',', '.')

    try:
        cost = float(text)
        if cost <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            f"❌ {'Пожалуйста, введи только число.' if lang == 'RU' else 'Bitte geben Sie nur eine Zahl ein.'} "
            + get_text(lang, 'calc_prompt'),
            parse_mode='Markdown',
        )
        return CALCULATE_INPUT

    if lang == 'RU':
        result_text = f"**Примерный расчёт:** С моей помощью клиенты обычно экономят **15-30%** от текущих расходов. При твоих расходах в **{cost:.2f} €** в месяц, твоя потенциальная экономия составит **{(cost * 0.15):.2f} €** - **{(cost * 0.25):.2f} €** в месяц или до **{(cost * 0.25 * 12):.2f} €** в год! Но для точного расчёта нужна бесплатная проверка контракта."
    else:
        result_text = f"**Beispielrechnung:** Mit meiner Hilfe sparen Kunden typischerweise **15-30%** der aktuellen Kosten. Bei Ihren Ausgaben von **{cost:.2f} €** pro Monat betragen Ihre potenziellen Einsparungen **{(cost * 0.15):.2f} €** - **{(cost * 0.25):.2f} €** pro Monat oder bis zu **{(cost * 0.25 * 12):.2f} €** pro Jahr! Aber für eine genaue Berechnung ist eine kostenlose Vertragsprüfung erforderlich."

    keyboard = [
        [
            InlineKeyboardButton(
                get_text(lang, 'check_start_button'), callback_data='start_lead'
            )
        ],
        [
            InlineKeyboardButton(
                get_text(lang, 'menu_buttons')['CONTACT'],
                url=f"https://t.me/{TELEGRAM_USERNAME.lstrip('@')}",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        result_text, reply_markup=reply_markup, parse_mode='Markdown'
    )
    return MAIN_MENU


async def show_tips(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    keyboard = [
        [
            InlineKeyboardButton(
                get_text(lang, 'check_start_button'), callback_data='start_lead'
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_text(lang, 'tips_content'),
        reply_markup=reply_markup,
        parse_mode='Markdown',
    )
    return MAIN_MENU


async def show_reviews(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    keyboard = [
        [
            InlineKeyboardButton(
                get_text(lang, 'check_start_button'), callback_data='start_lead'
            )
        ],
        [
            InlineKeyboardButton(
                get_text(lang, 'menu_buttons')['CONTACT'],
                url=f"https://t.me/{TELEGRAM_USERNAME.lstrip('@')}",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_text(lang, 'reviews_content'),
        reply_markup=reply_markup,
        parse_mode='Markdown',
    )
    return MAIN_MENU


async def show_contact_menu(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    keyboard = [
        [
            InlineKeyboardButton(
                get_text(lang, 'menu_buttons')['CONTACT'],
                url=f"https://t.me/{TELEGRAM_USERNAME.lstrip('@')}",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_text(lang, 'contact_menu_text'),
        reply_markup=reply_markup,
        parse_mode='Markdown',
    )
    return MAIN_MENU


async def handle_callback_main_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == 'start_lead':
        return await ask_name(update, context)
    return await show_main_menu(update, context, message_source=query)


async def cancel(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(
        f"✅ {'Воронка отменена. Возвращаемся в главное меню.' if lang == 'RU' else 'Trichter abgebrochen. Zurück zum Hauptmenü.'}",
        reply_markup=build_menu(lang),
    )
    return MAIN_MENU


async def global_error_handler(update: object, context) -> None:
    logger.error("Ошибка при обработке обновления:", exc_info=context.error)


# --- ЗАПУСК БОТА ---
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    lead_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                handle_callback_main_menu, pattern='^start_lead$'
            ),
            MessageHandler(
                filters.Regex(TEXTS['menu_buttons']['RU']['CHECK'])
                | filters.Regex(TEXTS['menu_buttons']['DE']['CHECK']),
                start_contract_check,
            ),
        ],
        states={
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)
            ],
            CITY_PLZ: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_city_plz)
            ],
            PROVIDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_provider)
            ],
            CONSUMPTION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, collect_consumption
                )
            ],
            CONTRACT_PHOTO: [
                MessageHandler(
                    filters.PHOTO | filters.Document.ALL, collect_photo
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, collect_photo),
                CallbackQueryHandler(skip_photo, pattern='^skip_photo$'),
            ],
            CONTACT_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, send_lead)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        map_to_parent={MAIN_MENU: MAIN_MENU, START_CHECK: MAIN_MENU},
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(set_language, pattern='^lang_')
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_callback_main_menu, pattern='^main$|^start_lead$'
        )
    )

    application.add_handler(
        ConversationHandler(
            entry_points=[
                MessageHandler(
                    filters.Regex(TEXTS['menu_buttons']['RU']['CALC'])
                    | filters.Regex(TEXTS['menu_buttons']['DE']['CALC']),
                    calculate_economy_prompt,
                )
            ],
            states={
                CALCULATE_INPUT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, calculate_economy
                    )
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            map_to_parent={MAIN_MENU: MAIN_MENU},
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(TEXTS['menu_buttons']['RU']['TIPS'])
            | filters.Regex(TEXTS['menu_buttons']['DE']['TIPS']),
            show_tips,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(TEXTS['menu_buttons']['RU']['REVIEW'])
            | filters.Regex(TEXTS['menu_buttons']['DE']['REVIEW']),
            show_reviews,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(TEXTS['menu_buttons']['RU']['CONTACT'])
            | filters.Regex(TEXTS['menu_buttons']['DE']['CONTACT']),
            show_contact_menu,
        )
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice)
    )
    application.add_handler(lead_conv_handler)
    application.add_error_handler(global_error_handler)

    logger.info("Серверный бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

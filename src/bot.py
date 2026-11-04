import logging
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
CHAT_ID_CONSULTANT = 773441776  # Ваш Telegram Chat ID
TELEGRAM_USERNAME = "@nikolajnujkinfit"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

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

TEXTS = {
    'start': {
        'RU': "Привет! Меня зовут **Nikolaj Nujkin** — энергетический консультант с 8-летним опытом. Я помогу тебе проверить твой контракт на электроэнергию или газ и найти способы сэкономить.\n\nВыбери язык:",
        'DE': "Hallo! Ich heiße **Nikolaj Nujkin** — Energieberater mit 8 Jahren Erfahrung. Ich helfe Ihnen, Ihren Strom- oder Gasvertrag zu überprüfen und Einsparmöglichkeiten zu finden.\n\nBitte wählen Sie die Sprache:",
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
            'RU': "В каком городе/PLZ ты живёшь?",
            'DE': "In welcher Stadt/PLZ wohnen Sie?",
        },
        '3_PROVIDER': {
            'RU': "Кто твой текущий поставщик энергии?",
            'DE': "Wer ist Ihr aktueller Energieanbieter?",
        },
        '4_CONSUMPTION': {
            'RU': "Сколько электроэнергии/газа ты потребляешь в год (в кВт⋅ч)? (Укажи число)",
            'DE': "Wie hoch ist Ihr Strom-/Gasverbrauch pro Jahr (in kWh)?",
        },
        '5_PHOTO': {
            'RU': "Пришли фото контракта или PDF. Если не хочешь, просто нажми кнопку ниже.",
            'DE': "Senden Sie ein Foto oder PDF Ihres Vertrags oder klicken Sie unten.",
        },
        '6_CONTACT': {
            'RU': "Укажи номер телефона или Telegram, чтобы я лично прислал результаты.",
            'DE': "Geben Sie Ihre Telefonnummer oder Telegram an.",
        },
    },
    'skip_photo_button': {'RU': "Пропустить ➡️", 'DE': "Überspringen ➡️"},
    'lead_thanks': {
        'RU': "**🚀 Данные приняты!** Я лично проанализирую твой контракт и свяжусь с тобой в течение 24 часов.",
        'DE': "**🚀 Daten erhalten!** Ich werde Ihren Vertrag persönlich analysieren und mich in Kürze melden.",
    },
    'tips_content': {
        'RU': "💡 **Советы по экономии:**\n\n1. Выключайте приборы полностью из розетки.\n2. Используйте LED-лампы.\n3. Настройте оптимальную температуру термостата.",
        'DE': "💡 **Energiespartipps:**\n\n1. Geräte vollständig ausschalten.\n2. LED-Lampen verwenden.\n3. Thermostat optimal einstellen.",
    },
    'calc_prompt': {
        'RU': "**💰 Введи текущие расходы в месяц (в евро, только число):**",
        'DE': "**💰 Geben Sie Ihre monatlichen Kosten ein (in Euro):**",
    },
    'contact_menu_text': {
        'RU': "**Связаться с Николаем:** Напишите мне прямо в Telegram для консультации.",
        'DE': "**Kontakt:** Schreiben Sie mir direkt auf Telegram für eine Beratung.",
    },
    'reviews_content': {
        'RU': "⭐ **Отзывы клиентов:**\n\n> *“Благодаря Николаю мы снизили расходы на газ почти вдвое!”*\n> *“Все объяснил понятно, рекомендую!”*",
        'DE': "⭐ **Kundenbewertungen:**\n\n> *„Dank Nikolaj haben wir unsere Gasrechnung fast halbiert!“*\n> *„Alles klar erklärt, sehr zufrieden!“*",
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

# Прямая обработка команды /start
async def start(update: Update, context):
    context.user_data.clear() # Сброс старых состояний
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
    
    menu_text = get_text(lang, 'main_menu')
    reply_markup = build_menu(lang)
    
    await query.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
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

async def start_contract_check(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data'] = {}
    check_text = get_text(lang, 'check_start')
    keyboard = [[InlineKeyboardButton(get_text(lang, 'check_start_button'), callback_data='start_lead')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(check_text, reply_markup=reply_markup, parse_mode='Markdown')
    return START_CHECK

async def ask_name(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'RU')
    await query.edit_message_text(get_text(lang, 'questions')['1_NAME'], parse_mode='Markdown')
    return NAME

async def collect_name(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Имя'] = update.message.text
    await update.message.reply_text(get_text(lang, 'questions')['2_CITY'], parse_mode='Markdown')
    return CITY_PLZ

async def collect_city_plz(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Город/PLZ'] = update.message.text
    await update.message.reply_text(get_text(lang, 'questions')['3_PROVIDER'], parse_mode='Markdown')
    return PROVIDER

async def collect_provider(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Поставщик'] = update.message.text
    await update.message.reply_text(get_text(lang, 'questions')['4_CONSUMPTION'], parse_mode='Markdown')
    return CONSUMPTION

async def collect_consumption(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text.replace(',', '.')

    if not re.match(r'^\d+(\.\d+)?$', text):
        await update.message.reply_text("❌ Укажите число в кВт⋅ч.", parse_mode='Markdown')
        return CONSUMPTION

    context.user_data['lead_data']['Потребление'] = text
    keyboard = [[InlineKeyboardButton(get_text(lang, 'skip_photo_button'), callback_data='skip_photo')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_text(lang, 'questions')['5_PHOTO'], reply_markup=reply_markup, parse_mode='Markdown')
    return CONTRACT_PHOTO

async def collect_photo(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    if update.message.photo or update.message.document:
        context.user_data['lead_data']['Контракт'] = "Файл прикреплен"
        context.user_data['lead_file_id'] = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    else:
        context.user_data['lead_data']['Контракт'] = "Пропущено"

    await update.message.reply_text(get_text(lang, 'questions')['6_CONTACT'], parse_mode='Markdown')
    return CONTACT_INFO

async def skip_photo(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Контракт'] = "Пропущено"
    await query.edit_message_text(get_text(lang, 'questions')['6_CONTACT'], parse_mode='Markdown')
    return CONTACT_INFO

async def send_lead(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Контакт'] = update.message.text
    user = update.effective_user

    lead_text = f"🔔 **НОВЫЙ ЛИД** 🔔\n\n**Клиент:** @{user.username or 'нет'} (ID: `{user.id}`)\n"
    for k, v in context.user_data['lead_data'].items():
        lead_text += f"**{k}:** {v}\n"

    try:
        await context.bot.send_message(chat_id=CHAT_ID_CONSULTANT, text=lead_text, parse_mode='Markdown')
        file_id = context.user_data.get('lead_file_id')
        if file_id:
            try:
                await context.bot.send_photo(chat_id=CHAT_ID_CONSULTANT, photo=file_id)
            except Exception:
                await context.bot.send_document(chat_id=CHAT_ID_CONSULTANT, document=file_id)
    except Exception as e:
        logger.error(f"Ошибка отправки лида: {e}")

    await update.message.reply_text(get_text(lang, 'lead_thanks'), reply_markup=build_menu(lang), parse_mode='Markdown')
    return MAIN_MENU

async def calculate_economy_prompt(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(get_text(lang, 'calc_prompt'), parse_mode='Markdown')
    return CALCULATE_INPUT

async def calculate_economy(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    try:
        cost = float(update.message.text.replace(',', '.'))
        res = f"💰 **Экономия:** примерно **{(cost * 0.2):.2f} €** в месяц!"
    except ValueError:
        res = "Пожалуйста, введите корректное число."

    await update.message.reply_text(res, reply_markup=build_menu(lang), parse_mode='Markdown')
    return MAIN_MENU

async def show_tips(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(get_text(lang, 'tips_content'), reply_markup=build_menu(lang), parse_mode='Markdown')
    return MAIN_MENU

async def show_reviews(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(get_text(lang, 'reviews_content'), reply_markup=build_menu(lang), parse_mode='Markdown')
    return MAIN_MENU

async def show_contact_menu(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    keyboard = [[InlineKeyboardButton("💬 Написать Николаю", url=f"https://t.me/{TELEGRAM_USERNAME.lstrip('@')}")]]
    await update.message.reply_text(get_text(lang, 'contact_menu_text'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return MAIN_MENU

async def cancel(update: Update, context):
    return MAIN_MENU

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(set_language, pattern='^lang_'),
        ],
        states={
            LANGUAGE_SELECT: [CallbackQueryHandler(set_language, pattern='^lang_')],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice),
                CallbackQueryHandler(ask_name, pattern='^start_lead$'),
            ],
            START_CHECK: [CallbackQueryHandler(ask_name, pattern='^start_lead$')],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)],
            CITY_PLZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_city_plz)],
            PROVIDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_provider)],
            CONSUMPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_consumption)],
            CONTRACT_PHOTO: [
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, collect_photo),
                CallbackQueryHandler(skip_photo, pattern='^skip_photo$'),
            ],
            CONTACT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_lead)],
            CALCULATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_economy)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

import logging
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен!")
CHAT_ID_CONSULTANT = 773441776
TELEGRAM_USERNAME = "@nikolajnujkinfit"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

LANGUAGE_SELECT, MAIN_MENU, START_CHECK, NAME, CITY_PLZ, PROVIDER, CONSUMPTION, CONTRACT_PHOTO, CONTACT_INFO, CALCULATE_INPUT = range(10)

TEXTS = {
    'start': {
        'RU': "Привет! Меня зовут **Nikolaj Nujkin** — энергетический консультант. Я помогу тебе проверить твой контракт и сэкономить.\n\nВыбери язык:",
        'DE': "Hallo! Ich heiße **Nikolaj Nujkin** — Energieberater. Bitte wählen Sie die Sprache:",
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
        'RU': "**Экспертная оценка.** Бесплатная проверка твоего контракта позволит точно узнать, переплачиваешь ли ты за электроэнергию или газ.",
        'DE': "**Expertenschätzung.** Kostenlose Vertragsprüfung.",
    },
    'check_start_button': {'RU': "Начать проверку 🚀", 'DE': "Prüfung starten 🚀"},
    'q_name': {'RU': "Как тебя зовут?", 'DE': "Wie heißen Sie?"},
    'q_city': {'RU': "В каком городе/PLZ ты живёшь?", 'DE': "In welcher Stadt/PLZ wohnen Sie?"},
    'q_provider': {'RU': "Кто твой текущий поставщик энергии?", 'DE': "Wer ist Ihr aktueller Energieanbieter?"},
    'q_consumption': {'RU': "Сколько энергии ты потребляешь в год (в кВт⋅ч)? (Укажи число)", 'DE': "Wie hoch ist Ihr Verbrauch pro Jahr (in kWh)?"},
    'q_photo': {'RU': "Пришли фото контракта или PDF. Если не хочешь, просто нажми кнопку ниже.", 'DE': "Senden Sie ein Foto oder PDF Ihres Vertrags."},
    'q_contact': {'RU': "Укажи номер телефона или Telegram, чтобы я лично прислал результаты.", 'DE': "Geben Sie Ihre Telefonnummer oder Telegram an."},
    'skip_photo_button': {'RU': "Пропустить ➡️", 'DE': "Überspringen ➡️"},
    'lead_thanks': {
        'RU': "**🚀 Данные приняты!** Я лично проанализирую твой контракт и свяжусь с тобой в течение 24 часов.",
        'DE': "**🚀 Daten erhalten!** Ich werde Ihren Vertrag analysieren.",
    },
    'tips_content': {
        'RU': "💡 **Советы по экономии:**\n1. Выключайте приборы полностью.\n2. Используйте LED-лампы.",
        'DE': "💡 **Tipps:** Geräte ausschalten, LED nutzen.",
    },
    'calc_prompt': {
        'RU': "**💰 Введи текущие расходы в месяц (в евро, только число):**",
        'DE': "**💰 Monatliche Kosten in Euro eingeben:**",
    },
    'contact_menu_text': {
        'RU': "**Связаться с Николаем:** Напишите мне прямо в Telegram.",
        'DE': "**Kontakt:** Schreiben Sie mir auf Telegram.",
    },
    'reviews_content': {
        'RU': "⭐ **Отзывы клиентов:** Экономия до 30%!",
        'DE': "⭐ **Kundenbewertungen:** Bis zu 30% sparen!",
    },
}

def get_text(lang, key):
    return TEXTS.get(key, {}).get(lang, 'Text error')

def build_menu(lang):
    buttons = TEXTS['menu_buttons'][lang]
    return ReplyKeyboardMarkup([
        [buttons['CHECK']],
        [buttons['CALC'], buttons['TIPS']],
        [buttons['REVIEW'], buttons['CONTACT']]
    ], resize_keyboard=True)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), HealthHandler).serve_forever()

async def start(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text(
        TEXTS['start']['RU'] + "\n\n" + TEXTS['start']['DE'],
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_RU'),
             InlineKeyboardButton("🇩🇪 Deutsch", callback_data='lang_DE')]
        ]),
        parse_mode='Markdown'
    )
    return LANGUAGE_SELECT

async def set_language(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang
    await query.message.reply_text(get_text(lang, 'main_menu'), reply_markup=build_menu(lang), parse_mode='Markdown')
    return MAIN_MENU

async def handle_menu_choice(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text
    if "Проверить" in text or "prüfen" in text:
        return await start_contract_check(update, context)
    elif "Рассчитать" in text or "berechnen" in text:
        return await calculate_economy_prompt(update, context)
    elif "Советы" in text or "Tipps" in text:
        return await show_tips(update, context)
    elif "Отзывы" in text or "Bewertungen" in text:
        return await show_reviews(update, context)
    elif "Связаться" in text or "Kontakt" in text:
        return await show_contact_menu(update, context)
    else:
        await update.message.reply_text(get_text(lang, 'main_menu'), reply_markup=build_menu(lang), parse_mode='Markdown')
        return MAIN_MENU

async def start_contract_check(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data'] = {}
    await update.message.reply_text(
        get_text(lang, 'check_start'),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text(lang, 'check_start_button'), callback_data='start_lead')]]),
        parse_mode='Markdown'
    )
    return START_CHECK

async def ask_name(update: Update, context):
    query = update.callback_query
    lang = context.user_data.get('lang', 'RU')
    if query:
        try: await query.answer()
        except: pass
        await query.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    else:
        await update.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    return NAME

async def collect_name(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Имя'] = update.message.text
    await update.message.reply_text(get_text(lang, 'q_city'), parse_mode='Markdown')
    return CITY_PLZ

async def collect_city_plz(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Город/PLZ'] = update.message.text
    await update.message.reply_text(get_text(lang, 'q_provider'), parse_mode='Markdown')
    return PROVIDER

async def collect_provider(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Поставщик'] = update.message.text
    await update.message.reply_text(get_text(lang, 'q_consumption'), parse_mode='Markdown')
    return CONSUMPTION

async def collect_consumption(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text.replace(',', '.')
    if not re.match(r'^\d+(\.\d+)?$', text):
        await update.message.reply_text("❌ Укажите число в кВт⋅ч.", parse_mode='Markdown')
        return CONSUMPTION
    context.user_data['lead_data']['Потребление'] = text
    await update.message.reply_text(
        get_text(lang, 'q_photo'),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text(lang, 'skip_photo_button'), callback_data='skip_photo')]]),
        parse_mode='Markdown'
    )
    return CONTRACT_PHOTO

async def collect_photo(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    if update.message.photo or update.message.document:
        context.user_data['lead_data']['Контракт'] = "Файл прикреплен"
        context.user_data['lead_file_id'] = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    else:
        context.user_data['lead_data']['Контракт'] = "Пропущено"
    await update.message.reply_text(get_text(lang, 'q_contact'), parse_mode='Markdown')
    return CONTACT_INFO

async def skip_photo(update: Update, context):
    query = update.callback_query
    if query:
        try: await query.answer()
        except: pass
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Контракт'] = "Пропущено"
    await query.message.reply_text(get_text(lang, 'q_contact'), parse_mode='Markdown')
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
            try: await context.bot.send_photo(chat_id=CHAT_ID_CONSULTANT, photo=file_id)
            except: await context.bot.send_document(chat_id=CHAT_ID_CONSULTANT, document=file_id)
    except Exception as e:
        logger.error(f"Ошибка отправки лида: {e}")
    await update.message.reply_text(get_text(lang, 'lead_thanks'), reply_markup=build_menu(lang), parse_mode='Markdown')
    return ConversationHandler.END

async def calculate_economy_prompt(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(get_text(lang, 'calc_prompt'), parse_mode='Markdown')
    return CALCULATE_INPUT

async def calculate_economy(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    try:
        cost = float(update.message.text.replace(',', '.'))
        res = f"💰 **Экономия:** примерно **{(cost * 0.2):.2f} €** в месяц (до **{(cost * 0.2 * 12):.2f} €** в год)!"
    except ValueError:
        res = "❌ Пожалуйста, введите корректное число в евро."
    await update.message.reply_text(res, reply_markup=build_menu(lang), parse_mode='Markdown')
    return ConversationHandler.END

async def show_tips(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(get_text(lang, 'tips_content'), reply_markup=build_menu(lang), parse_mode='Markdown')
    return ConversationHandler.END

async def show_reviews(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(get_text(lang, 'reviews_content'), reply_markup=build_menu(lang), parse_mode='Markdown')
    return ConversationHandler.END

async def show_contact_menu(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    keyboard = [[InlineKeyboardButton("💬 Написать Николаю", url=f"https://t.me/{TELEGRAM_USERNAME.lstrip('@')}")]]
    await update.message.reply_text(get_text(lang, 'contact_menu_text'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return ConversationHandler.END

def main():
    Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(set_language, pattern='^lang_'),
            CallbackQueryHandler(ask_name, pattern='^start_lead$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice),
        ],
        states={
            LANGUAGE_SELECT: [CallbackQueryHandler(set_language, pattern='^lang_')],
            MAIN_MENU: [
                CallbackQueryHandler(ask_name, pattern='^start_lead$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice),
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
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice)],
        allow_reentry=True
    )
    
    app.add_handler(conv)
    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()

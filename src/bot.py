import logging
import re
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

# Настройка логирования для обоих процессов (GUI и Bot)
logging.basicConfig(
import logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. СТРУКТУРА КОНФИГУРАЦИИ И УПРАВЛЕНИЕ ТЕКСТАМИ
#
# Вся конфигурация бота (токен, ID, тексты) хранится в этой структуре.
# GUI будет напрямую редактировать эту структуру.
# ==============================================================================

# --- СТЕЙТЫ (СОСТОЯНИЯ ДЛЯ ВОРОНКИ) ---
(LANGUAGE_SELECT, MAIN_MENU, START_CHECK, NAME, CITY_PLZ, PROVIDER, CONSUMPTION,
 CONTRACT_PHOTO, CONTACT_INFO, CALCULATE_INPUT, SHOW_TIPS, SHOW_REVIEWS, CONTACT_MENU) = range(13)

BOT_CONFIG = {
    'general': {
        'BOT_TOKEN': "1327283301:AAHKJGjr-QWWvyBMjXCeapICFTf-Clu52gI",
        # ВНИМАНИЕ: Замените '773441776' на ваш реальный числовой Telegram Chat ID.
        'CHAT_ID_CONSULTANT': 773441776, 
        'WHATSAPP_NUMBER': "+4915788348961",
        'TELEGRAM_USERNAME': "@nikolajnujkinfit",
    },
    'texts': {
        'RU': {
            'start': "Привет! Меня зовут **Nikolaj Nujkin** — энергетический консультант с 8-летним опытом. Я помогу тебе проверить твой контракт на электроэнергию или газ и найти способы сэкономить.\n\nВыбери язык:",
            'main_menu': "**Отлично!** Выбери, что ты хочешь сделать прямо сейчас:",
            'check_start': "**Экспертная оценка.** Бесплатная проверка твоего контракта позволит точно узнать, переплачиваешь ли ты за электроэнергию или газ. Я проведу точный расчёт и дам персональные рекомендации — **всё бесплатно** и без обязательств.",
            'check_start_button': "Начать проверку 🚀",
            'skip_photo_button': "Пропустить",
            'lead_thanks': "**🚀 Данные приняты!** Спасибо за информацию. Я лично, как эксперт, проанализирую твой текущий контракт, проведу расчёт потенциальной экономии и дам точные рекомендации.\n\n**Ожидай сообщение от меня в Telegram или WhatsApp** в ближайшие 24 часа. До связи!",
            'tips_content': "💡 **ТОП-3 простых совета от эксперта:** Ты можешь начать экономить уже сейчас, следуя этим простым правилам:\n\n– Выключай приборы полностью, а не оставляй их в режиме ожидания (Standby).\n– Используй современные светодиодные (LED) лампы.\n– Настрой термостат на оптимальную температуру (каждый градус — это +6% к расходу).",
            'reviews_content': "**⭐ Результаты говорят сами за себя.** Клиенты, с которыми я работал, экономят до 30% на счетах за электроэнергию и газ. Вот что они говорят:\n\n> *“Благодаря Николаю мы снизили расходы на газ почти вдвое! Он настоящий эксперт.”*\n> *“Все объяснил понятно, очень доволен! Проверку провёл быстро и с максимальной выгодой.”*\n> *“Уже порекомендовала всем друзьям. Спасибо за ежегодную экономию!”*",
            'calc_prompt': "**💰 Быстрая оценка экономии.** Чтобы примерно оценить твою потенциальную выгоду, введи текущие расходы на электроэнергию/газ в месяц (только число, в евро):",
            'contact_menu_text': "**Давай оформим выгоду.** Если ты готов(а) к реальной экономии, я могу составить персональный энергоплан и помочь оформить контракт с поставщиком. Таким образом, ты будешь экономить каждый месяц без лишних хлопот. Просто напиши мне или выбери удобное время.",
            'menu_buttons': {
                'CHECK': "🔍 Проверить мой контракт", 'CALC': "💰 Рассчитать экономию", 'TIPS': "💡 Советы по экономии энергии",
                'REVIEW': "⭐ Отзывы клиентов", 'CONTACT': "🧑‍💼 Связаться с экспертом",
            },
            'questions': {
                '1_NAME': "Как тебя зовут?", '2_CITY': "В каком городе/PLZ ты живёшь? (Это важно для поиска региональных тарифов).", 
                '3_PROVIDER': "Кто твой текущий поставщик энергии (Strom- und/oder Gasanbieter)?", 
                '4_CONSUMPTION': "Сколько электроэнергии и/или газа ты потребляешь в год (в кВт⋅ч)? (Укажи число).", 
                '5_PHOTO': "Для максимально точного анализа пришли фото контракта или PDF. Если не хочешь, просто отправь «Нет» или нажми кнопку ниже.", 
                '6_CONTACT': "Отлично, почти готово! Укажи номер телефона или Telegram-логин, чтобы я лично (Nikolaj) мог прислать тебе результаты проверки и персональные рекомендации.",
            },
        },
        'DE': {
            'start': "Hallo! Ich heiße **Nikolaj Nujkin** — Energieberater mit 8 Jahren Erfahrung. Ich helfe Ihnen, Ihren Strom- oder Gasvertrag zu überprüfen und Einsparmöglichkeiten zu finden.\n\nBitte wähle die Sprache:",
            'main_menu': "**Perfekt!** Wählen Sie, was Sie tun möchten:",
            'check_start': "**Expertenschätzung.** Eine kostenlose Vertragsprüfung zeigt Ihnen genau, ob Sie zu viel für Strom oder Gas bezahlen. Ich werde eine genaue Berechnung und persönliche Empfehlungen geben – **alles kostenlos** und unverbindlich.",
            'check_start_button': "Prüfung starten 🚀",
            'skip_photo_button': "Überspringen",
            'lead_thanks': "**🚀 Daten erhalten!** Vielen Dank für die Informationen. Ich werde Ihren aktuellen Vertrag persönlich als Experte analysieren, die potenziellen Einsparungen berechnen und Ihnen genaue Empfehlungen geben.\n\n**Sie erhalten in Kürze (innerhalb von 24 Stunden) eine persönliche Nachricht von mir (Nikolaj) über Telegram oder WhatsApp.** Bis bald!",
            'tips_content': "💡 **TOP-3 einfache Expertentipps:** Sie können sofort mit dem Sparen beginnen, indem Sie diese einfachen Regeln befolgen:\n\n– Geräte vollständig ausschalten, nicht im Standby-Modus lassen.\n– Verwenden Sie moderne LED-Lampen.\n– Stellen Sie den Thermostat auf die optimale Temperatur ein (jedes Grad ist eine Erhöhung des Verbrauchs um 6%).",
            'reviews_content': "**⭐ Die Ergebnisse sprechen für sich.** Kunden, mit denen ich zusammengearbeitet habe, sparen bis zu 30 % bei ihren Strom- und Gasrechnungen. Hier ist, was sie sagen:\n\n> *„Dank Nikolaj haben wir unsere Gasrechnung fast halbiert! Er ist ein echter Experte.”*\n> *„Alles klar erklärt, sehr zufrieden! Die Prüfung wurde schnell und mit maximalem Nutzen durchgeführt.”*\n> *„Ich habe es bereits allen meinen Freunden empfohlen. Vielen Dank für die jährlichen Einsparungen!”*",
            'calc_prompt': "**💰 Schnelle Einsparungsschätzung.** Geben Sie Ihre aktuellen monatlichen Strom-/Gaszahlungen (nur die Zahl, in Euro) ein, um Ihre möglichen Einsparungen zu berechnen:",
            'contact_menu_text': "**Lassen Sie uns Ihre Vorteile sichern.** Wenn Sie bereit für echte Einsparungen sind, kann ich einen persönlichen Energieplan erstellen und Ihnen helfen, einen Vertrag beim besten Anbieter abzuschließen. So sparen Sie jeden Monat ohne unnötigen Aufwand. Schreiben Sie mir einfach oder wählen Sie einen passenden Termin.",
            'menu_buttons': {
                'CHECK': "🔍 Vertrag prüfen", 'CALC': "💰 Einsparung berechnen", 'TIPS': "💡 Energiespartipps",
                'REVIEW': "⭐ Kundenbewertungen", 'CONTACT': "🧑‍💼 Kontakt zum Experten",
            },
            'questions': {
                '1_NAME': "Wie heißen Sie?", '2_CITY': "In welcher Stadt/PLZ wohnen Sie? (Dies ist wichtig für die Suche nach regionalen Tarifen).", 
                '3_PROVIDER': "Wer ist Ihr aktueller Energieanbieter (Strom- und/oder Gasanbieter)?", 
                '4_CONSUMPTION': "Wie hoch ist Ihr Strom- und/oder Gasverbrauch pro Jahr (in kWh)? (Geben Sie die Zahl ein).", 
                '5_PHOTO': "Für eine möglichst genaue Analyse senden Sie uns bitte ein Foto oder PDF Ihres Vertrags. Wenn Sie dies nicht möchten, senden Sie einfach «Nein» oder klicken Sie auf die Schaltfläche unten.", 
                '6_CONTACT': "Wunderbar, fast fertig! Bitte geben Sie Ihre Telefonnummer oder Ihren Telegram-Benutzernamen an, damit ich (Nikolaj) Ihnen die Prüfungsergebnisse und persönlichen Empfehlungen zusenden kann.",
            },
        }
    }
}

# --- ХЕЛПЕРЫ ДЛЯ БОТА ---

def get_text(lang, key):
    """Извлекает текст из глобальной конфигурации."""
    # Обработка вложенных ключей для вопросов
    if key.startswith('questions.'):
        q_key = key.split('.')[1]
        return BOT_CONFIG['texts'][lang]['questions'].get(q_key, 'Text error')
    
    # Обработка вложенных ключей для кнопок
    if key.startswith('menu_buttons.'):
        b_key = key.split('.')[1]
        return BOT_CONFIG['texts'][lang]['menu_buttons'].get(b_key, 'Text error')

    return BOT_CONFIG['texts'].get(lang, {}).get(key, 'Text error')

def get_contact_link(key):
    """Извлекает ссылку для контактов."""
    tg_user = BOT_CONFIG['general']['TELEGRAM_USERNAME'].lstrip('@')
    # Это вспомогательные ссылки, нередактируемые в GUI
    links = {
        'TELEGRAM': f"t.me/{tg_user}",
        'APPOINTMENT': "https://calendly.com/your-scheduling-link", # Placeholder
    }
    return links.get(key)

def build_menu(lang):
    """Собирает главное меню ReplyKeyboard."""
    buttons_data = BOT_CONFIG['texts'][lang]['menu_buttons']
    keyboard = [
        [buttons_data['CHECK']],
        [buttons_data['CALC'], buttons_data['TIPS']],
        [buttons_data['REVIEW'], buttons_data['CONTACT']]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def calculate_result_text(lang, cost):
    """Генерирует текст результата расчета экономии."""
    if lang == 'RU':
        return f"**Примерный расчёт:** С моей помощью клиенты обычно экономят **15-30%** от текущих расходов. При твоих расходах в **{cost:.2f} €** в месяц, твоя потенциальная экономия составит **{(cost * 0.15):.2f} €** - **{(cost * 0.25):.2f} €** в месяц или до **{(cost * 0.25 * 12):.2f} €** в год! Но для точного расчёта нужна бесплатная проверка контракта."
    else: # DE
        return f"**Beispielrechnung:** Mit meiner Hilfe sparen Kunden typischerweise **15-30%** der aktuellen Kosten. Bei Ihren Ausgaben von **{cost:.2f} €** pro Monat betragen Ihre potenziellen Einsparungen **{(cost * 0.15):.2f} €** - **{(cost * 0.25):.2f} €** pro Monat oder bis zu **{(cost * 0.25 * 12):.2f} €** pro Jahr! Aber für eine genaue Berechnung ist eine kostenlose Vertragsprüfung erforderlich."

# ==============================================================================
# 2. ЛОГИКА ТЕЛЕГРАМ-БОТА (МОДИФИЦИРОВАННАЯ)
# ==============================================================================

# Application instance placeholder
application = None 
bot_thread = None

async def start(update: Update, context):
    """Начало диалога и выбор языка."""
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_RU'),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data='lang_DE'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_text('RU', 'start') + "\n\n" + get_text('DE', 'start'),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return LANGUAGE_SELECT

async def set_language(update: Update, context):
    """Устанавливает язык и переходит в главное меню."""
    query = update.callback_query
    await query.answer()

    lang = query.data.split('_')[1]
    context.user_data['lang'] = lang

    await show_main_menu(update, context, message_source=query)
    return MAIN_MENU

async def show_main_menu(update: Update, context, message_source=None):
    """Отправляет главное меню."""
    lang = context.user_data.get('lang', 'RU')
    menu_text = get_text(lang, 'main_menu')
    reply_markup = build_menu(lang)
    
    if message_source and isinstance(message_source, Update.CallbackQuery):
        await message_source.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.message:
        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # Fallback
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=menu_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    return MAIN_MENU

async def handle_menu_choice(update: Update, context):
    """Маршрутизация по выбору главного меню."""
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text
    
    # Сопоставление текста кнопки с ключом действия
    menu_actions = {v: k for k, v in BOT_CONFIG['texts'][lang]['menu_buttons'].items()}
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
        await update.message.reply_text(get_text(lang, 'main_menu'), reply_markup=build_menu(lang), parse_mode='Markdown')
        return MAIN_MENU

# --- ВОРОНКА (Сбор Лида) ---

async def start_contract_check(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data'] = {}

    check_text = get_text(lang, 'check_start')
    
    keyboard = [[InlineKeyboardButton(get_text(lang, 'check_start_button'), callback_data='start_lead')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        check_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return START_CHECK

async def ask_name(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'RU')
    
    await query.edit_message_text(
        get_text(lang, 'questions.1_NAME'),
        reply_markup=None,
        parse_mode='Markdown'
    )
    return NAME

async def collect_name(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Name'] = update.message.text
    await update.message.reply_text(get_text(lang, 'questions.2_CITY'), parse_mode='Markdown')
    return CITY_PLZ

async def collect_city_plz(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['City/PLZ'] = update.message.text
    await update.message.reply_text(get_text(lang, 'questions.3_PROVIDER'), parse_mode='Markdown')
    return PROVIDER

async def collect_provider(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Provider'] = update.message.text
    await update.message.reply_text(get_text(lang, 'questions.4_CONSUMPTION'), parse_mode='Markdown')
    return CONSUMPTION

async def collect_consumption(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text.replace(',', '.')

    if not re.match(r'^\d+(\.\d+)?$', text):
        await update.message.reply_text(
            f"❌ {'Пожалуйста, введи только число (в кВт⋅ч).' if lang == 'RU' else 'Bitte geben Sie nur eine Zahl (in kWh) ein.'}", 
            parse_mode='Markdown'
        )
        return CONSUMPTION
    
    context.user_data['lead_data']['Consumption (kWh)'] = text
    
    keyboard = [[InlineKeyboardButton(get_text(lang, 'skip_photo_button'), callback_data='skip_photo')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_text(lang, 'questions.5_PHOTO'),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return CONTRACT_PHOTO

async def collect_photo(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    
    if update.message.photo or update.message.document:
        file_type = 'Photo' if update.message.photo else 'Document (PDF/other)'
        context.user_data['lead_data']['Contract Photo/File'] = f"{file_type} attached in the previous message."
        context.user_data['lead_file_id'] = (
            update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
        )
    elif update.message.text and update.message.text.lower() in ('нет', 'nein', get_text('RU', 'skip_photo_button').lower(), get_text('DE', 'skip_photo_button').lower()):
        context.user_data['lead_data']['Contract Photo/File'] = 'Skipped by user (Text/Button)'
    else:
        keyboard = [[InlineKeyboardButton(get_text(lang, 'skip_photo_button'), callback_data='skip_photo')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"❌ {'Пожалуйста, пришлите фото/PDF или нажмите «Пропустить».' if lang == 'RU' else 'Bitte senden Sie ein Foto/PDF oder klicken Sie auf «Überspringen».'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CONTRACT_PHOTO

    await update.message.reply_text(get_text(lang, 'questions.6_CONTACT'), parse_mode='Markdown')
    return CONTACT_INFO

async def skip_photo(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Contract Photo/File'] = 'Skipped by user (Button)'
    
    await query.edit_message_text(get_text(lang, 'questions.6_CONTACT'), reply_markup=None, parse_mode='Markdown')
    return CONTACT_INFO

async def send_lead(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    context.user_data['lead_data']['Contact Info'] = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    lead_info = context.user_data['lead_data']
    
    # 1. Форматирование уведомлений
    telegram_notification = f"🔔 **НОВЫЙ ЛИД (Telegram)** 🔔\n\n"
    telegram_notification += f"**Пользователь:** @{username} (ID: `{user_id}`)\n"
    telegram_notification += f"**Язык:** {lang}\n"
    telegram_notification += "--- ДАННЫЕ ЛИДА ---\n"
    for key, value in lead_info.items():
        telegram_notification += f"**{key}:** {value}\n"
    
    whatsapp_notification = (
        f"🤖 **WhatsApp-УВЕДОМЛЕНИЕ (Simulated via Telegram)** 🤖\n\n"
        f"**Новый запрос на проверку контракта от клиента:** {lead_info.get('Name', 'N/A')}\n"
        f"**Контакт (WhatsApp):** {lead_info.get('Contact Info', 'N/A')}\n"
        f"**Ссылка на чат:** tg://user?id={user_id}\n"
        f"--- Полные данные отправлены отдельным сообщением. ---"
    )

    # 2. Отправка уведомлений консультанту
    consultant_chat_id = BOT_CONFIG['general']['CHAT_ID_CONSULTANT']
    if consultant_chat_id != 000000000:
        try:
            # A. Полные данные в Telegram
            await context.bot.send_message(chat_id=consultant_chat_id, text=telegram_notification, parse_mode='Markdown')
            
            # B. Файл
            file_id = context.user_data.get('lead_file_id')
            if file_id:
                await context.bot.send_message(chat_id=consultant_chat_id, text="📄 **Приложенный файл/фото контракта:**", parse_mode='Markdown')
                try:
                    await context.bot.send_photo(chat_id=consultant_chat_id, photo=file_id)
                except Exception:
                    await context.bot.send_document(chat_id=consultant_chat_id, document=file_id)
            
            # C. Симулированное WhatsApp-уведомление
            await context.bot.send_message(chat_id=consultant_chat_id, text=whatsapp_notification, parse_mode='Markdown')
            logger.info(f"Lead from user {user_id} sent to consultant.")
        except Exception as e:
            logger.error(f"Failed to send lead to consultant {consultant_chat_id}: {e}")
            await update.message.reply_text(f"Произошла ошибка при отправке данных эксперту: {e}", parse_mode='Markdown')
    else:
        logger.warning("Consultant CHAT_ID is not set. Lead not sent.")
        await update.message.reply_text("ВНИМАНИЕ: ID консультанта не настроен. Лид не отправлен, но данные приняты.", parse_mode='Markdown')


    # 3. Подтверждение пользователю и возврат в главное меню
    await update.message.reply_text(
        get_text(lang, 'lead_thanks'), 
        reply_markup=build_menu(lang),
        parse_mode='Markdown'
    )
    return MAIN_MENU

# --- Расчёт, Советы, Отзывы, Контакт ---

async def calculate_economy_prompt(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(
        get_text(lang, 'calc_prompt'),
        reply_markup=None,
        parse_mode='Markdown'
    )
    return CALCULATE_INPUT

async def calculate_economy(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    text = update.message.text.replace(',', '.')

    try:
        cost = float(text)
        if cost <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text(
            f"❌ {'Пожалуйста, введи корректную сумму.' if lang == 'RU' else 'Bitte geben Sie einen korrekten Betrag ein.'} " + get_text(lang, 'calc_prompt'),
            parse_mode='Markdown'
        )
        return CALCULATE_INPUT
    
    result_text = calculate_result_text(lang, cost)
    
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'check_start_button'), callback_data='start_lead')],
        [InlineKeyboardButton(get_text(lang, 'menu_buttons.CONTACT'), url=get_contact_link('TELEGRAM'))],
        [InlineKeyboardButton(get_text(lang, 'menu_buttons.CHECK'), callback_data='main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        result_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def show_tips(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    
    keyboard = [[InlineKeyboardButton(get_text(lang, 'menu_buttons.CHECK'), callback_data='start_lead')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_text(lang, 'tips_content'), 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def show_reviews(update: Update, context):
    lang = context.user_data.get('lang', 'RU')

    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'check_start_button'), callback_data='start_lead')],
        [InlineKeyboardButton(get_text(lang, 'menu_buttons.CONTACT'), url=get_contact_link('TELEGRAM'))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_text(lang, 'reviews_content'),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU 

async def show_contact_menu(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'menu_buttons.CONTACT'), url=get_contact_link('TELEGRAM'))],
        [InlineKeyboardButton(f"🗓 {'Записаться' if lang == 'RU' else 'Termin wählen'}", url=get_contact_link('APPOINTMENT'))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_text(lang, 'contact_menu_text'),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def handle_callback_main_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_lead':
        return await ask_name(update, context) 
    
    # Для всех остальных случаев, возвращаем в главное меню
    return await show_main_menu(update, context, message_source=query)

async def cancel(update: Update, context):
    lang = context.user_data.get('lang', 'RU')
    await update.message.reply_text(
        f"✅ {'Воронка отменена. Возвращаемся в главное меню.' if lang == 'RU' else 'Trichter abgebrochen. Zurück zum Hauptmenü.'}", 
        reply_markup=build_menu(lang)
    )
    return MAIN_MENU

# --- ОБРАБОТЧИК ОШИБОК (ЧТОБЫ БОТ НЕ ПАДАЛ) ---
async def global_error_handler(update: object, context) -> None:
    """Логирует ошибки и предотвращает падение бота."""
    logger.error("Произошла ошибка при обработке обновления:", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Произошла временная ошибка при обработке запроса. Попробуйте еще раз или вернитесь в /start."
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {e}")


def run_bot():
    """Главная функция для запуска бота в отдельном потоке."""
    global application
    token = BOT_CONFIG['general']['BOT_TOKEN']
    
    if application and application.running:
        logger.info("Бот уже запущен.")
        return

    try:
        # 1. Создание Application
        application = Application.builder().token(token).build()

        # 2. Настройка хендлеров
        lead_conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(handle_callback_main_menu, pattern='^start_lead$'),
                MessageHandler(
                    filters.Regex(get_text('RU', 'menu_buttons.CHECK')) | filters.Regex(get_text('DE', 'menu_buttons.CHECK')), 
                    start_contract_check
                ),
            ],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)],
                CITY_PLZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_city_plz)],
                PROVIDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_provider)],
                CONSUMPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_consumption)],
                CONTRACT_PHOTO: [
                    MessageHandler(filters.PHOTO | filters.Document.ALL, collect_photo),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, collect_photo),
                    CallbackQueryHandler(skip_photo, pattern='^skip_photo$')
                ],
                CONTACT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_lead)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            map_to_parent={MAIN_MENU: MAIN_MENU, START_CHECK: MAIN_MENU},
        )
        
        # Общие хендлеры
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
        application.add_handler(CallbackQueryHandler(handle_callback_main_menu, pattern='^main$|^start_lead$'))
        
        # Хендлер для Расчета
        application.add_handler(ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(get_text('RU', 'menu_buttons.CALC')) | filters.Regex(get_text('DE', 'menu_buttons.CALC')), calculate_economy_prompt)],
            states={
                CALCULATE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_economy)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            map_to_parent={MAIN_MENU: MAIN_MENU},
        ))

        # Хендлеры для кнопок главного меню
        application.add_handler(MessageHandler(
            filters.Regex(get_text('RU', 'menu_buttons.TIPS')) | filters.Regex(get_text('DE', 'menu_buttons.TIPS')), 
            show_tips
        ))
        application.add_handler(MessageHandler(
            filters.Regex(get_text('RU', 'menu_buttons.REVIEW')) | filters.Regex(get_text('DE', 'menu_buttons.REVIEW')), 
            show_reviews
        ))
        application.add_handler(MessageHandler(
            filters.Regex(get_text('RU', 'menu_buttons.CONTACT')) | filters.Regex(get_text('DE', 'menu_buttons.CONTACT')), 
            show_contact_menu
        ))

        # Важно: Основной хендлер должен быть добавлен после всех regex-хендлеров
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice))
        
        # Хендлер воронки
        application.add_handler(lead_conv_handler)
        
        # ДОБАВЛЕНИЕ ОБРАБОТЧИКА ОШИБОК
        application.add_error_handler(global_error_handler)
        
        # 3. Запуск
        logger.info("Telegram Bot запущен и слушает обновления...")
        application.run_polling(allowed_updates=Update.ALL_TYPES, stop_signals=None)

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        messagebox.showerror("Ошибка Бота", f"Не удалось запустить бот. Проверьте токен или соединение: {e}")


def stop_bot():
    """Останавливает бота."""
    global application, bot_thread
    if application and application.running:
        application.stop()
        if bot_thread and bot_thread.is_alive():
            # Ждем завершения потока
            bot_thread.join(timeout=5) 
        logger.info("Telegram Bot остановлен.")
        return True
    return False


def start_bot_thread(status_label):
    """Запускает бота в отдельном потоке."""
    global bot_thread, application

    # Проверка обязательных полей
    if BOT_CONFIG['general']['CHAT_ID_CONSULTANT'] == 000000000:
        messagebox.showwarning("ВНИМАНИЕ", "ID консультанта не настроен. Бот запустится, но не сможет отправлять лиды. Пожалуйста, укажите CHAT ID.")

    if bot_thread and bot_thread.is_alive():
        messagebox.showinfo("Статус", "Бот уже запущен.")
        return

    # Убеждаемся, что бот остановлен перед запуском нового потока
    if application and application.running:
        stop_bot()

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    status_label.config(text="СТАТУС: БОТ ЗАПУЩЕН", fg="green")
    logger.info("Поток бота запущен.")

def stop_bot_thread(status_label):
    """Останавливает поток бота."""
    if stop_bot():
        status_label.config(text="СТАТУС: БОТ ОСТАНОВЛЕН", fg="red")
        messagebox.showinfo("Статус", "Бот успешно остановлен.")
    else:
        messagebox.showinfo("Статус", "Бот не был запущен.")
        
# ==============================================================================
# 3. ГРАФИЧЕСКИЙ ИНТЕРФЕЙС (TKINTER)
# ==============================================================================

class BotManagerGUI:
    def __init__(self, master):
        self.master = master
        master.title("Менеджер Энерго-Бота")

        # --- Переменные для полей ввода ---
        self.entry_vars = {}
        self.textarea_widgets = {}

        # --- Общие настройки (General Settings) ---
        general_frame = ttk.LabelFrame(master, text="Общие Настройки и Управление")
        general_frame.pack(padx=10, pady=10, fill="x")

        # Чат ID и Контакты
        self.add_general_settings(general_frame)
        
        # Управление ботом
        control_frame = ttk.Frame(master)
        control_frame.pack(padx=10, pady=(0, 10), fill="x")
        
        ttk.Button(control_frame, text="ЗАПУСТИТЬ БОТ", command=lambda: start_bot_thread(self.status_label)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="ОСТАНОВИТЬ БОТ", command=lambda: stop_bot_thread(self.status_label)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(control_frame, text="СОХРАНИТЬ КОНФИГУРАЦИЮ", command=self.save_config).pack(side=tk.RIGHT, padx=5, pady=5)
        
        self.status_label = ttk.Label(control_frame, text="СТАТУС: ОСТАНОВЛЕН", foreground="red", font=('Helvetica', 10, 'bold'))
        self.status_label.pack(side=tk.LEFT, padx=15)
        
        # --- Тексты (Notebook) ---
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(padx=10, pady=5, fill="both", expand=True)

        self.create_language_tab("RU", "Русский (RU)")
        self.create_language_tab("DE", "Немецкий (DE)")
        
        self.load_config_to_gui()

    def add_general_settings(self, parent):
        """Создает поля ввода для общих настроек (токен, ID)."""
        settings = [
            ('BOT_TOKEN', 'Токен Бота (ВНИМАНИЕ, не менять)'),
            ('CHAT_ID_CONSULTANT', 'CHAT ID Консультанта (Для лидов)'),
            ('TELEGRAM_USERNAME', 'Telegram Логин (@nikolajnujkinfit)'),
            ('WHATSAPP_NUMBER', 'WhatsApp Номер'),
        ]
        
        for i, (key, label_text) in enumerate(settings):
            ttk.Label(parent, text=label_text + ":", width=35).grid(row=i, column=0, sticky="w", padx=5, pady=2)
            
            var = tk.StringVar(parent, value=str(BOT_CONFIG['general'].get(key, '')))
            entry = ttk.Entry(parent, textvariable=var, width=60)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            self.entry_vars[key] = var
            
            # Токен делаем нередактируемым (ReadOnly)
            if key == 'BOT_TOKEN':
                entry.config(state='readonly')

    def create_language_tab(self, lang_code, tab_title):
        """Создает вкладку с полями для текстов на определенном языке."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text=tab_title)
        
        canvas = tk.Canvas(frame)
        canvas.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion = canvas.bbox("all")))

        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw", width=inner_frame.winfo_screenwidth()) # Привязка ширины
        
        self.add_text_fields(inner_frame, lang_code)
        
    def add_text_fields(self, parent, lang_code):
        """Добавляет текстовые области для редактирования сообщений."""
        texts = BOT_CONFIG['texts'][lang_code]
        row = 0
        
        # Основные тексты
        for key, value in texts.items():
            if isinstance(value, str):
                ttk.Label(parent, text=f"[{key}] {lang_code} (Основное сообщение):", font=('Helvetica', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10, 0))
                row += 1
                
                textarea = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=4, width=80, font=('TkDefaultFont', 10))
                textarea.grid(row=row, column=0, sticky="ew", padx=5, pady=2, columnspan=2)
                self.textarea_widgets[f'{lang_code}_{key}'] = textarea
                row += 1
        
        # Кнопки (отдельный раздел)
        ttk.Label(parent, text=f"\n[menu_buttons] {lang_code} (Тексты кнопок):", font=('Helvetica', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10, 0))
        row += 1
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        row += 1
        
        for b_key, b_text in texts['menu_buttons'].items():
            ttk.Label(button_frame, text=f"Кнопка '{b_key}':").pack(side=tk.LEFT, padx=(10, 2), pady=2)
            var = tk.StringVar(button_frame)
            ttk.Entry(button_frame, textvariable=var, width=20).pack(side=tk.LEFT, padx=(0, 10), pady=2)
            self.entry_vars[f'{lang_code}_menu_buttons_{b_key}'] = var

        # Вопросы (отдельный раздел)
        ttk.Label(parent, text=f"\n[questions] {lang_code} (Тексты вопросов воронки):", font=('Helvetica', 10, 'bold')).grid(row=row, column=0, sticky="w", padx=5, pady=(10, 0))
        row += 1
        
        for q_key, q_text in texts['questions'].items():
            ttk.Label(parent, text=f"Вопрос '{q_key}':").grid(row=row, column=0, sticky="w", padx=5, pady=2)
            row += 1
            
            textarea = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=2, width=80, font=('TkDefaultFont', 10))
            textarea.grid(row=row, column=0, sticky="ew", padx=5, pady=2, columnspan=2)
            self.textarea_widgets[f'{lang_code}_questions_{q_key}'] = textarea
            row += 1

    def load_config_to_gui(self):
        """Загружает данные из BOT_CONFIG в GUI."""
        # 1. Общие настройки
        for key, var in self.entry_vars.items():
            if key in BOT_CONFIG['general']:
                var.set(str(BOT_CONFIG['general'][key]))
        
        # 2. Тексты и вопросы
        for lang_code in ['RU', 'DE']:
            texts = BOT_CONFIG['texts'][lang_code]
            
            # Основные тексты
            for key in texts.keys():
                if isinstance(texts[key], str):
                    widget_key = f'{lang_code}_{key}'
                    if widget_key in self.textarea_widgets:
                        self.textarea_widgets[widget_key].delete('1.0', tk.END)
                        self.textarea_widgets[widget_key].insert(tk.END, texts[key])
                        
            # Кнопки
            for b_key, b_text in texts['menu_buttons'].items():
                var_key = f'{lang_code}_menu_buttons_{b_key}'
                if var_key in self.entry_vars:
                    self.entry_vars[var_key].set(b_text)

            # Вопросы
            for q_key, q_text in texts['questions'].items():
                widget_key = f'{lang_code}_questions_{q_key}'
                if widget_key in self.textarea_widgets:
                    self.textarea_widgets[widget_key].delete('1.0', tk.END)
                    self.textarea_widgets[widget_key].insert(tk.END, q_text)

    def save_config(self):
        """Сохраняет данные из GUI обратно в BOT_CONFIG."""
        
        # 1. Общие настройки
        try:
            # Чат ID должен быть числом
            chat_id = int(self.entry_vars['CHAT_ID_CONSULTANT'].get())
            if chat_id < 0: raise ValueError
            BOT_CONFIG['general']['CHAT_ID_CONSULTANT'] = chat_id
        except ValueError:
            messagebox.showerror("Ошибка Сохранения", "CHAT ID Консультанта должен быть корректным числом.")
            return

        BOT_CONFIG['general']['TELEGRAM_USERNAME'] = self.entry_vars['TELEGRAM_USERNAME'].get()
        BOT_CONFIG['general']['WHATSAPP_NUMBER'] = self.entry_vars['WHATSAPP_NUMBER'].get()

        # 2. Тексты и вопросы
        for lang_code in ['RU', 'DE']:
            # Основные тексты
            for key in BOT_CONFIG['texts'][lang_code].keys():
                if isinstance(BOT_CONFIG['texts'][lang_code][key], str):
                    widget_key = f'{lang_code}_{key}'
                    if widget_key in self.textarea_widgets:
                        text_content = self.textarea_widgets[widget_key].get('1.0', tk.END).strip()
                        BOT_CONFIG['texts'][lang_code][key] = text_content
                        
            # Кнопки
            for b_key in BOT_CONFIG['texts'][lang_code]['menu_buttons'].keys():
                var_key = f'{lang_code}_menu_buttons_{b_key}'
                if var_key in self.entry_vars:
                    BOT_CONFIG['texts'][lang_code]['menu_buttons'][b_key] = self.entry_vars[var_key].get()

            # Вопросы
            for q_key in BOT_CONFIG['texts'][lang_code]['questions'].keys():
                widget_key = f'{lang_code}_questions_{q_key}'
                if widget_key in self.textarea_widgets:
                    text_content = self.textarea_widgets[widget_key].get('1.0', tk.END).strip()
                    BOT_CONFIG['texts'][lang_code]['questions'][q_key] = text_content

        messagebox.showinfo("Конфигурация", "Настройки успешно сохранены в памяти.")
        
        # Если бот запущен, его нужно перезапустить, чтобы применить новые тексты
        if application and application.running:
            stop_bot_thread(self.status_label)
            messagebox.showinfo("Перезапуск Бота", "Бот остановлен. Нажмите 'ЗАПУСТИТЬ БОТ', чтобы применить новые тексты.")
            self.status_label.config(text="СТАТУС: ТРЕБУЕТСЯ ПЕРЕЗАПУСК", fg="orange")


if __name__ == '__main__':
    root = tk.Tk()
    app = BotManagerGUI(root)
    
    # Обработчик закрытия окна
    def on_closing():
        if application and application.running:
            stop_bot_thread(app.status_label)
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()



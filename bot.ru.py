import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Уникальный токен твоего бота от BotFather
TOKEN = "8870946479:AAGXjmQUJd3Lcs0hI2TqKoNTDCl1jbt90I8"

# Твой личный Telegram ID для получения заявок от клиентов
ADMIN_CHAT_ID = 773441776

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Шаг 1. Команда /start - приветствие и выбор языка
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "Здравствуйте! Добро пожаловать в службу консультаций по энергии.\n"
        "Помогу снизить расходы на электричество и газ в Германии.\n\n"
        "Bitte wählen Sie Ihre Sprache / Пожалуйста, выберите язык:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Шаг 2. Обработка нажатия на кнопки выбора языка
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "lang_ru":
        context.user_data['lang'] = 'ru'
        text = (
            "Отлично! Давайте подберем для вас выгодный тариф на свет или газ.\n"
            "Напишите, пожалуйста, ваше **имя** и **номер телефона**, чтобы я мог с вами связаться."
        )
    elif query.data == "lang_de":
        context.user_data['lang'] = 'de'
        text = (
            "Sehr gut! Lassen uns einen günstigeren Strom- oder Gastarif finden.\n"
            "Bitte schreiben Sie Ihren **Namen** und Ihre **Telefonnummer**, damit ich Sie kontaktieren kann."
        )
    else:
        return

    await query.edit_message_text(text=text, parse_mode="Markdown")

# Шаг 3. Получение данных от клиента и отправка уведомления тебе
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user = update.message.from_user
    
    # Формируем информацию о клиенте
    username_info = f"@{user.username}" if user.username else "нет username"
    client_info = (
        f"🚨 **Новая заявка на консультацию!**\n\n"
        f"👤 **Имя/Контакт от клиента:** {user_text}\n"
        f"🔗 **Профиль:** {user.first_name} ({username_info})\n"
        f"🆔 **ID клиента:** `{user.id}`"
    )
    
    # 1. Отправляем уведомление тебе (админу)
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=client_info,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу: {e}")

    # 2. Отвечаем клиенту на его языке
    lang = context.user_data.get('lang', 'ru')
    if lang == 'de':
        reply_msg = (
            "Vielen Dank! Ihre Anfrage wurde erfolgreich gesendet.\n"
            "Herr Nujkin wird sich in Kürze mit Ihnen in Verbindung setzen, um die besten Tarife zu vergleichen."
        )
    else:
        reply_msg = (
            "Спасибо! Ваша заявка успешно принята.\n"
            "Николай свяжется с вами в ближайшее время, чтобы подобрать лучшие тарифы."
        )
        
    await update.message.reply_text(reply_msg)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Бот запущен и готов принимать заявки!")
    application.run_polling()
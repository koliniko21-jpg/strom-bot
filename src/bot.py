
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from openai import OpenAI

# Инициализация OpenAI API клиента
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "8870946479:AAGXjmQUJd3Lcs0hI2TqKoNTDCl1jbt90I8"
ADMIN_CHAT_ID = 773441776

LANG, SERVICE, PLZ, CONSUMPTION, CONTACT = range(5)

TEXTS = {
    'RU': {
        'welcome': "Здравствуйте! Я помогу вам подобрать выгодный тариф на электричество или газ в Германии, а также отвечу на любые вопросы.",
        'choose_service': "Какая услуга вас интересует?",
        'service_strom': "⚡ Электричество (Strom)",
        'service_gas': "🔥 Газ (Gas)",
        'service_both': "⚡+🔥 Электричество и Газ",
        'ask_plz': "Введите ваш почтовый индекс (PLZ), например: 88499",
        'ask_consumption': "Отправьте **фото квитанции** (Jahresabrechnung) или напишите примерный годовой расход (в kWh / м³).\n\nИли напишите «Пропустить».",
        'photo_rec': "📸 Фото получено!\n\nТеперь напишите ваше **имя** и **номер телефона** для связи.",
        'ask_contact': "Напишите ваше **имя** и **номер телефона** для связи.",
        'thanks': "Спасибо! Ваша заявка успешно принята. Николай свяжется с вами в ближайшее время.",
        'admin_title': "🚨 **Новая заявка на консультацию!**\n\n",
    },
    'DE': {
        'welcome': "Hallo! Ich helfe Ihnen, einen günstigen Strom- oder Gastarif in Deutschland zu finden und beantworte gerne Ihre Fragen.",
        'choose_service': "Welcher Service interessiert Sie?",
        'service_strom': "⚡ Strom",
        'service_gas': "🔥 Gas",
        'service_both': "⚡+🔥 Strom & Gas",
        'ask_plz': "Bitte geben Sie Ihre Postleitzahl (PLZ) ein, z.B.: 88499",
        'ask_consumption': "Senden Sie ein **Foto der Jahresabrechnung** oder den Verbrauch (in kWh / m³).\n\nOder schreiben Sie «Weiter».",
        'photo_rec': "📸 Foto empfangen!\n\nBitte schreiben Sie jetzt Ihren **Namen** und Ihre **Telefonnummer**.",
        'ask_contact': "Bitte schreiben Sie Ihren **Namen** und Ihre **Telefonnummer**.",
        'thanks': "Vielen Dank! Ihre Anfrage wurde erfolgreich empfangen. Nikolaj wird sich in Kürze melden.",
        'admin_title': "🚨 **Neue Beratungsanfrage!**\n\n",
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Русский 🇷🇺", callback_data='lang_RU')],
        [InlineKeyboardButton("Deutsch 🇩🇪", callback_data='lang_DE')]
    ]
    await update.message.reply_text(
        "Willkommen! / Добро пожаловать!\nВыберите язык / Wählen Sie die Sprache:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang = 'RU' if query.data == 'lang_RU' else 'DE'
    context.user_data['lang'] = lang
    t = TEXTS[lang]
    
    keyboard = [
        [InlineKeyboardButton(t['service_strom'], callback_data='srv_strom')],
        [InlineKeyboardButton(t['service_gas'], callback_data='srv_gas')],
        [InlineKeyboardButton(t['service_both'], callback_data='srv_both')]
    ]
    await query.edit_message_text(
        f"{t['welcome']}\n\n{t['choose_service']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SERVICE

async def set_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    service_map = {
        'srv_strom': '⚡ Strom',
        'srv_gas': '🔥 Gas',
        'srv_both': '⚡+🔥 Strom & Gas'
    }
    context.user_data['service'] = service_map.get(query.data, 'Strom/Gas')
    lang = context.user_data.get('lang', 'RU')
    
    await query.edit_message_text(TEXTS[lang]['ask_plz'])
    return PLZ

async def set_plz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['plz'] = update.message.text
    lang = context.user_data.get('lang', 'RU')
    
    await update.message.reply_text(TEXTS[lang]['ask_consumption'], parse_mode='Markdown')
    return CONSUMPTION

async def set_consumption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'RU')
    t = TEXTS[lang]
    
    if update.message.photo:
        context.user_data['photo_id'] = update.message.photo[-1].file_id
        context.user_data['consumption'] = "📸 Фото квитанции прикреплено"
        await update.message.reply_text(t['photo_rec'], parse_mode='Markdown')
    else:
        context.user_data['consumption'] = update.message.text
        await update.message.reply_text(t['ask_contact'], parse_mode='Markdown')
        
    return CONTACT

async def set_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contact'] = update.message.text
    lang = context.user_data.get('lang', 'RU')
    t = TEXTS[lang]
    
    user = update.effective_user
    username = f"@{user.username}" if user.username else "нет username"
    
    admin_msg = (
        f"{t['admin_title']}"
        f"👤 **Контакт:** {context.user_data['contact']}\n"
        f"🛠 **Услуга:** {context.user_data.get('service', '—')}\n"
        f"📍 **PLZ:** {context.user_data.get('plz', '—')}\n"
        f"📊 **Данные:** {context.user_data.get('consumption', '—')}\n"
        f"💬 **Профиль:** {username} (ID: `{user.id}`)"
    )
    
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')
    
    if 'photo_id' in context.user_data:
        await context.bot.send_photo(
            chat_id=ADMIN_CHAT_ID,
            photo=context.user_data['photo_id'],
            caption=f"📄 Квитанция от клиента: {context.user_data['contact']}"
        )
        
    await update.message.reply_text(t['thanks'])
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён / Dialog abgebrochen.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Обработчик свободных вопросов с использованием ChatGPT
async def handle_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    system_prompt = (
        "Вы — вежливый и профессиональный цифровой помощник Николая, независимого энергоконсультанта "
        "(Energieberater) в Германии. Ваша задача — помогать клиентам разбираться в вопросах смены поставщиков "
        "электричества и газа (Strom und Gas), тарифах, экономии, бонусах и договорах в Германии. "
        "Отвечайте коротко, понятно, дружелюбно и профессионально. "
        "Если клиент спрашивает о конкретном расчете или хочет сменить тариф, вежливо предложите ему "
        "нажать на команду /start, чтобы подать заявку."
    )
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            max_tokens=400
        )
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        await update.message.reply_text("Извините, произошла ошибка при обработке запроса. Вы можете начать подачу заявки командой /start.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANG: [CallbackQueryHandler(set_language, pattern='^lang_')],
            SERVICE: [CallbackQueryHandler(set_service, pattern='^srv_')],
            PLZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_plz)],
            CONSUMPTION: [
                MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), set_consumption)
            ],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_contact)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(conv_handler)
    
    # Обработчик для обычных сообщений вне анкеты (вопросы к ИИ)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_question))
    
    print("Умный бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()

import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен. Добавьте его в Render → Environment.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Не выводим URL запросов Telegram API в логи: в них присутствует токен.
logging.getLogger("httpx").setLevel(logging.WARNING)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return


def start_web_server():
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info("Health server listening on port %s", port)
    server.serve_forever()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
    ]]
    await update.message.reply_text(
        "⚡ Willkommen bei Strom & Gas Deutschland!\n\n"
        "Добро пожаловать!\n\n"
        "Bitte wählen Sie Ihre Sprache.\n"
        "Пожалуйста, выберите язык.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = "ru" if query.data == "lang_ru" else "de"
    context.user_data["language"] = language

    if language == "ru":
        text = "⚡ Добро пожаловать!\n\nЧто вы хотите сделать?"
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить договор", callback_data="contract")],
            [InlineKeyboardButton("💰 Рассчитать экономию", callback_data="savings")],
            [InlineKeyboardButton("👨‍💼 Связаться с консультантом", callback_data="contact")],
        ]
    else:
        text = "⚡ Herzlich willkommen!\n\nWas möchten Sie tun?"
        keyboard = [
            [InlineKeyboardButton("🔍 Vertrag prüfen", callback_data="contract")],
            [InlineKeyboardButton("💰 Ersparnis berechnen", callback_data="savings")],
            [InlineKeyboardButton("👨‍💼 Berater kontaktieren", callback_data="contact")],
        ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = context.user_data.get("language", "de")

    if query.data == "contract":
        text = (
            "🔍 Отправьте ваш договор на электроэнергию или газ. "
            "Автоматическая проверка пока не подключена."
            if language == "ru"
            else "🔍 Senden Sie Ihren Strom- oder Gasvertrag. "
                 "Die automatische Prüfung ist noch nicht verfügbar."
        )
    elif query.data == "savings":
        text = (
            "💰 Скоро здесь можно будет рассчитать экономию."
            if language == "ru"
            else "💰 Hier können Sie bald Ihre Ersparnis berechnen."
        )
    elif query.data == "contact":
        text = (
            "👨‍💼 Свяжитесь с консультантом: @nikolajnujkinfit"
            if language == "ru"
            else "👨‍💼 Kontaktieren Sie Ihren Berater: @nikolajnujkinfit"
        )
    else:
        return

    await query.message.reply_text(text)


def main():
    # Render Web Service требует открытый HTTP-порт.
    Thread(target=start_web_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choose_language, pattern=r"^lang_(ru|de)$"))
    app.add_handler(CallbackQueryHandler(handle_menu, pattern=r"^(contract|savings|contact)$"))
    app.run_polling()


if __name__ == "__main__":
    main()

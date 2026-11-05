
import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не установлен!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de"),
        ]
    ]

    await update.message.reply_text(
        "⚡ Willkommen bei Strom & Gas Deutschland!\n\n"
        "Добро пожаловать!\n\n"
        "Bitte wählen Sie Ihre Sprache.\n"
        "Пожалуйста, выберите язык.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

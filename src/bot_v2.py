"""Strom & Gas Berater — Telegram lead intake and optional document reading.
Environment: BOT_TOKEN, OPENAI_API_KEY, ADMIN_CHAT_ID; optional PORT, OPENAI_MODEL.
Requires python-telegram-bot>=20,<23. No extra PDF libraries required.
"""
import asyncio
import base64
import json
import logging
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

LANG, NAME, PLZ, CITY, STREET, ENERGY, DOCUMENT, VERIFY, CONTACT_METHOD, CONTACT, CONSENT = range(11)
MAX_FILE_BYTES = 15 * 1024 * 1024

T = {
    "ru": {
        "hello": "Здравствуйте! Я помощник Strom & Gas Berater. Выберите язык:",
        "name": "Как вас зовут? Напишите имя и фамилию.",
        "plz": "Укажите ваш PLZ (почтовый индекс Германии, 5 цифр). Можно нажать «Пропустить».",
        "city": "В каком городе вы живёте? Можно пропустить.",
        "street": "Улица и номер дома (необязательно). Можно пропустить.",
        "energy": "Что хотите проверить?",
        "doc": "Можете отправить фото или PDF счёта/договора. Это НЕ обязательно — можно пропустить. Не присылайте документы с лишними персональными данными.",
        "reading": "📄 Получил документ, пытаюсь прочитать. Подождите немного…",
        "read_ok": "Вот что удалось прочитать (проверьте, пожалуйста):\n\n{details}\n\nДанные верны? Если нет, можно написать исправления следующим сообщением.",
        "read_fail": "Не получилось надёжно прочитать документ. Можете отправить более чёткое фото/PDF или пропустить. Я не буду придумывать данные.",
        "verify": "Напишите исправления одним сообщением или нажмите «Подтвердить».",
        "method": "Как Николаю удобнее с вами связаться? Выберите один способ:",
        "phone": "Напишите номер телефона с кодом страны, например +49…",
        "email": "Напишите адрес e-mail.",
        "telegram": "Для связи через Telegram желательно иметь публичный @username. Если он есть, я использую его. Если нет — введите свой @username или выберите другой способ связи командой /contact.",
        "no_username": "У вашего аккаунта нет публичного @username. Укажите @username после его создания или выберите телефон/e-mail командой /contact.",
        "consent": "Передать Николаю вашу анкету, выбранный контакт и, если вы прислали, документ для подготовки предложения? Это добровольно. Передача будет происходить через Telegram. Нажмите «Согласен» для отправки или «Отмена».",
        "sent": "✅ Спасибо! Ваша заявка отправлена Николаю. Он свяжется с вами выбранным способом.",
        "send_error": "Не удалось передать заявку консультанту. Пожалуйста, попробуйте позже или начните заново с /start.",
        "cancel": "Заявка отменена, данные консультанту не отправлены. Для новой заявки нажмите /start.",
        "skip": "⏭ Пропустить", "confirm": "✅ Подтвердить", "fix": "✏️ Исправить", "yes": "✅ Согласен", "no": "❌ Отмена",
        "invalid": "Пожалуйста, ответьте на текущий вопрос или используйте кнопки.",
        "bad_plz": "PLZ должен содержать 5 цифр. Например: 88499. Или нажмите «Пропустить».",
        "bad_email": "Проверьте e-mail и отправьте ещё раз.",
        "bad_phone": "Проверьте номер телефона и отправьте ещё раз.",
        "bad_file": "Отправьте фотографию или PDF (до 15 МБ) либо нажмите «Пропустить».",
    },
    "de": {
        "hello": "Willkommen bei Strom & Gas Berater! Bitte wählen Sie Ihre Sprache:",
        "name": "Wie heißen Sie? Bitte Vor- und Nachnamen eingeben.",
        "plz": "Ihre Postleitzahl (5 Ziffern)? Optional: Überspringen.",
        "city": "In welcher Stadt wohnen Sie? Optional.",
        "street": "Straße und Hausnummer (freiwillig). Sie können überspringen.",
        "energy": "Was möchten Sie prüfen lassen?",
        "doc": "Sie können ein Foto oder eine PDF Ihrer Rechnung/Ihres Vertrags senden. Das ist FREIWILLIG. Alternativ überspringen. Bitte unnötige persönliche Angaben schwärzen.",
        "reading": "📄 Dokument erhalten. Ich versuche, die Angaben auszulesen…",
        "read_ok": "Ich konnte Folgendes erkennen (bitte prüfen):\n\n{details}\n\nSind die Angaben richtig? Falls nicht, können Sie die Korrekturen schreiben.",
        "read_fail": "Das Dokument konnte nicht zuverlässig gelesen werden. Bitte ein deutlicheres Foto/PDF senden oder überspringen. Ich erfinde keine Werte.",
        "verify": "Bitte Korrekturen als Nachricht senden oder auf „Bestätigen“ tippen.",
        "method": "Wie soll Nikolai Sie kontaktieren? Bitte wählen:",
        "phone": "Bitte Telefonnummer mit Ländervorwahl eingeben, z. B. +49…",
        "email": "Bitte E-Mail-Adresse eingeben.",
        "telegram": "Für Telegram-Kontakt wird ein öffentlicher @Benutzername benötigt. Falls keiner vorhanden ist, erstellen Sie einen oder wählen /contact für eine andere Kontaktart.",
        "no_username": "Sie haben keinen öffentlichen @Benutzernamen. Bitte erstellen Sie einen oder wählen /contact für Telefon/E-Mail.",
        "consent": "Darf ich Ihre Angaben, den gewählten Kontaktweg und gegebenenfalls Ihr Dokument über Telegram an Nikolai weiterleiten, damit er ein Angebot vorbereiten kann? Die Angabe ist freiwillig. Bitte ausdrücklich zustimmen.",
        "sent": "✅ Vielen Dank! Ihre Anfrage wurde an Nikolai gesendet. Er meldet sich über den gewählten Kontaktweg.",
        "send_error": "Die Anfrage konnte nicht zugestellt werden. Bitte versuchen Sie es später erneut oder starten Sie mit /start.",
        "cancel": "Anfrage abgebrochen. Es wurden keine Angaben an den Berater gesendet. Neustart mit /start.",
        "skip": "⏭ Überspringen", "confirm": "✅ Bestätigen", "fix": "✏️ Korrigieren", "yes": "✅ Einverstanden", "no": "❌ Abbrechen",
        "invalid": "Bitte beantworten Sie die aktuelle Frage oder nutzen Sie die Schaltflächen.",
        "bad_plz": "Die PLZ muss 5 Ziffern haben, z. B. 88499. Oder überspringen.",
        "bad_email": "Bitte eine gültige E-Mail-Adresse eingeben.",
        "bad_phone": "Bitte Telefonnummer prüfen und erneut senden.",
        "bad_file": "Bitte ein Foto oder eine PDF (bis 15 MB) senden oder überspringen.",
    },
}


def lang(ctx):
    return ctx.user_data.get("lang", "ru")


def tr(ctx, key):
    return T[lang(ctx)][key]


def buttons(*rows):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=key) for label, key in row] for row in rows])


def skip_buttons(ctx):
    return buttons([(tr(ctx, "skip"), "skip")])


async def say(update, text, markup=None):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, reply_markup=markup)
    else:
        await update.effective_message.reply_text(text, reply_markup=markup)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await say(update, "Здравствуйте! Willkommen! Выберите язык / Sprache wählen:", buttons([("🇷🇺 Русский", "lang_ru"), ("🇩🇪 Deutsch", "lang_de")]))
    return LANG


async def choose_lang(update, ctx):
    data = update.callback_query.data
    ctx.user_data["lang"] = "de" if data == "lang_de" else "ru"
    await say(update, tr(ctx, "name"))
    return NAME


async def get_name(update, ctx):
    value = update.message.text.strip()
    if len(value) < 2 or len(value) > 120:
        await say(update, tr(ctx, "invalid"))
        return NAME
    ctx.user_data["name"] = value
    await say(update, tr(ctx, "plz"), skip_buttons(ctx))
    return PLZ


async def get_plz(update, ctx):
    if update.callback_query:
        ctx.user_data["plz"] = "—"
    else:
        value = update.message.text.strip()
        if not re.fullmatch(r"\d{5}", value):
            await say(update, tr(ctx, "bad_plz"), skip_buttons(ctx))
            return PLZ
        ctx.user_data["plz"] = value
    await say(update, tr(ctx, "city"), skip_buttons(ctx))
    return CITY


async def get_city(update, ctx):
    ctx.user_data["city"] = "—" if update.callback_query else update.message.text.strip()[:120]
    await say(update, tr(ctx, "street"), skip_buttons(ctx))
    return STREET


async def get_street(update, ctx):
    ctx.user_data["street"] = "—" if update.callback_query else update.message.text.strip()[:160]
    await say(update, tr(ctx, "energy"), buttons([("⚡ Strom", "energy_strom"), ("🔥 Gas", "energy_gas")]))
    return ENERGY


async def get_energy(update, ctx):
    ctx.user_data["energy"] = "Strom" if update.callback_query.data == "energy_strom" else "Gas"
    await say(update, tr(ctx, "doc"), skip_buttons(ctx))
    return DOCUMENT


def openai_extract(file_bytes, mime_type):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    encoded = base64.b64encode(file_bytes).decode("ascii")
    if mime_type == "application/pdf":
        attachment = {"type": "input_file", "filename": "vertrag.pdf", "file_data": f"data:application/pdf;base64,{encoded}"}
    else:
        attachment = {"type": "input_image", "image_url": f"data:{mime_type};base64,{encoded}"}
        instruction = (
    "Read this German electricity/gas contract or invoice. Return a short, plain-text report in Russian and German. ",
    "Use Russian and German labels. Provide the report in both languages. ", 
    "Extract ONLY information clearly visible: supplier (Anbieter), annual consumption (Jahresverbrauch kWh), "
    "unit price (Arbeitspreis with unit), fixed fee (Grundpreis with period), and document type. "
        "If a field is absent or unreadable, write 'nicht gefunden'. Respond in both Russian and German.", 
        "Do not invent values, do not provide offers, and do not reproduce personal identifiers, bank details or names. "
        "Limit response to 1100 characters."
    )
    payload = {"model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"), "input": [{"role": "user", "content": [{"type": "input_text", "text": instruction}, attachment]}], "max_output_tokens": 450}
    request = Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=75) as response:
            result = json.load(response)
    except HTTPError as error:
        log.warning("OpenAI returned HTTP %s", error.code)
        raise RuntimeError("OpenAI request failed") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError("OpenAI unavailable") from error
    fragments = []
    for item in result.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                fragments.append(part.get("text", ""))
    text = "\n".join(fragments).strip()
    if not text:
        raise RuntimeError("No extracted text")
    return text[:1600]


async def receive_doc(update, ctx):
    if update.callback_query:
        ctx.user_data["doc"] = None
        ctx.user_data["extracted"] = "—"
        return await ask_method(update, ctx)
    msg = update.message
    if msg.photo:
        obj = msg.photo[-1]
        mime = "image/jpeg"
        kind = "photo"
    elif msg.document and msg.document.mime_type in ("application/pdf", "image/jpeg", "image/png", "image/webp"):
        obj = msg.document
        mime = msg.document.mime_type
        kind = "document"
    else:
        await say(update, tr(ctx, "bad_file"), skip_buttons(ctx))
        return DOCUMENT
    if obj.file_size and obj.file_size > MAX_FILE_BYTES:
        await say(update, tr(ctx, "bad_file"), skip_buttons(ctx))
        return DOCUMENT
    await say(update, tr(ctx, "reading"))
    try:
        tg_file = await obj.get_file()
        raw = bytes(await tg_file.download_as_bytearray())
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError("File too large")
        ctx.user_data["doc"] = {"kind": kind, "file_id": obj.file_id}
        extracted = await asyncio.to_thread(openai_extract, raw, mime)
        ctx.user_data["extracted"] = extracted
        await say(update, tr(ctx, "read_ok").format(details=extracted), buttons([(tr(ctx, "confirm"), "verify_yes"), (tr(ctx, "fix"), "verify_fix")]))
        return VERIFY
    except Exception:
        log.exception("Document recognition failed")
        ctx.user_data["extracted"] = "Не удалось прочитать / Nicht lesbar"
        await say(update, tr(ctx, "read_fail"), skip_buttons(ctx))
        return DOCUMENT


async def verify(update, ctx):
    if update.callback_query:
        if update.callback_query.data == "verify_fix":
            await say(update, tr(ctx, "verify"))
            return VERIFY
        return await ask_method(update, ctx)
    correction = update.message.text.strip()[:1200]
    ctx.user_data["extracted"] += "\nКлиент уточнил / Kunde korrigiert: " + correction
    return await ask_method(update, ctx)


async def ask_method(update, ctx):
    await say(update, tr(ctx, "method"), buttons([("📞 Telefon", "method_phone")], [("✉️ E-Mail", "method_email")], [("💬 Telegram", "method_telegram")]))
    return CONTACT_METHOD


async def choose_method(update, ctx):
    method = update.callback_query.data.replace("method_", "")
    ctx.user_data["contact_method"] = method
    if method == "telegram":
        username = update.effective_user.username
        if username:
            ctx.user_data["contact"] = "@" + username
            return await ask_consent(update, ctx)
        await say(update, tr(ctx, "no_username"))
        return CONTACT
    await say(update, tr(ctx, method))
    return CONTACT


async def get_contact(update, ctx):
    method = ctx.user_data.get("contact_method")
    value = update.message.text.strip()
    if method == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        await say(update, tr(ctx, "bad_email"))
        return CONTACT
    if method == "phone" and (len(re.sub(r"\D", "", value)) < 7 or len(value) > 40):
        await say(update, tr(ctx, "bad_phone"))
        return CONTACT
    if method == "telegram" and not re.fullmatch(r"@[A-Za-z0-9_]{5,32}", value):
        await say(update, tr(ctx, "no_username"))
        return CONTACT
    ctx.user_data["contact"] = value[:120]
    return await ask_consent(update, ctx)


async def contact_command(update, ctx):
    return await ask_method(update, ctx)


async def ask_consent(update, ctx):
    await say(update, tr(ctx, "consent"), buttons([(tr(ctx, "yes"), "consent_yes")], [(tr(ctx, "no"), "consent_no")]))
    return CONSENT


def safe(s):
    return str(s or "—").replace("<", "‹").replace(">", "›")


async def finish(update, ctx):
    if update.callback_query.data == "consent_no":
        await say(update, tr(ctx, "cancel"))
        ctx.user_data.clear()
        return ConversationHandler.END
    admin = os.environ.get("ADMIN_CHAT_ID", "").strip()
    if not admin:
        log.error("ADMIN_CHAT_ID is missing")
        await say(update, tr(ctx, "send_error"))
        return CONSENT
    user = update.effective_user
    data = ctx.user_data
    report = (
        "📩 Новая заявка / Neue Anfrage\n\n"
        f"Имя / Name: {safe(data.get('name'))}\n"
        f"PLZ: {safe(data.get('plz'))}\n"
        f"Город / Stadt: {safe(data.get('city'))}\n"
        f"Адрес / Straße: {safe(data.get('street'))}\n"
        f"Энергия: {safe(data.get('energy'))}\n"
        f"Связь / Kontakt: {safe(data.get('contact_method'))} — {safe(data.get('contact'))}\n"
        f"Telegram ID: {user.id}\n"
        f"Договор / Dokument: {'Да / Ja' if data.get('doc') else 'Нет / Nein'}\n\n"
        f"Распознано / Ausgelesen:\n{safe(data.get('extracted'))}"
    )
    try:
        await ctx.bot.send_message(chat_id=int(admin), text=report[:3900])
        doc = data.get("doc")
        if doc:
            if doc["kind"] == "photo":
                await ctx.bot.send_photo(chat_id=int(admin), photo=doc["file_id"], caption="Оригинал договора / Originaldokument")
            else:
                await ctx.bot.send_document(chat_id=int(admin), document=doc["file_id"], caption="Оригинал договора / Originaldokument")
    except Exception:
        log.exception("Failed to forward lead to admin")
        await say(update, tr(ctx, "send_error"))
        return CONSENT
    await say(update, tr(ctx, "sent"))
    ctx.user_data.clear()
    return ConversationHandler.END


async def cancel(update, ctx):
    await say(update, tr(ctx, "cancel"))
    ctx.user_data.clear()
    return ConversationHandler.END


async def unexpected(update, ctx):
    await say(update, tr(ctx, "invalid"))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args):
        pass


def health_server():
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()


def main():
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN missing in Render Environment")
    Thread(target=health_server, daemon=True).start()
    app = Application.builder().token(token).build()
    text_filter = filters.TEXT & ~filters.COMMAND
    doc_filter = filters.PHOTO | filters.Document.ALL
    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [CallbackQueryHandler(choose_lang, pattern=r"^lang_(ru|de)$")],
            NAME: [MessageHandler(text_filter, get_name)],
            PLZ: [CallbackQueryHandler(get_plz, pattern="^skip$"), MessageHandler(text_filter, get_plz)],
            CITY: [CallbackQueryHandler(get_city, pattern="^skip$"), MessageHandler(text_filter, get_city)],
            STREET: [CallbackQueryHandler(get_street, pattern="^skip$"), MessageHandler(text_filter, get_street)],
            ENERGY: [CallbackQueryHandler(get_energy, pattern=r"^energy_(strom|gas)$")],
            DOCUMENT: [CallbackQueryHandler(receive_doc, pattern="^skip$"), MessageHandler(doc_filter, receive_doc)],
            VERIFY: [CallbackQueryHandler(verify, pattern=r"^verify_(yes|fix)$"), MessageHandler(text_filter, verify)],
            CONTACT_METHOD: [CallbackQueryHandler(choose_method, pattern=r"^method_(phone|email|telegram)$")],
            CONTACT: [MessageHandler(text_filter, get_contact)],
            CONSENT: [CallbackQueryHandler(finish, pattern=r"^consent_(yes|no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("contact", contact_command), MessageHandler(filters.ALL, unexpected)],
        allow_reentry=True,
    )
    app.add_handler(conversation)
    log.info("Starting bot polling and health server")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

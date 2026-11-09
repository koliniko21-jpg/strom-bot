"""Strom & Gas Berater Telegram bot.

Environment: BOT_TOKEN, ADMIN_CHAT_ID, OPENAI_API_KEY (optional), OPENAI_MODEL (optional), PORT (optional).
Dependencies: python-telegram-bot>=20.7,<23
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
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('strombot')
MAX_FILE = 12 * 1024 * 1024

RU = {
 'choose': 'Выберите язык / Sprache wählen:', 'welcome': 'Здравствуйте! Помогу проверить ваш договор на электричество или газ. Выберите действие:',
 'check': '📄 Проверить договор', 'consult': '👤 Связаться с консультантом', 'restart': '🔄 Начать заново',
 'name': 'Как вас зовут? Напишите имя.', 'plz': 'Укажите почтовый индекс (PLZ, 5 цифр) и город.',
 'contact': 'Напишите номер телефона или другой способ связи. Если хотите общаться только здесь, напишите «Telegram».',
 'energy': 'Что проверяем?', 'electric': '⚡ Электричество', 'gas': '🔥 Газ',
 'doc': 'Отправьте фото договора или счёта либо PDF-файл. Можно также нажать «Пропустить».',
 'skip': 'Пропустить', 'received': 'Документ получен. Проверяю данные…',
 'no_ai': 'Автоматическое чтение сейчас недоступно. Документ будет передан консультанту.',
 'unreadable': 'Не удалось надёжно прочитать документ. Консультант сможет проверить его вручную.',
 'consent': 'Разрешаете передать ваши контактные данные и документ консультанту для обработки заявки?',
 'yes': '✅ Да, отправить', 'no': '❌ Нет, отменить',
 'done': 'Спасибо! Заявка отправлена консультанту. С вами свяжутся.',
 'no_admin': 'Заявка подготовлена, но адрес консультанта не настроен. Пожалуйста, попробуйте позже.',
 'cancel': 'Заявка отменена. Данные этой заявки не отправлены консультанту.',
 'bad_plz': 'Напишите PLZ из 5 цифр и город, например: 88499 Riedlingen.',
 'too_big': 'Файл слишком большой. Отправьте документ размером до 12 МБ.',
 'bad_doc': 'Пожалуйста, отправьте фото (JPG/PNG) или PDF.',
 'error': 'Произошла ошибка. Попробуйте ещё раз через /start.',
 'no_savings': 'Точную экономию можно посчитать только после сравнения с актуальным тарифом. Бот не придумывает предложения и цены.',
 'consult_intro': 'Оставьте данные, и консультант свяжется с вами.',
}
DE = {
 'choose': 'Sprache wählen / Выберите язык:', 'welcome': 'Willkommen! Ich helfe bei der Prüfung Ihres Strom- oder Gasvertrags. Bitte wählen:',
 'check': '📄 Vertrag prüfen', 'consult': '👤 Berater kontaktieren', 'restart': '🔄 Neu starten',
 'name': 'Wie heißen Sie? Bitte geben Sie Ihren Namen ein.', 'plz': 'Bitte geben Sie Ihre PLZ (5 Ziffern) und Ihren Ort an.',
 'contact': 'Bitte geben Sie Ihre Telefonnummer oder eine andere Kontaktmöglichkeit an. Für Kontakt nur über Telegram schreiben Sie „Telegram“.',
 'energy': 'Was möchten Sie prüfen?', 'electric': '⚡ Strom', 'gas': '🔥 Gas',
 'doc': 'Bitte senden Sie ein Foto oder eine PDF Ihres Vertrags bzw. Ihrer Rechnung. Sie können auch „Überspringen“ wählen.',
 'skip': 'Überspringen', 'received': 'Dokument erhalten. Ich prüfe die Angaben…',
 'no_ai': 'Automatische Auswertung ist derzeit nicht verfügbar. Ihr Berater kann das Dokument prüfen.',
 'unreadable': 'Das Dokument konnte nicht zuverlässig gelesen werden. Der Berater kann es manuell prüfen.',
 'consent': 'Dürfen Ihre Kontaktdaten und das Dokument zur Bearbeitung an den Berater weitergeleitet werden?',
 'yes': '✅ Ja, senden', 'no': '❌ Nein, abbrechen',
 'done': 'Vielen Dank! Ihre Anfrage wurde an den Berater gesendet.',
 'no_admin': 'Ihre Anfrage wurde vorbereitet, aber der Berater ist nicht konfiguriert. Bitte versuchen Sie es später erneut.',
 'cancel': 'Anfrage abgebrochen. Ihre Daten wurden nicht an den Berater gesendet.',
 'bad_plz': 'Bitte PLZ mit 5 Ziffern und Ort eingeben, z. B. 88499 Riedlingen.',
 'too_big': 'Datei zu groß. Bitte senden Sie höchstens 12 MB.',
 'bad_doc': 'Bitte senden Sie ein Foto (JPG/PNG) oder eine PDF.',
 'error': 'Ein Fehler ist aufgetreten. Bitte versuchen Sie /start erneut.',
 'no_savings': 'Eine genaue Ersparnis ist erst mit einem aktuellen Vergleichstarif berechenbar. Der Bot erfindet keine Preise oder Angebote.',
 'consult_intro': 'Hinterlassen Sie Ihre Daten, und der Berater meldet sich.',
}

def tr(ctx, key):
    return (DE if ctx.user_data.get('lang') == 'de' else RU)[key]

def buttons(*items):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=key)] for label, key in items])

def menu(ctx):
    return buttons((tr(ctx, 'check'), 'check'), (tr(ctx, 'consult'), 'consult'), (tr(ctx, 'restart'), 'restart'))

async def send(update, text, markup=None):
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=markup)
    else:
        await update.effective_message.reply_text(text, reply_markup=markup)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    ctx.user_data['step'] = 'language'
    await send(update, RU['choose'], buttons(('🇷🇺 Русский', 'lang_ru'), ('🇩🇪 Deutsch', 'lang_de')))

async def action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data
    if key == 'restart':
        await start(update, ctx)
        return
    if key.startswith('lang_'):
        ctx.user_data['lang'] = key[5:]
        ctx.user_data['step'] = 'menu'
        await send(update, tr(ctx, 'welcome'), menu(ctx))
    elif key in ('check', 'consult'):
        ctx.user_data['mode'] = key
        ctx.user_data['step'] = 'name'
        await send(update, (tr(ctx, 'consult_intro') + '\n\n' if key == 'consult' else '') + tr(ctx, 'name'))
    elif key in ('energy_strom', 'energy_gas') and ctx.user_data.get('step') == 'energy':
        ctx.user_data['energy'] = 'Strom' if key == 'energy_strom' else 'Gas'
        ctx.user_data['step'] = 'document'
        await send(update, tr(ctx, 'doc'), buttons((tr(ctx, 'skip'), 'skip')))
    elif key == 'skip' and ctx.user_data.get('step') == 'document':
        ctx.user_data['step'] = 'consent'
        await ask_consent(update, ctx)
    elif key == 'agree' and ctx.user_data.get('step') == 'consent':
        await submit(update, ctx)
    elif key == 'decline' and ctx.user_data.get('step') == 'consent':
        lang = ctx.user_data.get('lang', 'ru')
        ctx.user_data.clear()
        ctx.user_data['lang'] = lang
        await send(update, tr(ctx, 'cancel'))
    else:
        await send(update, tr(ctx, 'welcome'), menu(ctx))

async def ask_consent(update, ctx):
    await send(update, tr(ctx, 'consent'), buttons((tr(ctx, 'yes'), 'agree'), (tr(ctx, 'no'), 'decline')))

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    step = ctx.user_data.get('step')
    value = (update.message.text or '').strip()
    if step == 'name':
        if len(value) < 2 or len(value) > 100:
            await send(update, tr(ctx, 'name'))
            return
        ctx.user_data['name'] = value
        ctx.user_data['step'] = 'plz'
        await send(update, tr(ctx, 'plz'))
    elif step == 'plz':
        if not re.search(r'\b\d{5}\b', value):
            await send(update, tr(ctx, 'bad_plz'))
            return
        ctx.user_data['location'] = value[:150]
        ctx.user_data['step'] = 'contact'
        await send(update, tr(ctx, 'contact'))
    elif step == 'contact':
        if len(value) < 3 or len(value) > 150:
            await send(update, tr(ctx, 'contact'))
            return
        ctx.user_data['contact'] = value
        if ctx.user_data.get('mode') == 'consult':
            ctx.user_data['energy'] = 'Beratung'
            ctx.user_data['step'] = 'consent'
            await ask_consent(update, ctx)
        else:
            ctx.user_data['step'] = 'energy'
            await send(update, tr(ctx, 'energy'), buttons((tr(ctx, 'electric'), 'energy_strom'), (tr(ctx, 'gas'), 'energy_gas')))
    elif step == 'document':
        await send(update, tr(ctx, 'bad_doc'), buttons((tr(ctx, 'skip'), 'skip')))
    elif step == 'consent':
        await ask_consent(update, ctx)
    else:
        await start(update, ctx)


def extract_sync(raw: bytes, mime: str):
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        return None
    b64 = base64.b64encode(raw).decode('ascii')
    if mime == 'application/pdf':
        attachment = {'type': 'input_file', 'filename': 'vertrag.pdf', 'file_data': 'data:application/pdf;base64,' + b64}
    else:
        attachment = {'type': 'input_image', 'image_url': f'data:{mime};base64,{b64}'}
    prompt = ('Read this German electricity or gas contract/invoice. Extract only clearly visible: '
              'provider, electricity/gas, annual consumption kWh, Arbeitspreis ct/kWh, '
              'Grundpreis EUR/month or year, annual amount if visible. '
              'Write a concise bilingual Russian and German summary. '
              'If a value is missing say unknown. Do not invent savings or prices. '
              'Do not repeat names, addresses, account numbers or personal identifiers. '
              'Limit output to 1200 characters.')
    payload = {'model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
               'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': prompt}, attachment]}],
               'max_output_tokens': 550}
    req = Request('https://api.openai.com/v1/responses',
                  data=json.dumps(payload).encode('utf-8'),
                  headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(req, timeout=75) as resp:
            result = json.load(resp)
    except HTTPError as exc:
        # Never log credentials or contract content. Error body can contain user content; omit it.
        log.warning('OpenAI HTTP %s (model=%s, mime=%s)', exc.code, payload['model'], mime)
        return None
    except (URLError, TimeoutError, ValueError) as exc:
        log.warning('OpenAI request failed: %s', type(exc).__name__)
        return None
    texts = []
    for item in result.get('output', []):
        if item.get('type') == 'message':
            for part in item.get('content', []):
                if part.get('type') == 'output_text':
                    texts.append(part.get('text', ''))
    return '\n'.join(texts).strip()[:1800] or None

async def document_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if ctx.user_data.get('step') != 'document':
        await send(update, tr(ctx, 'welcome'), menu(ctx))
        return
    msg = update.message
    doc = msg.document
    if msg.photo:
        obj = msg.photo[-1]
        mime = 'image/jpeg'
    elif doc and doc.mime_type in ('application/pdf', 'image/jpeg', 'image/png'):
        obj = doc
        mime = doc.mime_type
    else:
        await send(update, tr(ctx, 'bad_doc'))
        return
    if obj.file_size and obj.file_size > MAX_FILE:
        await send(update, tr(ctx, 'too_big'))
        return
    await send(update, tr(ctx, 'received'))
    try:
        tg_file = await obj.get_file()
        data = bytes(await tg_file.download_as_bytearray())
        if len(data) > MAX_FILE:
            await send(update, tr(ctx, 'too_big'))
            return
        ctx.user_data['document_file_id'] = obj.file_id
        ctx.user_data['document_kind'] = 'photo' if msg.photo else 'document'
        if os.getenv('OPENAI_API_KEY', '').strip():
            summary = await asyncio.to_thread(extract_sync, data, mime)
            await send(update, summary if summary else tr(ctx, 'unreadable'))
        else:
            await send(update, tr(ctx, 'no_ai'))
        await send(update, tr(ctx, 'no_savings'))
        ctx.user_data['step'] = 'consent'
        await ask_consent(update, ctx)
    except Exception:
        log.exception('Document processing error')
        ctx.user_data['step'] = 'consent'
        await send(update, tr(ctx, 'unreadable'))
        await ask_consent(update, ctx)

async def submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get('lang', 'ru')
    admin = os.getenv('ADMIN_CHAT_ID', '').strip()
    if not admin or not re.fullmatch(r'-?\d+', admin):
        await send(update, tr(ctx, 'no_admin'))
        return
    user = update.effective_user
    info = (f'📩 Neue Anfrage / Новая заявка\n'
            f'Name: {ctx.user_data.get("name", "-")}\n'
            f'PLZ/Ort: {ctx.user_data.get("location", "-")}\n'
            f'Kontakt: {ctx.user_data.get("contact", "-")}\n'
            f'Energie: {ctx.user_data.get("energy", "-")}\n'
            f'Sprache: {lang}\n'
            f'Telegram ID: {user.id}')
    if user.username:
        info += f'\nTelegram: @{user.username}'
    try:
        await ctx.bot.send_message(chat_id=int(admin), text=info)
        file_id = ctx.user_data.get('document_file_id')
        if file_id:
            if ctx.user_data.get('document_kind') == 'photo':
                await ctx.bot.send_photo(chat_id=int(admin), photo=file_id, caption='Документ к заявке / Vertragsdokument')
            else:
                await ctx.bot.send_document(chat_id=int(admin), document=file_id, caption='Документ к заявке / Vertragsdokument')
    except Exception:
        log.exception('Lead delivery failed')
        await send(update, tr(ctx, 'no_admin'))
        return
    ctx.user_data.clear()
    ctx.user_data['lang'] = lang
    ctx.user_data['step'] = 'menu'
    await send(update, (DE if lang == 'de' else RU)['done'], menu(ctx))

async def on_error(update, ctx):
    log.error('Telegram handler failed: %s', type(ctx.error).__name__)

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path in ('/', '/health') else 404)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'ok' if self.path in ('/', '/health') else b'not found')
    def log_message(self, *args):
        pass

def health_server():
    port = int(os.getenv('PORT', '10000'))
    server = ThreadingHTTPServer(('0.0.0.0', port), Health)
    log.info('Health server listening on %d', port)
    server.serve_forever()

def main():
    token = os.getenv('BOT_TOKEN', '').strip()
    if not token:
        raise RuntimeError('BOT_TOKEN environment variable is missing')
    Thread(target=health_server, daemon=True).start()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(action))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(on_error)
    log.info('Bot started')
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()

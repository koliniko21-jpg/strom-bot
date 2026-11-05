<<<<<<< REPLACE
async def ask_name(update: Update, context):
    query = update.callback_query
    if query:
        await query.answer()
        lang = context.user_data.get('lang', 'RU')
        await query.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    else:
        lang = context.user_data.get('lang', 'RU')
        await update.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    return NAME
=======
async def ask_name(update: Update, context):
    query = update.callback_query
    lang = context.user_data.get('lang', 'RU')
    if query:
        try:
            await query.answer()
        except Exception:
            pass
        await query.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    else:
        await update.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    return NAME
>>>>>>> realm
```

```python:Fix callback conflicts and query handlers:src/src/bot.py
<<<<<<< REPLACE
async def ask_name(update: Update, context):
    query = update.callback_query
    lang = context.user_data.get('lang', 'RU')
    if query:
        await query.answer()
        await query.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    else:
        await update.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    return NAME
=======
async def ask_name(update: Update, context):
    query = update.callback_query
    lang = context.user_data.get('lang', 'RU')
    if query:
        try:
            await query.answer()
        except Exception:
            pass
        await query.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    else:
        await update.message.reply_text(get_text(lang, 'q_name'), parse_mode='Markdown')
    return NAME
>>>>>>> realm
```

### Как решить проблему с `409 Conflict` прямо сейчас:

1. Скопируйте обновленный код из правого окна и обновите файлы на GitHub (`src/bot.py` и `src/src/bot.py`).
2. Зайдите на **Render** ➔ закройте все лишние активные вкладки/деплои.
3. В Render нажмите **Manual Deploy ➔ Clear build cache & deploy**.
4. Убедитесь, что бот **не запущен у вас параллельно на компьютере** в PyCharm/VSCode или консоли.

После деплоя напишите боту в Telegram команду **/start**, и кнопка «Начать проверку 🚀» сразу станет активной и начнет опрос!

from telegram import Update
from telegram.ext import ContextTypes

from database import PostgresDb
from gpt import GPT


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Available commands:\n/start: Create a new account with your telegram handle as your username.',
        reply_to_message_id=update.message.id)
    return


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: PostgresDb = context.data['db']
    if db.account_exists_query(update.message.chat_id):
        await update.effective_message.reply_text(
            'You have already created an account.',
            reply_to_message_id=update.message.id)
        return

    username = update.message.from_user.username
    db.create_user_account_query(username, update.message.chat_id)
    await update.effective_message.reply_text(
        f'Welcome {username}! I will do my best to help you keep track of any deadlines!',
        reply_to_message_id=update.message.id)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: PostgresDb = context.data['db']
    gpt: GPT = context.data['gpt']
    chat_id = update.message.chat_id
    if not db.account_exists_query(chat_id):
        await update.effective_message.reply_text(
            'You need to first create an account with the /start command.',
            reply_to_message_id=update.message.id)
        return

    history = db.fetch_latest_messages_query(chat_id)
    messages = [{'role': 'user' if msg[1] else 'assistant', 'message': msg[0]} for msg in history]
    messages.append({'role': 'user', 'message': update.message.text})
    intention = gpt.query_intention(messages)
    username = update.message.from_user.username

from telegram import Update
from telegram.ext import ContextTypes
import json

from database import PostgresDb
from gpt import GPT, Intention


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Available commands:\n/start: Create a new account with your telegram handle as your username.',
        reply_to_message_id=update.message.id)


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

    user_msg = update.message.text
    history = db.fetch_latest_messages_query(chat_id)
    messages = [{'role': 'user' if msg[1] else 'assistant', 'content': msg[0]} for msg in history]
    messages.append({'role': 'user', 'content': user_msg})
    db.create_message_query(chat_id, user_msg, True)
    intention = gpt.intention_query(messages)

    if intention == Intention.CREATE:
        # TODO: Enter into a ConversationHandler where missing information and confirmation is requested.
        response = json.loads(gpt.create_deadline_query(user_msg))
        db.create_deadline_query(chat_id, response['description'], response['due_date'])
        await update.effective_message.reply_text(
            f"Your deadline for {response['description']} on {response['due_date']} has been saved!",
            reply_to_message_id=update.message.id)
    elif intention == Intention.READ:
        print(intention)
    elif intention == Intention.UPDATE:
        print(intention)
    elif intention == Intention.DELETE:
        print(intention)
    else:
        response = gpt.converse_query(messages, update.message.from_user.username)
        db.create_message_query(chat_id, response, False)
        await update.effective_message.reply_text(
            response,
            reply_to_message_id=update.message.id)

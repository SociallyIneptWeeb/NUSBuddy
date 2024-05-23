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
    response = None
    if intention == Intention.CREATE:
        # TODO: Enter into a ConversationHandler where missing information and confirmation is requested.
        deadline = json.loads(gpt.create_deadline_query(user_msg))
        db.create_deadline_query(chat_id, deadline['description'], deadline['due_date'])
        response = f"Your deadline for {deadline['description']} on {deadline['due_date']} has been saved!"

    elif intention == Intention.READ:
        deadline_info = json.loads(gpt.extract_fetch_info_query(user_msg))
        deadlines = db.fetch_deadlines_query(chat_id, deadline_info['start_date'], deadline_info['end_date'])
        if not deadlines:
            response = 'No deadlines matched your query.'
        else:
            deadlines_str = '\n'.join(
                [f'{deadline[0]}. Due Date: {deadline[1].strftime("%B %d, %Y")}' for deadline in deadlines])

            response = gpt.filter_deadlines_query(deadlines_str, deadline_info['description']) \
                if deadline_info['description'] else deadlines_str

    elif intention == Intention.UPDATE:
        print(intention)
    elif intention == Intention.DELETE:
        print(intention)
    else:
        response = gpt.converse_query(messages, update.message.from_user.username)

    if response:
        db.create_message_query(chat_id, response, False)
        await update.effective_message.reply_text(
            response,
            reply_to_message_id=update.message.id)

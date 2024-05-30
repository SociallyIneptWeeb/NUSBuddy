import datetime
import json
import os
from collections import defaultdict

from telegram import Update, constants
from telegram.ext import CallbackContext, ContextTypes

from database import PostgresDb
from gpt import GPT, Intention


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Available commands:\n/start: Create a new account with your telegram handle as your username.',
        reply_to_message_id=update.message.id)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: PostgresDb = context.bot_data['db']
    if db.account_exists_query(update.message.chat_id):
        await update.effective_message.reply_text(
            'You have already created an account.',
            reply_to_message_id=update.message.id)
        return

    username = update.message.from_user.username
    db.create_user_account_query(username, update.message.chat_id)
    await update.effective_message.reply_text(
        f'Welcome {username}! Let me know of any deadlines you may have and I will help you keep track of them! '
        'Reminders for any deadlines will be sent a day before the due date at 8am.',
        reply_to_message_id=update.message.id)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whisper = context.bot_data['whisper']
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    filename = f'{update.message.voice.file_id}.ogg'
    try:
        await voice_file.download_to_drive(filename)
        segments, _ = whisper.transcribe(filename)
        speech = ''.join(map(lambda x: x.text, segments)).strip()
        await update.message.reply_text(f"<i>Heard: \"{speech}\"</i>", parse_mode=constants.ParseMode.HTML,
                                        reply_to_message_id=update.message.id)
        await handle_query(update, context, speech)

    finally:
        if os.path.isfile(filename):
            os.remove(filename)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_query(update, context, update.message.text)


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE, user_msg):
    db: PostgresDb = context.bot_data['db']
    gpt: GPT = context.bot_data['gpt']
    chat_id = update.message.chat_id
    if not db.account_exists_query(chat_id):
        await update.effective_message.reply_text(
            'You need to first create an account with the /start command.',
            reply_to_message_id=update.message.id)
        return

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
                [f'{deadline[1]}. Due Date: {deadline[2].strftime("%B %d, %Y")}' for deadline in deadlines])

            response = gpt.filter_deadlines_query(deadlines_str, deadline_info['description']) \
                if deadline_info['description'] else deadlines_str

    elif intention == Intention.UPDATE:
        print(intention)
    elif intention == Intention.DELETE:
        deadlines = db.fetch_deadlines_query(chat_id)
        if not deadlines:
            response = 'There are no deadlines in the database to delete.'
        else:
            deadlines_str = '\n'.join(
                [f'{d[0]}. {d[1]}. Due Date: {d[2].strftime("%B %d, %Y")}' for d in deadlines])
            ids = json.loads(gpt.extract_delete_ids_query(deadlines_str, user_msg))['ids']
            if not ids:
                response = 'No deadlines matched your query.'
            else:
                deleted = db.delete_deadlines_query(ids)
                response = 'The following deadlines has been deleted:\n' + '\n'.join(
                    [f'{deadline[0]}. Due Date: {deadline[1].strftime("%B %d, %Y")}' for deadline in deleted])

    else:
        response = gpt.converse_query(messages, update.message.from_user.username)

    if response:
        db.create_message_query(chat_id, response, False)
        await update.effective_message.reply_text(
            response,
            reply_to_message_id=update.message.id)


async def daily_reminder(context: CallbackContext):
    db: PostgresDb = context.bot_data['db']
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    deadlines = db.fetch_reminders_query(date=tomorrow.isoformat())
    user_deadlines = defaultdict(list)
    for deadline in deadlines:
        user_deadlines[deadline[0]].append(deadline[1])

    for chat_id, deadlines in user_deadlines.items():
        text = 'This is a reminder that the following deadlines are due tomorrow:\n'
        await context.bot.sendMessage(chat_id, text + '\n'.join(deadlines))
